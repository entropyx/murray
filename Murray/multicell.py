import os
import concurrent.futures

import numpy as np

from logger_config import get_logger

from .selection import select_treatments_exclusive
from .better_groups import (
    evaluate_group_exclusive,
    _init_bettergroups_worker,
    _evaluate_group_exclusive_worker,
)

logger = get_logger("multicell")


def _resolve_multicell_feasibility(allowed_sizes, total_cells_needed, excluded_locations, data):
    """
    Resolve a feasible cell count instead of hard-failing.

    Each of `effective_k` cells gets a slice of about n_available / effective_k geos, which
    must hold at least the smallest allowed size. Returns the largest cell count that
    satisfies this (capped at the requested count), plus human-readable warnings describing
    any reduction. effective_k == 0 means not even one cell is feasible.

    Returns:
        tuple: (effective_k: int, warnings: list[str])
    """
    warnings = []
    excluded = {loc for loc in (excluded_locations or []) if str(loc).strip()}
    n_available = data.loc[~data["location"].isin(excluded), "location"].nunique()

    min_size = max(min(allowed_sizes), 1) if allowed_sizes else 1
    max_feasible_k = n_available // min_size
    effective_k = min(total_cells_needed, max_feasible_k)

    if effective_k < total_cells_needed:
        warnings.append(
            f"Requested {total_cells_needed} cells but only {n_available} locations are "
            f"available for the smallest cell size ({min_size}); reducing to {effective_k} cells."
        )

    return effective_k, warnings


def partition_locations_systematic(data, excluded_locations, k, seed=42):
    """
    Partition geos into k disjoint, volume-balanced cells (GeoLift-style).

    Ranks locations by total Y descending, then deals them round-robin across k cells
    (cell at rank-offset o receives ranked[o::k]) so each cell gets a comparable mix of
    high/low-volume geos. The rotation offset is seeded for reproducibility. Mirrors
    GeoLift's MultiCellMarketSelection systematic sampling (R/MultiCell.R:184-201).

    Returns:
        dict: {cell_id (1-based int): [locations]} with min(k, n_available) non-empty cells.
    """
    excluded = {loc for loc in (excluded_locations or []) if str(loc).strip()}
    sums = (
        data[~data["location"].isin(excluded)]
        .groupby("location")["Y"]
        .sum()
        .sort_values(ascending=False)
    )
    ranked = list(sums.index)
    n = len(ranked)
    if n == 0 or k <= 0:
        return {}

    k = min(k, n)  # cannot make more cells than available locations
    rng = np.random.default_rng(seed)
    offsets = rng.permutation(k)  # permutation of 0..k-1 -> disjoint, full coverage

    partition = {}
    for cell_idx in range(k):
        start = int(offsets[cell_idx])
        partition[cell_idx + 1] = ranked[start::k]
    return partition


def _finalize_multicell_controls(
    chosen_cells,
    all_treatments,
    data,
    total_Y,
    correlation_matrix,
    min_holdout,
    df_pivot,
    excluded_locations,
    excluded_control_locations,
):
    """
    Pass 2: re-derive each cell's control from the shared pool (global minus ALL treatments)
    and re-score, so reported MAPE/SMAPE reflect the final control actually used (fixes the
    Phase-1/Phase-3 metric mismatch). Returns the `global_experiment` cell dicts.
    """
    unified = []
    for treatment_group, size in chosen_cells:
        other_treatments = set(all_treatments) - set(treatment_group)
        result = evaluate_group_exclusive(
            treatment_group,
            data,
            total_Y,
            correlation_matrix,
            min_holdout,
            df_pivot,
            used_treatment_locations=other_treatments,
            excluded_locations=excluded_locations,
            excluded_control_locations=excluded_control_locations,
        )
        if result is None or not np.isfinite(result[2]):
            logger.warning(f"Dropping cell with treatment {treatment_group}: no valid final control")
            continue

        (_, control_group, mape, smape, y, predictions, weights, observed_conformity, _, _) = result
        treatment_Y = data[data["location"].isin(treatment_group)]["Y"].sum()
        holdout_percentage = round(
            ((total_Y - treatment_Y) / total_Y) * 100 if total_Y > 0 else 0.0, 2
        )

        unified.append(
            {
                "Cell": len(unified) + 1,
                "Size": size,
                "Best Treatment Group": treatment_group,
                "Control Group": control_group,
                "MAPE": mape,
                "SMAPE": smape,
                "Actual Target Metric (y)": y,
                "Predictions": predictions,
                "Weights": weights,
                "Holdout Percentage": holdout_percentage,
                "observed_conformity": observed_conformity,
            }
        )

    return unified


def _cell_rank_key(result):
    """Per-cell selection key for multi-cell candidates.

    Ranks by synthetic-control fit quality: scaled-L2 imbalance first (the normalized
    noise floor that drives detectability / MDE, GeoLift's "Scaled L2 Imbalance"), with
    ranking-SMAPE as the tiebreak. Lower is better for both. `result` is the
    ``evaluate_group_exclusive`` tuple (MAPE=2, SMAPE=3, scaled_l2=8).
    """
    return (result[8], result[3])  # (scaled_l2 imbalance asc, SMAPE asc)


def _results_by_cell_for_sensitivity(global_experiment):
    """Build the per-CELL input for evaluate_sensitivity from a global_experiment.

    Keyed by cell number (not size) so multiple cells of the SAME size each get their own
    sensitivity computed on their own treatment/control — partition-first lets two cells
    share a size, and a per-size key would collapse them onto one cell's metrics.
    Returns {cell_number: result_dict}.
    """
    results_by_cell = {}
    for cell in global_experiment:
        results_by_cell[cell["Cell"]] = {
            "Best Treatment Group": cell["Best Treatment Group"],
            "Control Group": cell["Control Group"],
            "MAPE": cell["MAPE"],
            "SMAPE": cell["SMAPE"],
            "Actual Target Metric (y)": cell["Actual Target Metric (y)"],
            "Predictions": cell["Predictions"],
            "Weights": cell["Weights"],
            "observed_conformity": cell["observed_conformity"],
        }
    return results_by_cell


def optimize_global_multicell(
    similarity_matrix,
    allowed_sizes,
    total_cells_needed,
    excluded_locations,
    data,
    correlation_matrix,
    maximum_treatment_percentage,
    excluded_control_locations=None,
    progress_updater=None,
    status_updater=None,
    seed=42,
):
    """
    Partition-first global multi-cell optimization.

    Partitions available geos into disjoint slices, generates slice-restricted
    candidates in a single process pool (Pass 1), picks the best (size, treatment)
    per cell, then re-scores all cells against the shared control pool (Pass 2).

    Args:
        similarity_matrix: Correlation matrix for treatment selection
        allowed_sizes: List of allowed cell sizes to choose from
        total_cells_needed: Total number of cells in final experiment
        excluded_locations: Globally excluded locations
        data: Input data
        correlation_matrix: Market correlation matrix
        maximum_treatment_percentage: Max treatment percentage
        excluded_control_locations: Locations excluded from control pool
        progress_updater: Progress bar updater
        status_updater: Status text updater
        seed: Random seed for deterministic partitioning and candidate generation

    Returns:
        dict: {"global_experiment": [cell_dicts]}, or None if no valid cells produced
    """
    logger.info(
        f"Partition-first multi-cell optimization: {total_cells_needed} cells, sizes {allowed_sizes}"
    )

    # Resolve geometric feasibility (can we partition into effective_k cells?).
    # Holdout feasibility (treatment-share limits per cell) is enforced downstream in evaluate_group_exclusive.
    effective_k, warnings = _resolve_multicell_feasibility(
        allowed_sizes, total_cells_needed, excluded_locations, data
    )
    for warning in warnings:
        logger.warning(f"Multicell feasibility: {warning}")
    if effective_k < 1:
        logger.error("BetterGroups failed: no locations available for even one cell.")
        return None

    total_Y = data["Y"].sum()
    if total_Y == 0:
        logger.error("BetterGroups failed: Total Y sum is 0.")
        return None

    min_holdout = 100 - (maximum_treatment_percentage * 100)
    df_pivot = data.pivot(index="time", columns="location", values="Y")

    # Step 1: deterministic, volume-balanced partition into effective_k disjoint slices
    partition = partition_locations_systematic(
        data, excluded_locations, effective_k, seed=seed
    )

    # Step 2 (Pass 1): generate slice-restricted candidates across allowed sizes
    indexed_candidates = []  # (cell_id, size, treatment_group)
    for cell_id, slice_locs in sorted(partition.items()):
        for size in allowed_sizes:
            if size > len(slice_locs):
                continue
            groups = select_treatments_exclusive(
                similarity_matrix,
                size,
                excluded_locations,
                used_treatment_locations=set(),
                allowed_locations=slice_locs,
                seed=seed,
            )
            for group in groups:
                indexed_candidates.append((cell_id, size, group))

    if not indexed_candidates:
        logger.error("BetterGroups failed: no candidates generated in any slice.")
        return None

    # Evaluate every candidate once (provisional control = global minus its own treatment)
    groups_only = [c[2] for c in indexed_candidates]
    best_per_cell = {}  # cell_id -> (sort_key, size, treatment_group)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=os.cpu_count() or 4,
        initializer=_init_bettergroups_worker,
        initargs=(data, total_Y, correlation_matrix, min_holdout, df_pivot,
                  set(), excluded_locations, excluded_control_locations),
    ) as executor:
        for (cell_id, size, _), result in zip(
            indexed_candidates, executor.map(_evaluate_group_exclusive_worker, groups_only)
        ):
            if result is None or not np.isfinite(result[2]) or not np.isfinite(result[8]):
                continue
            sort_key = _cell_rank_key(result)  # (scaled_l2 imbalance asc, SMAPE asc)
            if cell_id not in best_per_cell or sort_key < best_per_cell[cell_id][0]:
                best_per_cell[cell_id] = (sort_key, size, result[0])

    if not best_per_cell:
        logger.error("BetterGroups failed: no cell produced a valid treatment group.")
        return None

    # Order cells by cell_id; collect every treatment for the shared-pool control step
    chosen_cells = [
        (best_per_cell[cell_id][2], best_per_cell[cell_id][1])
        for cell_id in sorted(best_per_cell)
    ]
    all_treatments = set()
    for treatment_group, _ in chosen_cells:
        all_treatments.update(treatment_group)

    # Step 3 (Pass 2): final controls from the shared pool + re-score for honest metrics
    unified_results = _finalize_multicell_controls(
        chosen_cells, all_treatments, data, total_Y, correlation_matrix,
        min_holdout, df_pivot, excluded_locations, excluded_control_locations,
    )

    if not unified_results:
        logger.error("BetterGroups failed: no cell survived final control re-scoring.")
        return None

    logger.info(f"Partition multi-cell completed: {len(unified_results)} cells")
    return {"global_experiment": unified_results}

import concurrent.futures
import multiprocessing
import os
from math import comb

import numpy as np

from logger_config import get_logger

from .parallel import _limit_blas_threads
from .selection import (
    select_treatments,
    select_controls,
    select_treatments_exclusive,
    select_controls_exclusive,
)
from .synthetic_control import (
    smape,
    scaled_l2_imbalance,
    _fit_sc_counterfactual,
    _rolling_origin_smapes,
    select_engine_isolated,
)
from .inference import compute_falsification_metrics

logger = get_logger("better_groups")

_WORKER_DATA = None


def _evaluate_group_isolated(args, timeout=300):
    """
    Run evaluate_group in a SEPARATE single-threaded-BLAS process and return its result tuple,
    or ``None`` if the child dies. Used for the design final-cell augmentation="auto" re-fit,
    which (like the evaluation path) runs ~20 cvxpy/SCS solves that can SIGSEGV in the Modal
    container's main thread — see select_engine_isolated. The caller keeps the ridge result on
    a None return, so a native crash degrades to ridge instead of crash-looping the runner.

    ``args`` is the positional tuple passed straight to evaluate_group.
    """
    # spawn context for the same reason as select_engine_isolated (fork-from-thread is unsafe;
    # spawn re-imports with the image's single-thread BLAS env vars in effect).
    executor = concurrent.futures.ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn"),
        initializer=_limit_blas_threads,
    )
    try:
        return executor.submit(evaluate_group, *args).result(timeout=timeout)
    except Exception as e:
        logger.warning(
            f"isolated auto re-fit failed ({type(e).__name__}: {e}); keeping ridge fit"
        )
        return None
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def evaluate_group(
    treatment_group, data, total_Y, correlation_matrix, min_holdout, df_pivot,
    treatment_period=None, excluded_control_locations=None, cv_folds=2, augmentation=None,
):
    """
    Evaluates a treatment group and returns error metrics.

    Args:
        treatment_group: List of locations in the treatment group
        data: Input data
        total_Y: Total sum of Y values
        correlation_matrix: Market correlation matrix
        min_holdout: Minimum holdout percentage required
        df_pivot: Pivoted data with time as index
        treatment_period: Number of periods for treatment (if None, uses 80/20 split)
        excluded_control_locations: Locations the user wants out of the control group. Threaded
            through to select_controls so single-cell mode honors it.
    """
    logger.debug(f"Starting evaluation for treatment group: {treatment_group}")

    treatment_Y = data[data["location"].isin(treatment_group)]["Y"].sum()
    holdout_percentage = round((1 - (treatment_Y / total_Y)) * 100, 2)

    logger.debug(
        f"Treatment Y: {treatment_Y}, Holdout percentage: {holdout_percentage:.2f}%"
    )

    if holdout_percentage < min_holdout:
        logger.debug(
            f"Holdout percentage {holdout_percentage:.2f}% below minimum {min_holdout}%, skipping"
        )
        return None

    logger.debug("Selecting control group")
    control_group = select_controls(
        correlation_matrix=correlation_matrix,
        treatment_group=treatment_group,
        excluded_control_locations=excluded_control_locations,
    )
    logger.debug(f"Control group selected: {control_group}")

    if not control_group:
        logger.warning(f"No control group found for treatment group: {treatment_group}")
        return (treatment_group, [], float("inf"), float("inf"), None, None, None, None, float("inf"), None)

    logger.debug("Preparing data for synthetic control")
    X = df_pivot[control_group].values
    y = df_pivot[treatment_group].sum(axis=1).values

    if treatment_period is not None:
        split_index = len(X) - treatment_period
    else:
        default_period = min(10, len(X) // 4)
        split_index = len(X) - default_period

    fit = _fit_sc_counterfactual(X, y, split_index, augmentation=augmentation)
    if fit.get("engine"):  # only set on the augmentation="auto" path (final-cell re-fit)
        logger.info(
            f"SCM engine for {treatment_group}: {fit['engine']} (alpha={fit.get('ridge_alpha')})"
        )
    counterfactual_full_original = fit["counterfactual"]
    y_original = fit["y_original"]
    model = fit["model"]
    split_index = fit["split_index"]

    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    logger.debug("Calculating metrics")
    MAPE = round(
        np.mean(
            np.abs(
                (y_original[split_index:] - counterfactual_full_original[split_index:])
                / (y_original[split_index:] + 1e-10)
            )
        )
        * 100,
        2
    )
    SMAPE_value = round(
        smape(
            y_original[split_index:], counterfactual_full_original[split_index:]
        ),
        2
    )
    observed_conformity = round(float(np.mean(y_original - counterfactual_full_original)), 2)
    scaled_l2 = round(
        scaled_l2_imbalance(
            y_original[:split_index], counterfactual_full_original[:split_index], X[:split_index]
        ),
        4,
    )

    # Ranking SMAPE (ISS-7): average the main 0.8 holdout with earlier forward-chaining
    # folds so the rank is less sensitive to a one-off shock in the recent window.
    ranking_smape = SMAPE_value
    if cv_folds and cv_folds > 0:
        cv_smapes = _rolling_origin_smapes(X, y, n_folds=cv_folds, augmentation=augmentation)
        if cv_smapes:
            ranking_smape = round(float(np.mean([SMAPE_value] + cv_smapes)), 2)

    return (
        treatment_group,
        filtered_control_group,
        MAPE,
        ranking_smape,
        np.round(y_original, 2),
        np.round(counterfactual_full_original, 2),
        filtered_weights,
        observed_conformity,
        scaled_l2,
        X,
    )


def evaluate_group_exclusive(
    treatment_group,
    data,
    total_Y,
    correlation_matrix,
    min_holdout,
    df_pivot,
    used_treatment_locations=None,
    excluded_locations=None,
    excluded_control_locations=None,
    treatment_period=None,
    cv_folds=2,
    augmentation=None,
):
    """
    Evaluates a treatment group with location exclusivity for multi-cell mode.

    Applies the same evaluation logic as evaluate_group() but with additional
    exclusivity constraints for multi-cell experiments.

    Args:
        treatment_group (list): List of treatment locations to evaluate
        data (pd.DataFrame): Input data with 'location', 'time', and 'Y' columns
        total_Y (float): Total sum of Y values across all locations
        correlation_matrix (pd.DataFrame): Market correlation matrix for control selection
        min_holdout (float): Minimum required holdout percentage
        df_pivot (pd.DataFrame): Pivoted data with time as index and locations as columns
        used_treatment_locations (set): Set of locations already used as treatment in other cells
        excluded_locations (list): List of globally excluded locations
        treatment_period (int): Number of periods for treatment (if None, uses 80/20 split)

    Returns:
        tuple: (treatment_group, control_group, MAPE, SMAPE, y_original,
                counterfactual_full_original, filtered_weights, observed_conformity)
        None: If holdout percentage is below minimum or no valid control group found
    """
    logger.debug(
        f"Starting exclusive evaluation for treatment group: {treatment_group}"
    )

    treatment_Y = data[data["location"].isin(treatment_group)]["Y"].sum()
    holdout_percentage = round((1 - (treatment_Y / total_Y)) * 100, 2)

    logger.debug(
        f"Treatment Y: {treatment_Y}, Holdout percentage: {holdout_percentage:.2f}%"
    )

    if holdout_percentage < min_holdout:
        logger.debug(
            f"Holdout percentage {holdout_percentage:.2f}% below minimum {min_holdout}%, skipping"
        )
        return None

    logger.debug("Selecting control group with exclusivity")
    control_group = select_controls_exclusive(
        correlation_matrix=correlation_matrix,
        treatment_group=treatment_group,
        used_treatment_locations=used_treatment_locations,
        excluded_locations=excluded_locations,
        excluded_control_locations=excluded_control_locations,
    )
    logger.debug(f"Control group selected: {control_group}")

    if not control_group:
        logger.warning(f"No control group found for treatment group: {treatment_group}")
        return (treatment_group, [], float("inf"), float("inf"), None, None, None, None, float("inf"), None)

    logger.debug("Preparing data for synthetic control")
    X = df_pivot[control_group].values
    y = df_pivot[treatment_group].sum(axis=1).values

    if treatment_period is not None:
        split_index = len(X) - treatment_period
    else:
        default_period = min(10, len(X) // 4)
        split_index = len(X) - default_period

    fit = _fit_sc_counterfactual(X, y, split_index, augmentation=augmentation)
    if fit.get("engine"):  # only set on the augmentation="auto" path (final-cell re-fit)
        logger.info(
            f"SCM engine for {treatment_group}: {fit['engine']} (alpha={fit.get('ridge_alpha')})"
        )
    counterfactual_full_original = fit["counterfactual"]
    y_original = fit["y_original"]
    model = fit["model"]
    split_index = fit["split_index"]

    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    logger.debug("Calculating metrics")
    MAPE = round(
        np.mean(
            np.abs(
                (y_original[split_index:] - counterfactual_full_original[split_index:])
                / (y_original[split_index:] + 1e-10)
            )
        )
        * 100,
        2
    )
    SMAPE_value = round(
        smape(
            y_original[split_index:], counterfactual_full_original[split_index:]
        ),
        2
    )
    observed_conformity = round(float(np.mean(y_original - counterfactual_full_original)), 2)
    scaled_l2 = round(
        scaled_l2_imbalance(
            y_original[:split_index], counterfactual_full_original[:split_index], X[:split_index]
        ),
        4,
    )

    # Ranking SMAPE (ISS-7): average the main 0.8 holdout with earlier forward-chaining
    # folds so the rank is less sensitive to a one-off shock in the recent window.
    ranking_smape = SMAPE_value
    if cv_folds and cv_folds > 0:
        cv_smapes = _rolling_origin_smapes(X, y, n_folds=cv_folds, augmentation=augmentation)
        if cv_smapes:
            ranking_smape = round(float(np.mean([SMAPE_value] + cv_smapes)), 2)

    return (
        treatment_group,
        filtered_control_group,
        MAPE,
        ranking_smape,
        np.round(y_original, 2),
        np.round(counterfactual_full_original, 2),
        filtered_weights,
        observed_conformity,
        scaled_l2,
        X,
    )


# ---------------------------------------------------------------------------
# ProcessPoolExecutor helpers for BetterGroups
# Must be module-level (not lambdas) to be picklable by multiprocessing.
# Data is sent once per worker process via initializer, not once per task.
# ---------------------------------------------------------------------------


def _init_bettergroups_worker(*args):
    global _WORKER_DATA
    _limit_blas_threads()
    _WORKER_DATA = args


def _evaluate_group_worker(group):
    return evaluate_group(group, *_WORKER_DATA)


def _evaluate_group_exclusive_worker(group):
    return evaluate_group_exclusive(group, *_WORKER_DATA)


def BetterGroups(
    similarity_matrix,
    excluded_locations,
    data,
    correlation_matrix,
    maximum_treatment_percentage=0.50,
    progress_updater=None,
    status_updater=None,
    multicell_config=None,
    global_optimization=False,
    excluded_control_locations=None,
    top_k=None,
    significance_level=0.1,
    fpr_gate_multiplier=2.0,
    top_k_finalists=10,
    n_power_simulations_falsification=100,
    n_permutations_falsification=500,
    alternative="two-sided",
    inference_type="iid",
    max_abs_lift_in_zero=3.0,
):
    """
    Enhanced simulates and evaluates treatment groups for geo-experiments.

    Supports three modes:
    1. Single-cell mode: Finds optimal treatment groups for each size
    2. Multi-cell normal mode: Finds N best groups per size with location exclusivity
    3. Multi-cell global mode: Global optimization for heterogeneous cell sizes

    Args:
        similarity_matrix (pd.DataFrame): Correlation matrix for treatment selection
        excluded_locations (list): List of locations to exclude from treatment selection
        data (pd.DataFrame): Input data with 'location', 'time', and 'Y' columns
        correlation_matrix (pd.DataFrame): Market correlation matrix for control selection
        maximum_treatment_percentage (float): Maximum treatment percentage (default: 0.50)
        progress_updater (callable): Progress bar updater function
        status_updater (callable): Status text updater function
        multicell_config (dict): Multi-cell configuration with 'sizes' and 'top_n' keys
        global_optimization (bool): Whether to use global optimization for multi-cell mode

    Returns:
        dict: Results organized by mode:
            - Single-cell: {size: {group_info}}
            - Multi-cell normal: {size: [group1, group2, ...]}
            - Multi-cell global: {"global_experiment": [cell1, cell2, ...]}
        None: If no valid groups found
    """
    unique_locations = data["location"].unique()
    no_locations = len(unique_locations)
    # max_group_size = round(no_locations * 0.35)
    # min_elements_in_treatment = round(no_locations * 0.20)
    max_group_size = round(no_locations * 0.45)
    min_elements_in_treatment = round(no_locations * 0.15)
    min_holdout = 100 - (maximum_treatment_percentage * 100)
    total_Y = data["Y"].sum()

    if total_Y == 0:
        logger.error("BetterGroups failed: Total Y sum is 0. Check that your data contains non-zero values in the 'Y' column.")
        return None

    df_pivot = data.pivot(index="time", columns="location", values="Y")

    # --- Multi-cell mode---
    if multicell_config is not None and multicell_config.get("sizes"):
        sizes = multicell_config["sizes"]
        top_n = multicell_config.get("top_n", 1)

        # Check if global optimization is requested
        if global_optimization:
            logger.info(
                f"Starting global multi-cell optimization for {top_n} cells with allowed sizes {sizes}"
            )
            from .multicell import optimize_global_multicell
            return optimize_global_multicell(
                similarity_matrix=similarity_matrix,
                allowed_sizes=sizes,
                total_cells_needed=top_n,
                excluded_locations=excluded_locations,
                data=data,
                correlation_matrix=correlation_matrix,
                maximum_treatment_percentage=maximum_treatment_percentage,
                excluded_control_locations=excluded_control_locations,
                progress_updater=progress_updater,
                status_updater=status_updater,
            )

        # Original multi-cell mode (per-size optimization)
        logger.info(f"Starting multi-cell flexible with location exclusivity")
        results_by_size = {}
        used_treatment_locations = set()

        for size in sizes:

            groups = select_treatments_exclusive(
                similarity_matrix, size, excluded_locations, used_treatment_locations
            )
            if not groups:
                logger.warning(
                    f"No valid groups available for size {size} (insufficient available locations)"
                )
                continue

            total_groups = len(groups)
            results = []
            total_groups_all_sizes = sum(
                len(
                    select_treatments_exclusive(
                        similarity_matrix,
                        s,
                        excluded_locations,
                        used_treatment_locations,
                    )
                )
                for s in sizes
            )
            groups_processed_so_far = sum(
                len(results_by_size.get(s, [])) for s in sizes
            )
            log_interval = max(1, total_groups_all_sizes // 10)

            with concurrent.futures.ProcessPoolExecutor(
                max_workers=os.cpu_count() or 4,
                initializer=_init_bettergroups_worker,
                initargs=(data, total_Y, correlation_matrix, min_holdout, df_pivot,
                          used_treatment_locations, excluded_locations,
                          excluded_control_locations),
            ) as executor:
                futures = executor.map(_evaluate_group_exclusive_worker, groups)

                for idx, result in enumerate(futures):
                    results.append(result)
                    current_total = groups_processed_so_far + idx + 1
                    if progress_updater:
                        progress_updater.progress(
                            current_total / total_groups_all_sizes
                        )
                    if status_updater:
                        status_updater.text(
                            f"Evaluando grupos totales: {current_total}/{total_groups_all_sizes} ({int(current_total / total_groups_all_sizes * 100)}%)"
                        )
                    if (
                        current_total % log_interval == 0
                        or idx == 0
                        or current_total == total_groups_all_sizes
                    ):
                        logger.info(
                            f"Processed {current_total}/{total_groups_all_sizes} total groups"
                        )

            valid_results = [r for r in results if r is not None]
            if not valid_results:
                logger.warning(f"No valid results for size {size}")
                continue

            sorted_results = sorted(valid_results, key=lambda x: (x[2], -x[3]))

            selected_treatment_groups = []
            size_used_treatments = set()

            for result in sorted_results:
                treatment_group = set(result[0])

                all_conflicts = used_treatment_locations | size_used_treatments

                if not (treatment_group & all_conflicts):
                    selected_treatment_groups.append(result[0])
                    size_used_treatments.update(treatment_group)

                    if len(selected_treatment_groups) >= top_n:
                        break
                else:
                    logger.debug(
                        f"Skipping treatment group {result[0]} due to conflicts with used locations"
                    )

            final_results = []
            for treatment_group in selected_treatment_groups:
                other_treatments_this_size = set()
                for other_group in selected_treatment_groups:
                    if other_group != treatment_group:
                        other_treatments_this_size.update(other_group)

                current_used_treatments = (
                    used_treatment_locations | other_treatments_this_size
                )

                result = evaluate_group_exclusive(
                    treatment_group=treatment_group,
                    data=data,
                    total_Y=total_Y,
                    correlation_matrix=correlation_matrix,
                    min_holdout=min_holdout,
                    df_pivot=df_pivot,
                    used_treatment_locations=current_used_treatments,
                    excluded_locations=excluded_locations,
                    excluded_control_locations=excluded_control_locations,
                )
                if result is not None:
                    final_results.append(result)

            final_results_sorted = sorted(final_results, key=lambda x: (x[2], -x[3]))

            results_by_size[size] = []
            for idx, r in enumerate(final_results_sorted):
                result_dict = {
                    "Best Treatment Group": r[0],
                    "Control Group": r[1],
                    "MAPE": r[2],
                    "SMAPE": r[3],
                    "Actual Target Metric (y)": r[4],
                    "Predictions": r[5],
                    "Weights": r[6],
                    "Holdout Percentage": (
                        (
                            (total_Y - data[data["location"].isin(r[0])]["Y"].sum())
                            / total_Y
                        )
                        * 100
                        if total_Y > 0
                        else 0.0
                    ),
                    "observed_conformity": r[7],
                }
                results_by_size[size].append(result_dict)

            if final_results:
                best_result = final_results_sorted[0]
                used_treatment_locations.update(best_result[0])

        if not results_by_size:
            logger.error("BetterGroups failed: No valid results for any size in multi-cell mode. Try reducing excluded locations or adjusting group sizes.")
            return None
        return results_by_size

    # --- Single-cell mode ---
    logger.info(f"Starting single-cell mode")
    possible_groups = []
    for size in range(min_elements_in_treatment, max_group_size + 1):
        groups = select_treatments(similarity_matrix, size, excluded_locations)
        possible_groups.extend(groups)

    if not possible_groups:
        logger.error("BetterGroups failed: No possible groups found for single-cell mode. Check excluded locations and treatment percentage settings.")
        return None

    total_groups = len(possible_groups)
    results = []
    log_interval = max(1, total_groups // 10)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=os.cpu_count() or 4,
        initializer=_init_bettergroups_worker,
        initargs=(data, total_Y, correlation_matrix, min_holdout, df_pivot,
                  None, excluded_control_locations),
    ) as executor:
        futures = executor.map(_evaluate_group_worker, possible_groups)
        for idx, result in enumerate(futures):
            results.append(result)
            if progress_updater:
                progress_updater.progress((idx + 1) / total_groups)
            if status_updater:
                status_updater.text(
                    f"Finding the best groups: {int((idx + 1) / total_groups * 100)}% complete"
                )
            if (idx + 1) % log_interval == 0 or idx == 0 or idx == total_groups - 1:
                logger.info(f"Processed {idx + 1}/{total_groups} groups")
    logger.info(f"All groups processed. Results count: {len(results)}")
    # Two-stage single-cell selection (ISS-1):
    #   Stage 1 — rank candidates by out-of-sample fit (holdout SMAPE r[3], tie-break
    #             scaled_l2 r[8]); keep the top_k_finalists.
    #   Stage 2 — falsify each finalist on placebo windows DISJOINT from the ranking
    #             window (skip_recent=1) and keep those passing BOTH gates (FPR and
    #             abs_lift_in_zero). Choose the best-fitting survivor; if none pass,
    #             keep the best-SMAPE finalist marked gate_passed=False (WARNING).
    results_by_size = {}
    fpr_threshold = fpr_gate_multiplier * significance_level
    for size in range(min_elements_in_treatment, max_group_size + 1):
        size_results = [
            r for r in results
            if r is not None and len(r[0]) == size and r[9] is not None
        ]
        if not size_results:
            continue

        finalists = sorted(size_results, key=lambda x: (x[3], x[8]))[:top_k_finalists]

        evaluated = []
        for r in finalists:
            fals = compute_falsification_metrics(
                y_real=r[4],
                donors=r[9],
                skip_recent=1,
                significance_level=significance_level,
                n_power_simulations=n_power_simulations_falsification,
                n_permutations_per_test=n_permutations_falsification,
                alternative=alternative,
                inference_type=inference_type,
            )
            abs_lift = fals["abs_lift_in_zero"]
            fpr = fals["false_positive_rate"]
            fpr_ok = fpr <= fpr_threshold
            abs_ok = (max_abs_lift_in_zero is None) or (abs_lift <= max_abs_lift_in_zero)
            evaluated.append(
                {"r": r, "abs_lift": abs_lift, "fpr": fpr, "fpr_ok": fpr_ok,
                 "abs_ok": abs_ok, "passed": fpr_ok and abs_ok}
            )

        survivors = [e for e in evaluated if e["passed"]]
        if survivors:
            chosen = min(survivors, key=lambda e: (e["r"][3], e["r"][8]))
            gate_passed = True
        else:
            # Fallback: keep the best out-of-sample fit, tie-break by smaller placebo bias.
            chosen = min(evaluated, key=lambda e: (e["r"][3], e["abs_lift"]))
            gate_passed = False
            logger.warning(
                f"size {size}: no finalist passed both gates "
                f"(FPR<= {fpr_threshold:.3f}, abs_lift<= {max_abs_lift_in_zero}); "
                f"keeping best-SMAPE candidate with gate_passed=False"
            )

        r = chosen["r"]
        treatment_Y = data[data["location"].isin(r[0])]["Y"].sum()
        holdout_percentage = (
            round(((total_Y - treatment_Y) / total_Y) * 100, 2) if total_Y > 0 else 0.0
        )

        # ISS-11 wiring (option 1): the candidate SEARCH ran on the fast ridge engine, but the
        # single chosen winner is re-fit once with augmentation="auto" so the reported
        # counterfactual/weights use the better of ridge-on-time / ASCM(lambda*) by holdout fit.
        # cv_folds=0 keeps it to a single auto fit (no nested rolling-origin CV). The placebo
        # gate fields stay as decided by the ridge-based search above. Falls back to the ridge
        # fit if the auto re-eval fails or degenerates.
        # Isolated in a single-threaded-BLAS child so the auto re-fit's ~20 cvxpy solves can't
        # SIGSEGV the main process (see _evaluate_group_isolated). On a None return (child died
        # or timed out) we keep the ridge result `r` from the search.
        report = r
        auto_r = _evaluate_group_isolated((
            r[0], data, total_Y, correlation_matrix, min_holdout, df_pivot,
            None, excluded_control_locations, 0, "auto",
        ))
        if auto_r is not None and auto_r[4] is not None and auto_r[5] is not None:
            report = auto_r

        results_by_size[size] = {
            "Best Treatment Group": report[0],
            "Control Group": report[1],
            "MAPE": report[2],
            "SMAPE": report[3],
            "Actual Target Metric (y)": report[4],
            "Predictions": report[5],
            "Weights": report[6],
            "Holdout Percentage": holdout_percentage,
            "observed_conformity": report[7],
            "Scaled L2 Imbalance": report[8],
            "abs_lift_in_zero": chosen["abs_lift"],
            "false_positive_rate": chosen["fpr"],
            "fpr_gate_passed": chosen["fpr_ok"],
            "abs_lift_gate_passed": chosen["abs_ok"],
            "gate_passed": gate_passed,
        }

    if not results or all(result is None for result in results):
        logger.error("BetterGroups failed: No valid results found for single-cell mode. Check data quality and configuration.")
        return None

    return results_by_size

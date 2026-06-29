import itertools
from math import comb

import numpy as np

from logger_config import get_logger

logger = get_logger("selection")


def select_treatments(similarity_matrix, treatment_size, excluded_locations):
    """
    Selects n combinations of treatments based on a similarity DataFrame, excluding certain states
    from the treatment selection but allowing their inclusion in the control.


    Args:
        similarity_matrix (pd.DataFrame): DataFrame containing correlations between locations in a standard matrix format
        treatment_size (int): Number of treatments to select for each combination.
        excluded_locations (list): List of locations to exclude from the treatment selection.



    Returns:
        list: A list of unique combinations, each combination being a list of states.
    """
    # Filter out empty strings from excluded_locations
    excluded_locations = [loc for loc in excluded_locations if loc.strip()]

    logger.debug(
        f"select_treatments called: treatment_size={treatment_size}, excluded_locations={excluded_locations}"
    )

    missing_locations = [
        location
        for location in excluded_locations
        if location not in similarity_matrix.index
        or location not in similarity_matrix.columns
    ]

    if missing_locations:
        logger.error(
            f"The following locations are not present in the similarity matrix: {missing_locations}"
        )
        raise KeyError(
            f"The following locations are not present in the similarity matrix: {missing_locations}"
        )

    similarity_matrix_filtered = similarity_matrix.loc[
        ~similarity_matrix.index.isin(excluded_locations),
        ~similarity_matrix.columns.isin(excluded_locations),
    ]

    logger.debug(
        f"Filtered similarity matrix shape: {similarity_matrix_filtered.shape}"
    )

    if treatment_size > similarity_matrix_filtered.shape[1]:
        logger.error(
            f"The treatment size ({treatment_size}) exceeds the available number of columns ({similarity_matrix_filtered.shape[1]})."
        )
        raise ValueError(
            f"The treatment size ({treatment_size}) exceeds the available number of columns "
            f"({similarity_matrix_filtered.shape[1]})."
        )

    n = similarity_matrix_filtered.shape[1]
    r = treatment_size
    max_combinations = comb(n, r)

    n_combinations = max_combinations
    if n_combinations > 5000:
        n_combinations = 5000
    # if n_combinations > 2000:
        # n_combinations = 2000

    logger.debug(f"Generating {n_combinations} combinations")

    combinations = set()

    while len(combinations) < n_combinations:
        sample_columns = np.random.choice(
            similarity_matrix_filtered.columns, size=treatment_size, replace=False
        )
        sample_group = tuple(sorted(sample_columns))
        combinations.add(sample_group)

    logger.debug(f"Generated {len(combinations)} unique combinations")
    return [list(comb) for comb in combinations]


def select_controls(
    correlation_matrix, treatment_group, top_k=None,
    excluded_control_locations=None,
):
    """
    Select the donor pool for a treatment group (ISS-6).

    By default (``top_k=None``) returns ALL eligible donors ranked by their mean
    correlation to the treatment group; the synthetic-control simplex (sum(w)=1, w>=0)
    plus the weight filter then perform the joint, sparse selection. This replaces the
    old hard ``min_correlation=0.8`` marginal pre-filter, which could (a) drop a donor
    that is only useful *in combination* with others (suppressor/masking, Fan & Lv) and
    (b) change the donor membership when the data window shifts, causing the lift to
    jump (the window-consistency complaint). An explicit integer ``top_k`` keeps only
    the top-K as an optional cap. Donors with a NaN correlation score are dropped.

    Args:
        correlation_matrix (pd.DataFrame): correlation matrix between locations.
        treatment_group (list): treatment locations.
        top_k (int | None): optional cap on the number of donors (None = all eligible).
        excluded_control_locations (list): locations the user wants out of the control group.

    Returns:
        list: control-group (donor) locations, ranked by mean correlation (desc).
    """
    if excluded_control_locations is None:
        excluded_control_locations = []
    excluded_set = set(treatment_group) | set(excluded_control_locations)

    present = [t for t in treatment_group if t in correlation_matrix.index]
    if not present:
        logger.warning(
            "No treatment location found in correlation matrix; empty control group"
        )
        return []

    # mean correlation of each candidate donor to the treatment group
    scores = correlation_matrix.loc[present].mean(axis=0)
    eligible = scores[~scores.index.isin(excluded_set)].dropna().sort_values(ascending=False)
    if top_k is not None:
        eligible = eligible.head(top_k)

    control_group = eligible.index.tolist()
    logger.debug(
        f"select_controls: {len(control_group)} eligible donors (top_k={top_k})"
    )
    return control_group


def select_treatments_exclusive(
    similarity_matrix,
    treatment_size,
    excluded_locations,
    used_treatment_locations=None,
    allowed_locations=None,
    seed=None,
    max_candidates_cap=5000,
):
    """
    Improved treatment selection for multi-cell mode ensuring treatment location exclusivity.
    Control locations can be reused across cells.

    Args:
        similarity_matrix (pd.DataFrame): DataFrame containing correlations between locations
        treatment_size (int): Number of treatments to select for each combination
        excluded_locations (list): List of locations to exclude globally
        used_treatment_locations (set): Set of treatment locations already used in previous cells
        allowed_locations (list, optional): Restrict generated treatment candidates to this subset of locations (a partition slice). If None, all available locations are used.
        seed (int, optional): Seed for deterministic random sampling when the candidate pool is too large to enumerate. None leaves the RNG unseeded.
        max_candidates_cap (int): When the number of possible combinations is at or below this, all combinations are enumerated exhaustively (deterministic); above it, seeded random sampling is used. Default 5000.

    Returns:
        list: A list of unique combinations, each combination being a list of states
    """
    if used_treatment_locations is None:
        used_treatment_locations = set()

    # Filter out empty strings from excluded_locations
    excluded_locations = [loc for loc in excluded_locations if loc.strip()]
    all_excluded = set(excluded_locations) | used_treatment_locations

    logger.debug(
        f"select_treatments_exclusive: treatment_size={treatment_size}, excluded={len(all_excluded)} locations"
    )

    missing_locations = [
        location
        for location in excluded_locations
        if location not in similarity_matrix.index
        or location not in similarity_matrix.columns
    ]

    if missing_locations:
        logger.error(
            f"The following locations are not present in the similarity matrix: {missing_locations}"
        )
        raise KeyError(
            f"The following locations are not present in the similarity matrix: {missing_locations}"
        )

    similarity_matrix_filtered = similarity_matrix.loc[
        ~similarity_matrix.index.isin(all_excluded),
        ~similarity_matrix.columns.isin(all_excluded),
    ]

    cols = list(similarity_matrix_filtered.columns)
    if allowed_locations is not None:
        allowed = set(allowed_locations)
        cols = [c for c in cols if c in allowed]

    n = len(cols)
    r = treatment_size
    if r > n:
        logger.warning(
            f"Treatment size ({r}) exceeds available locations ({n}), skipping"
        )
        return []

    max_combinations = comb(n, r)
    if max_combinations == 0:
        logger.warning(f"No combinations possible for size {r} with available locations")
        return []

    # Exhaustive when feasible -> deterministic AND complete (no missed combinations).
    if max_combinations <= max_candidates_cap:
        return [list(c) for c in itertools.combinations(sorted(cols), r)]

    # Large pool: seeded random sampling for reproducibility.
    rng = np.random.default_rng(seed)
    combinations = set()
    attempts = 0
    max_attempts = max_candidates_cap * 10
    while len(combinations) < max_candidates_cap and attempts < max_attempts:
        sample_columns = rng.choice(cols, size=r, replace=False)
        combinations.add(tuple(sorted(sample_columns)))
        attempts += 1

    logger.debug(f"Generated {len(combinations)} sampled combinations for size {r}")
    return [list(c) for c in combinations]


def select_controls_exclusive(
    correlation_matrix,
    treatment_group,
    used_treatment_locations=None,
    excluded_locations=None,
    excluded_control_locations=None,
    top_k=None,
):
    # NOTE: `excluded_locations` is a GLOBAL exclusion list used in multi-cell mode
    # as a safety mechanism. When a user excludes a location (e.g. Puebla) we must
    # keep it out of BOTH treatment and control across every cell, because the
    # random control picker in one cell could otherwise re-select a location that
    # another cell is using as treatment. `excluded_control_locations` is the
    # explicit control-only exclusion list surfaced in the UI as an advanced option.
    # ISS-6: top_k=None returns ALL eligible donors (simplex selects); top_k caps.
    if used_treatment_locations is None:
        used_treatment_locations = set()
    if excluded_locations is None:
        excluded_locations = []
    if excluded_control_locations is None:
        excluded_control_locations = []

    all_excluded = (
        set(treatment_group)
        | set(used_treatment_locations)
        | set(excluded_locations)
        | set(excluded_control_locations)
    )

    present = [t for t in treatment_group if t in correlation_matrix.index]
    if not present:
        logger.warning(
            "No treatment location found in correlation matrix; empty control group"
        )
        return []

    scores = correlation_matrix.loc[present].mean(axis=0)
    eligible = scores[~scores.index.isin(all_excluded)].dropna().sort_values(ascending=False)
    if top_k is not None:
        eligible = eligible.head(top_k)
    final_control = eligible.index.tolist()

    # Final verification: ensure no treatment locations leaked into the control group
    all_treatment = set(treatment_group) | set(used_treatment_locations)
    overlap_check = set(final_control) & all_treatment
    if overlap_check:
        logger.error(f"CRITICAL ERROR: Control group contains treatment locations: {overlap_check}")
        final_control = [loc for loc in final_control if loc not in all_treatment]
        logger.warning(f"Removed overlap, final control group: {final_control}")

    logger.debug(
        f"select_controls_exclusive: {len(final_control)} eligible donors (top_k={top_k})"
    )
    return final_control

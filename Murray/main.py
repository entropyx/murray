import concurrent.futures
from math import comb
import numpy as np
import cvxpy as cp
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, RegressorMixin
from Murray.plots import plot_mde_results
from Murray.auxiliary import market_correlations, handle_duplicates
from sklearn.linear_model import Ridge
from logger_config import get_logger
import os
import warnings


warnings.filterwarnings("ignore", message=".*ScriptRunContext.*", category=UserWarning)

logger = get_logger("main")


def is_streamlit_context():
    """Check if we're running in a Streamlit context."""
    return (
        "STREAMLIT_SERVER_PORT" in os.environ
        or "STREAMLIT_SERVER_ADDRESS" in os.environ
    )


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
    correlation_matrix, treatment_group, min_correlation=0.8, fallback_n=1
):
    """
    Dynamically selects control group states based on correlation values.
    If no state meets the min_correlation, it selects the top `fallback_n` correlated states.

    Args:
        correlation_matrix (pd.DataFrame): Correlation matrix between states.
        treatment_group (list): List of states in the treatment group.
        min_correlation (float): Minimum correlation threshold to consider a state as part of the control group.
        fallback_n (int): Number of top correlated states to select if no state meets the min_correlation.

    Returns:
        list: List of states selected as the control group.
    """
    logger.debug(
        f"select_controls called: treatment_group={treatment_group}, min_correlation={min_correlation}"
    )

    control_group = set()

    for treatment_location in treatment_group:
        if treatment_location not in correlation_matrix.index:
            logger.warning(
                f"Treatment location {treatment_location} not found in correlation matrix"
            )
            continue
        treatment_row = correlation_matrix.loc[treatment_location]

        similar_states = (
            treatment_row[
                (treatment_row >= min_correlation)
                & (~treatment_row.index.isin(treatment_group))
            ]
            .sort_values(ascending=False)
            .index.tolist()
        )

        if not similar_states:
            logger.debug(
                f"No states meet min_correlation {min_correlation} for {treatment_location}, using fallback"
            )
            similar_states = (
                treatment_row[~treatment_row.index.isin(treatment_group)]
                .sort_values(ascending=False)
                .head(fallback_n)
                .index.tolist()
            )

        control_group.update(similar_states)
        logger.debug(
            f"Added {len(similar_states)} control states for {treatment_location}"
        )

    logger.debug(f"Final control group: {list(control_group)}")
    return list(control_group)


class SyntheticControl(BaseEstimator, RegressorMixin):
    def __init__(
        self,
        regularization_strength_l1=0.1,
        regularization_strength_l2=0.1,
        seasonality=None,
        delta=1.0,
        use_ridge_adjustment=False,
        ridge_alpha=1.0,
    ):
        """
        Args:
            regularization_strength_l1: Strength of L1 regularization (not used in this example, but can be expanded).
            regularization_strength_l2: Strength of L2 regularization in the optimization of the weights.
            seasonality: DataFrame with the calculated seasonality, indexed by time.
            delta: Parameter for the Huber loss function (not used in this example).
            use_ridge_adjustment: If True, adjusts the pre-intervention residual with Ridge regression.
            ridge_alpha: Parameter alpha for Ridge regression (regularization strength).
        """
        self.regularization_strength_l1 = regularization_strength_l1
        self.regularization_strength_l2 = regularization_strength_l2
        self.seasonality = seasonality
        self.delta = delta
        self.use_ridge_adjustment = use_ridge_adjustment
        self.ridge_alpha = ridge_alpha

    def _prepare_data(self, X, time_index=None):
        """
        Combines the original features with seasonality if available.

        Args:
            X: Input features
            time_index: Time index in case of using seasonality

        Returns:
            numpy.ndarray: Processed features matrix
        """
        X = np.array(X)
        if self.seasonality is not None and time_index is not None:
            if len(time_index) != X.shape[0]:
                raise ValueError("The size of the time index does not match X.")
            seasonal_values = self.seasonality.loc[time_index].to_numpy().reshape(-1, 1)
            X = np.hstack([X, seasonal_values])
        return X

    def squared_loss(self, x):
        """Calculates the quadratic loss."""
        return cp.sum_squares(x)

    def fit(self, X, y, time_train=None):
        """
        Fits the synthetic control model.

        Args:
            X: Training features
            y: Target values
            time_train (optional): Time vector or indices for the training data, required if Ridge adjustment is enabled.

        Returns:
            self: Fitted model
        """

        X_proc = self._prepare_data(X, time_index=time_train)
        y = np.ravel(y)

        if X_proc.shape[0] != y.shape[0]:
            raise ValueError("The number of rows in X must match the size of y.")

        w = cp.Variable(X_proc.shape[1])
        errors = X_proc @ w - y

        regularization_l2 = self.regularization_strength_l2 * cp.norm2(w)
        objective = cp.Minimize(self.squared_loss(errors) + regularization_l2)
        constraints = [cp.sum(w) == 1, w >= 0]
        problem = cp.Problem(objective, constraints)
        problem.solve(solver=cp.SCS, verbose=False)

        if problem.status != cp.OPTIMAL:
            problem.solve(solver=cp.ECOS, verbose=False)

        if problem.status != cp.OPTIMAL:
            raise ValueError(
                "The optimization did not converge. Status: " + problem.status
            )

        self.X_ = X_proc
        self.y_ = y
        self.w_ = w.value
        self.is_fitted_ = True

        self.synthetic_prediction_ = X_proc.dot(self.w_)

        if self.use_ridge_adjustment:
            if time_train is None:
                raise ValueError("The time vector is required for Ridge adjustment.")
            self.residuals_ = y - self.synthetic_prediction_
            time_train = np.array(time_train).reshape(-1, 1)
            self.ridge_model_ = Ridge(alpha=self.ridge_alpha)
            self.ridge_model_.fit(time_train, self.residuals_)
        return self

    def predict(self, X, time_index=None):
        """
        Performs prediction using synthetic control. If Ridge adjustment is enabled and a time vector is provided,
        the prediction is adjusted with the predicted residual.

        Args:
            X: Test features
            time_index (optional): Time vector for the test data

        Returns:
            tuple: (predictions, weights)
                - predictions: numpy.ndarray with the final predictions
                - weights: numpy.ndarray with the fitted weights
        """
        if not self.is_fitted_:
            raise ValueError("The model has not been fitted yet. Call 'fit' first.")

        X_proc = self._prepare_data(X, time_index=time_index)
        base_prediction = X_proc.dot(self.w_)

        if self.use_ridge_adjustment:
            if time_index is None:
                raise ValueError(
                    "The time vector is required to predict with the Ridge adjustment."
                )
            time_index = np.array(time_index).reshape(-1, 1)
            ridge_adjustment = self.ridge_model_.predict(time_index)
            return base_prediction + ridge_adjustment, self.w_

        return base_prediction, self.w_

    def filter_controls_by_weights(self, control_group, min_weight_threshold=0.001):
        """
        Filters control locations based on their weights, removing those with very small contributions.

        Args:
            control_group (list): List of control location names
            min_weight_threshold (float): Minimum weight threshold to keep a control location

        Returns:
            tuple: (filtered_control_group, filtered_weights)
                - filtered_control_group: List of control locations with significant weights
                - filtered_weights: Array of weights for the filtered control locations
        """
        if not self.is_fitted_:
            raise ValueError("The model has not been fitted yet. Call 'fit' first.")

        if len(control_group) != len(self.w_):
            raise ValueError(
                "The number of control locations must match the number of weights."
            )

        significant_indices = np.where(self.w_ >= min_weight_threshold)[0]

        if len(significant_indices) == 0:

            significant_indices = [np.argmax(self.w_)]

        filtered_control_group = [control_group[i] for i in significant_indices]
        filtered_weights = self.w_[significant_indices]

        if np.sum(filtered_weights) > 0:
            filtered_weights = filtered_weights / np.sum(filtered_weights)

        return filtered_control_group, filtered_weights


def smape(A, F):
    denominator = np.abs(A) + np.abs(F)
    denominator = np.where(denominator == 0, 1e-8, denominator)
    return 100 / len(A) * np.sum(2 * np.abs(F - A) / denominator)


def evaluate_group(
    treatment_group, data, total_Y, correlation_matrix, min_holdout, df_pivot
):
    """
    Evaluates a treatment group and returns error metrics.
    """
    logger.debug(f"Starting evaluation for treatment group: {treatment_group}")

    treatment_Y = data[data["location"].isin(treatment_group)]["Y"].sum()
    holdout_percentage = (1 - (treatment_Y / total_Y)) * 100

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
        min_correlation=0.8,
    )
    logger.debug(f"Control group selected: {control_group}")

    if not control_group:
        logger.warning(f"No control group found for treatment group: {treatment_group}")
        return (treatment_group, [], float("inf"), float("inf"), None, None, None, None)

    logger.debug("Preparing data for synthetic control")
    X = df_pivot[control_group].values
    y = df_pivot[treatment_group].sum(axis=1).values

    time_index = np.arange(len(df_pivot))

    logger.debug("Scaling data")
    scaler_x = MinMaxScaler()
    scaler_y = MinMaxScaler()

    X_scaled = scaler_x.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))

    split_index = int(len(X_scaled) * 0.8)

    X_train, X_test = X_scaled[:split_index], X_scaled[split_index:]
    y_train, y_test = y_scaled[:split_index], y_scaled[split_index:]

    time_train = time_index[:split_index]
    time_test = time_index[split_index:]

    logger.debug("Fitting synthetic control model")
    model = SyntheticControl(use_ridge_adjustment=True, ridge_alpha=1.0)
    model.fit(X_train, y_train, time_train=time_train)
    logger.debug("Model fitted successfully")

    logger.debug("Making predictions")
    counterfactual_test, weights = model.predict(X_test, time_index=time_test)
    counterfactual_full, weights = model.predict(X_scaled, time_index=time_index)
    counterfactual_full = counterfactual_full.reshape(-1, 1)
    counterfactual_full_original = scaler_y.inverse_transform(counterfactual_full)
    y_original = scaler_y.inverse_transform(y_scaled)
    counterfactual_full_original = counterfactual_full_original.flatten()
    y_original = y_original.flatten()

    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    logger.debug("Calculating metrics")
    MAPE = (
        np.mean(
            np.abs(
                (y_original[split_index:] - counterfactual_full_original[split_index:])
                / (y_original[split_index:] + 1e-10)
            )
        )
        * 100
    )
    SMAPE_value = smape(
        y_original[split_index:], counterfactual_full_original[split_index:]
    )
    observed_conformity = np.mean(y_original - counterfactual_full_original)

    return (
        treatment_group,
        filtered_control_group,
        MAPE,
        SMAPE_value,
        y_original,
        counterfactual_full_original,
        filtered_weights,
        observed_conformity,
    )


def select_treatments_exclusive(
    similarity_matrix, treatment_size, excluded_locations, used_treatment_locations=None
):
    """
    Selects treatments excluding both globally excluded locations and previously used treatment locations.
    This function is used specifically for multi-cell mode to ensure treatment location exclusivity.
    Control locations can be reused across cells.

    Args:
        similarity_matrix (pd.DataFrame): DataFrame containing correlations between locations
        treatment_size (int): Number of treatments to select for each combination
        excluded_locations (list): List of locations to exclude globally
        used_treatment_locations (set): Set of treatment locations already used in previous cells

    Returns:
        list: A list of unique combinations, each combination being a list of states
    """
    if used_treatment_locations is None:
        used_treatment_locations = set()

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

    logger.debug(
        f"Filtered similarity matrix shape: {similarity_matrix_filtered.shape}"
    )

    if treatment_size > similarity_matrix_filtered.shape[1]:
        logger.warning(
            f"Treatment size ({treatment_size}) exceeds available locations ({similarity_matrix_filtered.shape[1]}), skipping"
        )
        return []

    n = similarity_matrix_filtered.shape[1]
    r = treatment_size
    max_combinations = comb(n, r)

    n_combinations = min(max_combinations, 5000)

    if n_combinations == 0:
        logger.warning(
            f"No combinations possible for size {treatment_size} with available locations"
        )
        return []

    logger.debug(f"Generating {n_combinations} combinations for size {treatment_size}")

    combinations = set()
    attempts = 0
    max_attempts = n_combinations * 10

    while len(combinations) < n_combinations and attempts < max_attempts:
        sample_columns = np.random.choice(
            similarity_matrix_filtered.columns, size=treatment_size, replace=False
        )
        sample_group = tuple(sorted(sample_columns))
        combinations.add(sample_group)
        attempts += 1

    logger.debug(
        f"Generated {len(combinations)} unique combinations for size {treatment_size}"
    )
    return [list(comb) for comb in combinations]


def select_controls_exclusive(
    correlation_matrix,
    treatment_group,
    used_treatment_locations=None,
    excluded_locations=None,
    min_correlation=0.8,
    fallback_n=1,
):
    """
    Dynamically selects control group states based on correlation values.
    This function is used specifically for multi-cell mode with the following exclusion rules:
    - Excludes current treatment group locations
    - Excludes globally excluded locations
    - Excludes locations that have been used as treatment in previous cells
    - ALLOWS reuse of control locations from previous cells

    Args:
        correlation_matrix (pd.DataFrame): Correlation matrix between states.
        treatment_group (list): List of states in the treatment group.
        used_treatment_locations (set): Set of treatment locations already used in previous cells.
        excluded_locations (list): List of globally excluded locations.
        min_correlation (float): Minimum correlation threshold to consider a state as part of the control group.
        fallback_n (int): Number of top correlated states to select if no state meets the min_correlation.

    Returns:
        list: List of states selected as the control group.
    """
    if used_treatment_locations is None:
        used_treatment_locations = set()
    if excluded_locations is None:
        excluded_locations = []

    logger.debug(
        f"select_controls_exclusive called: treatment_group={treatment_group}, used_treatment_locations={len(used_treatment_locations)}, excluded_locations={len(excluded_locations)}"
    )

    control_group = set()
    all_excluded = (
        set(treatment_group) | used_treatment_locations | set(excluded_locations)
    )

    for treatment_location in treatment_group:
        if treatment_location not in correlation_matrix.index:
            logger.warning(
                f"Treatment location {treatment_location} not found in correlation matrix"
            )
            continue
        treatment_row = correlation_matrix.loc[treatment_location]

        available_correlations = treatment_row[~treatment_row.index.isin(all_excluded)]

        similar_states = (
            available_correlations[available_correlations >= min_correlation]
            .sort_values(ascending=False)
            .index.tolist()
        )

        if not similar_states:
            logger.debug(
                f"No available states meet min_correlation {min_correlation} for {treatment_location}, using fallback"
            )
            similar_states = (
                available_correlations.sort_values(ascending=False)
                .head(fallback_n)
                .index.tolist()
            )

        control_group.update(similar_states)
        logger.debug(
            f"Added {len(similar_states)} control states for {treatment_location}"
        )

    logger.debug(f"Final control group: {list(control_group)}")
    return list(control_group)


def evaluate_group_exclusive(
    treatment_group,
    data,
    total_Y,
    correlation_matrix,
    min_holdout,
    df_pivot,
    used_treatment_locations=None,
    excluded_locations=None,
):
    """
    Evaluates a treatment group with location exclusivity for multi-cell mode.
    """
    logger.debug(
        f"Starting exclusive evaluation for treatment group: {treatment_group}"
    )

    treatment_Y = data[data["location"].isin(treatment_group)]["Y"].sum()
    holdout_percentage = (1 - (treatment_Y / total_Y)) * 100

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
        min_correlation=0.8,
    )
    logger.debug(f"Control group selected: {control_group}")

    if not control_group:
        logger.warning(f"No control group found for treatment group: {treatment_group}")
        return (treatment_group, [], float("inf"), float("inf"), None, None, None, None)

    logger.debug("Preparing data for synthetic control")
    X = df_pivot[control_group].values
    y = df_pivot[treatment_group].sum(axis=1).values

    time_index = np.arange(len(df_pivot))

    logger.debug("Scaling data")
    scaler_x = MinMaxScaler()
    scaler_y = MinMaxScaler()

    X_scaled = scaler_x.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))

    split_index = int(len(X_scaled) * 0.8)

    X_train, X_test = X_scaled[:split_index], X_scaled[split_index:]
    y_train, y_test = y_scaled[:split_index], y_scaled[split_index:]

    time_train = time_index[:split_index]
    time_test = time_index[split_index:]

    logger.debug("Fitting synthetic control model")
    model = SyntheticControl(use_ridge_adjustment=True, ridge_alpha=1.0)
    model.fit(X_train, y_train, time_train=time_train)
    logger.debug("Model fitted successfully")

    logger.debug("Making predictions")
    counterfactual_test, weights = model.predict(X_test, time_index=time_test)
    counterfactual_full, weights = model.predict(X_scaled, time_index=time_index)
    counterfactual_full = counterfactual_full.reshape(-1, 1)
    counterfactual_full_original = scaler_y.inverse_transform(counterfactual_full)
    y_original = scaler_y.inverse_transform(y_scaled)
    counterfactual_full_original = counterfactual_full_original.flatten()
    y_original = y_original.flatten()

    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    logger.debug("Calculating metrics")
    MAPE = (
        np.mean(
            np.abs(
                (y_original[split_index:] - counterfactual_full_original[split_index:])
                / (y_original[split_index:] + 1e-10)
            )
        )
        * 100
    )
    SMAPE_value = smape(
        y_original[split_index:], counterfactual_full_original[split_index:]
    )

    observed_conformity = np.mean(y_original - counterfactual_full_original)

    return (
        treatment_group,
        filtered_control_group,
        MAPE,
        SMAPE_value,
        y_original,
        counterfactual_full_original,
        filtered_weights,
        observed_conformity,
    )


def BetterGroups(
    similarity_matrix,
    excluded_locations,
    data,
    correlation_matrix,
    maximum_treatment_percentage=0.50,
    progress_updater=None,
    status_updater=None,
    multicell_config=None,
    cancellation_callback=None,
):
    """
    Simula posibles grupos de tratamiento y evalúa su desempeño.
    Si multicell_config está presente, usa los sizes y top_n del usuario y guarda los mejores N grupos por size.
    """
    unique_locations = data["location"].unique()
    no_locations = len(unique_locations)
    max_group_size = round(no_locations * 0.45)
    min_elements_in_treatment = round(no_locations * 0.15)
    min_holdout = 100 - (maximum_treatment_percentage * 100)
    total_Y = data["Y"].sum()

    if total_Y == 0:
        return None

    df_pivot = data.pivot(index="time", columns="location", values="Y")

    # --- Multi-cell mode---
    if multicell_config is not None and multicell_config.get("sizes"):
        logger.info(f"Starting multi-cell flexible with location exclusivity")
        sizes = multicell_config["sizes"]
        top_n = multicell_config.get("top_n", 1)
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

            with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
                futures = executor.map(
                    evaluate_group_exclusive,
                    groups,
                    [data] * total_groups,
                    [total_Y] * total_groups,
                    [correlation_matrix] * total_groups,
                    [min_holdout] * total_groups,
                    [df_pivot] * total_groups,
                    [used_treatment_locations] * total_groups,
                    [excluded_locations] * total_groups,
                    chunksize=5,
                )

                for idx, result in enumerate(futures):
                    # Check for cancellation every 10 iterations
                    if idx % 10 == 0 and cancellation_callback and cancellation_callback():
                        logger.info("🚫 SIMULATION CANCELLED: During BetterGroups multi-cell evaluation")
                        executor.shutdown(wait=False)
                        return None
                    results.append(result)
                    current_total = groups_processed_so_far + idx + 1
                    if progress_updater:
                        progress_updater.progress(
                            current_total / total_groups_all_sizes
                        )
                    if status_updater:
                        status_updater.text(
                            f"Evaluando grupos totales: {current_total}/{total_groups_all_sizes} ({int(current_total / total_groups_all_sizes * 100)}%) ⏳"
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
            logger.warning("No valid results for any size in multi-cell mode")
            return None
        return results_by_size

    # --- Single-cell mode ---
    logger.info(f"Starting single-cell mode")
    possible_groups = []
    for size in range(min_elements_in_treatment, max_group_size + 1):
        groups = select_treatments(similarity_matrix, size, excluded_locations)
        possible_groups.extend(groups)

    if not possible_groups:
        return None

    total_groups = len(possible_groups)
    results = []
    log_interval = max(1, total_groups // 10)
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        futures = executor.map(
            evaluate_group,
            possible_groups,
            [data] * total_groups,
            [total_Y] * total_groups,
            [correlation_matrix] * total_groups,
            [min_holdout] * total_groups,
            [df_pivot] * total_groups,
            chunksize=5,
        )
        for idx, result in enumerate(futures):
            # Check for cancellation every 10 iterations
            if idx % 10 == 0 and cancellation_callback and cancellation_callback():
                logger.info("🚫 SIMULATION CANCELLED: During BetterGroups single-cell evaluation")
                executor.shutdown(wait=False)
                return None
            results.append(result)
            if progress_updater:
                progress_updater.progress((idx + 1) / total_groups)
            if status_updater:
                status_updater.text(
                    f"Finding the best groups: {int((idx + 1) / total_groups * 100)}% complete ⏳"
                )
            if (idx + 1) % log_interval == 0 or idx == 0 or idx == total_groups - 1:
                logger.info(f"Processed {idx + 1}/{total_groups} groups")
    logger.info(f"All groups processed. Results count: {len(results)}")
    results_by_size = {}
    for size in range(min_elements_in_treatment, max_group_size + 1):
        best_results = [
            result
            for result in results
            if result is not None and len(result[0]) == size
        ]
        if best_results:
            best_result = min(best_results, key=lambda x: (x[2], -x[3]))
            (
                best_treatment_group,
                best_control_group,
                best_MAPE,
                best_SMAPE,
                y,
                predictions,
                weights,
                observed_conformity,
            ) = best_result

            treatment_Y = data[data["location"].isin(best_treatment_group)]["Y"].sum()

            if total_Y > 0:
                holdout_percentage = ((total_Y - treatment_Y) / total_Y) * 100
            else:
                holdout_percentage = 0.0

            results_by_size[size] = {
                "Best Treatment Group": best_treatment_group,
                "Control Group": best_control_group,
                "MAPE": best_MAPE,
                "SMAPE": best_SMAPE,
                "Actual Target Metric (y)": y,
                "Predictions": predictions,
                "Weights": weights,
                "Holdout Percentage": holdout_percentage,
                "observed_conformity": observed_conformity,
            }

    if not results or all(result is None for result in results):
        return None

    return results_by_size


def apply_lift(y, delta, start_treatment, end_treatment):
    """
    Apply a lift (delta) to a time series y between start_treatment and end_treatment

    Args:
        y (np.array): Original time series
        delta (float): Lift to apply (as a decimal)
        start_treatment (int/str): Start index of treatment period
        end_treatment (int/str): End index of treatment period

    Returns:
        np.array: Time series with lift applied
    """

    y = np.array(y).flatten()
    y_with_lift = y.copy()

    start_idx = max(0, int(start_treatment))
    end_idx = min(len(y_with_lift), int(end_treatment))

    if start_idx < end_idx:
        y_with_lift[start_idx:end_idx] = y_with_lift[start_idx:end_idx] * (1 + delta)
    else:
        raise ValueError("Start index is greater than end index")

    return y_with_lift


def calculate_conformity(y_real, y_control, start_treatment, end_treatment):
    """
    Calculates the conformity between real and control data for conformal inference.

    Args:
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        start_treatment (int): Start index of the treatment period.
        end_treatment (int): End index of the treatment period.

    Returns:
        float: Calculated conformity.
    """
    conformity = np.mean(y_real[start_treatment:end_treatment]) - np.mean(
        y_control[start_treatment:end_treatment]
    )
    return conformity


def compute_residuals(y_treatment, y_control):
    """
    Compute residuals between treatment and control series
    """

    y_treatment = np.array(y_treatment).flatten()
    y_control = np.array(y_control).flatten()
    return y_treatment - y_control


def _block_permutation(data, block_size):
    """
    Perform block-based permutation for time series data to preserve local temporal structure.

    Args:
        data (numpy array): Time series data to permute
        block_size (int): Size of blocks to permute

    Returns:
        numpy array: Block-permuted data
    """
    data = np.array(data).flatten()
    n = len(data)

    blocks = []
    for i in range(0, n, block_size):
        block = data[i : i + block_size]
        blocks.append(block)

    np.random.shuffle(blocks)

    permuted = np.concatenate(blocks)

    return permuted[:n]


def calculate_minimum_sample_size(
    y_real,
    y_control,
    delta,
    period,
    target_power=0.8,
    significance_level=0.05,
    inference_type="iid",
    max_iterations=20,
    tolerance=0.05,
    n_permutations_sample_size=500,
    n_power_simulations_sample_size=30,
):
    """
    Calculate minimum sample size needed to achieve target statistical power.

    Uses iterative approach to find the minimum number of time periods needed
    to achieve the target power level for a given effect size.

    Args:
        y_real (numpy array): Actual target metrics (full series)
        y_control (numpy array): Control metrics (full series)
        delta (float): Effect size to detect
        period (int): Treatment period duration
        target_power (float): Target statistical power (default 0.8)
        significance_level (float): Significance level (default 0.05)
        inference_type (str): Type of inference ("iid" or "block")
        max_iterations (int): Maximum number of iterations
        tolerance (float): Tolerance for power convergence
        n_permutations_sample_size (int): Number of permutations per test for sample size calculation (default 500)
        n_power_simulations_sample_size (int): Number of power simulations for sample size calculation (default 30)

    Returns:
        dict: Dictionary containing minimum sample size, achieved power, and iterations
    """
    logger.info(
        f"Calculating minimum sample size for delta={delta}, target_power={target_power}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    min_size = period + 10  # Minimum size should be larger than treatment period
    max_size = len(y_real)

    for iteration in range(max_iterations):
        current_size = (min_size + max_size) // 2

        if current_size >= len(y_real):
            logger.warning(
                f"Required sample size exceeds available data length ({len(y_real)})"
            )
            break

        y_real_sub = y_real[:current_size]
        y_control_sub = y_control[:current_size]

        try:
            _, power, power_ci, _, _ = simulate_power(
                y_real_sub,
                y_control_sub,
                delta,
                period,
                n_permutations_per_test=n_permutations_sample_size,
                significance_level=significance_level,
                test_type="sum",
                inference_type=inference_type,
                n_power_simulations=n_power_simulations_sample_size,
            )

            logger.debug(
                f"Iteration {iteration + 1}: size={current_size}, power={power:.3f}, target={target_power}"
            )

            if abs(power - target_power) <= tolerance:
                logger.info(
                    f"Converged at iteration {iteration + 1}: size={current_size}, power={power:.3f}"
                )
                return {
                    "minimum_sample_size": current_size,
                    "achieved_power": power,
                    "power_ci": power_ci,
                    "iterations": iteration + 1,
                    "converged": True,
                }

            if power < target_power:
                min_size = current_size + 1
            else:
                max_size = current_size - 1

        except Exception as e:
            logger.error(
                f"Error in sample size calculation at iteration {iteration + 1}: {str(e)}"
            )
            break

        if min_size >= max_size:
            break

    final_size = min(max_size, len(y_real))
    try:
        _, final_power, final_ci, _, _ = simulate_power(
            y_real[:final_size],
            y_control[:final_size],
            delta,
            period,
            n_permutations_per_test=n_permutations_sample_size,
            significance_level=significance_level,
            test_type="sum",
            inference_type=inference_type,
            n_power_simulations=n_power_simulations_sample_size,
        )

        logger.info(
            f"Sample size calculation completed: size={final_size}, power={final_power:.3f} (target={target_power})"
        )
        return {
            "minimum_sample_size": final_size,
            "achieved_power": final_power,
            "power_ci": final_ci,
            "iterations": max_iterations,
            "converged": False,
        }

    except Exception as e:
        logger.error(f"Final power calculation failed: {str(e)}")
        return {
            "minimum_sample_size": len(y_real),
            "achieved_power": None,
            "power_ci": None,
            "iterations": max_iterations,
            "converged": False,
        }


def simulate_power(
    y_real,
    y_control,
    delta,
    period,
    n_permutations_per_test=3000,
    significance_level=0.05,
    test_type="sum",
    inference_type="iid",
    stat_func=None,
    n_power_simulations=40,
    block_size=5,
):
    """
    Simulates statistical power using Monte Carlo simulation with permutation tests.

    Power is calculated by:
    1. Simulating multiple datasets under the alternative hypothesis (with effect)
    2. For each simulated dataset, running a permutation test
    3. Calculating the proportion of tests that reject the null hypothesis

    Args:
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        delta (float): Effect size applied.
        period (int): Duration of the treatment period.
        n_permutations_per_test (int): Number of permutations per test.
        significance_level (float): Significance level.
        test_type (str): Statistical test type ("sum", "mean_diff", "t_test", "median_diff").
        inference_type (str): Type of inference ("iid" or "block").
        stat_func (callable): Custom test statistic function.
        n_power_simulations (int): Number of Monte Carlo simulations for power calculation.
        block_size (int): Block size for block-based permutation.

    Returns:
        tuple: Delta, statistical power, confidence interval, and sample adjusted series.
    """
    logger.debug(
        f"Starting simulate_power: delta={delta}, period={period}, n_permutations_per_test={n_permutations_per_test}, n_power_simulations={n_power_simulations}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    start_treatment = len(y_real) - period
    end_treatment = start_treatment + period

    logger.debug(f"Treatment period: {start_treatment} to {end_treatment}")

    # Default test statistic functions
    if stat_func is None:
        if test_type == "mean_diff":
            stat_func = lambda x: np.mean(x)
        elif test_type == "t_test":
            stat_func = lambda x: (
                np.mean(x) / (np.std(x) / np.sqrt(len(x))) if np.std(x) > 0 else 0
            )
        elif test_type == "median_diff":
            stat_func = lambda x: np.median(x)
        else:  # default sum
            stat_func = lambda x: np.sum(x)

    # Monte Carlo power simulation
    rejected_tests = 0
    p_values = []

    for sim in range(n_power_simulations):
        if sim % 50 == 0 and sim > 0:
            logger.debug(f"Completed {sim}/{n_power_simulations} power simulations")

        # Add noise to make each simulation slightly different
        noise_scale = np.std(y_real) * 0.05  # 5% of data std as noise
        y_real_noisy = y_real + np.random.normal(0, noise_scale, len(y_real))
        y_control_noisy = y_control + np.random.normal(0, noise_scale, len(y_control))

        # Apply effect
        y_with_lift = apply_lift(y_real_noisy, delta, start_treatment, end_treatment)
        residuals = compute_residuals(y_with_lift, y_control_noisy)
        treatment_residuals = residuals[start_treatment:]

        observed_stat = stat_func(treatment_residuals)

        # Permutation test
        null_stats = []
        for i in range(n_permutations_per_test):
            if inference_type == "block":
                # Block-based permutation for time series
                permuted_residuals = _block_permutation(residuals, block_size)
            else:
                # IID permutation
                permuted_residuals = np.random.permutation(residuals)

            permuted = permuted_residuals[start_treatment:]
            null_stats.append(stat_func(permuted))

        null_stats = np.array(null_stats)

        # Two-sided test
        p_value = np.mean(np.abs(null_stats) >= np.abs(observed_stat))
        p_values.append(p_value)

        if p_value < significance_level:
            rejected_tests += 1

    power = rejected_tests / n_power_simulations

    # Calculate confidence interval for power estimate
    power_se = np.sqrt(power * (1 - power) / n_power_simulations)
    power_ci = (max(0, power - 1.95 * power_se), min(1, power + 1.95 * power_se))

    y_with_lift_sample = apply_lift(y_real, delta, start_treatment, end_treatment)

    logger.debug(
        f"Power simulation completed: power={power:.4f}, CI=({power_ci[0]:.4f}, {power_ci[1]:.4f}), mean p-value={np.mean(p_values):.4f}"
    )

    return delta, power, power_ci, y_with_lift_sample, np.mean(p_values)


def run_simulation(
    delta,
    y_real,
    y_control,
    period,
    n_permutations_per_test,
    significance_level,
    test_type="sum",
    inference_type="iid",
    size_block=None,
    n_power_simulations=40,
):
    """
    Wrapper function to run a single simulation of statistical power.
    """
    logger.debug(
        f"Starting simulation: delta={delta}, period={period}, n_permutations_per_test={n_permutations_per_test}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    try:
        result = simulate_power(
            y_real=y_real,
            y_control=y_control,
            delta=delta,
            period=period,
            n_permutations_per_test=n_permutations_per_test,
            significance_level=significance_level,
            test_type=test_type,
            inference_type=inference_type,
            block_size=size_block if size_block else 5,
            n_power_simulations=n_power_simulations,
        )
        return result
    except Exception as e:
        logger.error(f"Simulation failed for delta={delta}, period={period}: {str(e)}")
        raise


def evaluate_sensitivity(
    results_by_size,
    deltas,
    periods,
    n_permutations_per_test,
    significance_level=0.05,
    test_type="sum",
    inference_type="iid",
    size_block=None,
    progress_bar=None,
    status_text=None,
    n_power_simulations=40,
    cancellation_callback=None,
):
    """
    Evaluates sensitivity of results to different treatment periods and deltas using permutations.

    Args:
        results_by_size (dict): Results organized by sample size.
        deltas (list): List of delta values to evaluate.
        periods (list): List of treatment periods to evaluate.
        n_permutations (int): Number of permutations.
        significance_level (float): Significance level.
        test_type (str): Statistical test type ("sum", "mean_diff", "t_test", "median_diff").
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int): Size of blocks for block shuffling (if applicable).

    Returns:
        dict: Sensitivity results by size and period.
        dict: Adjusted series for each delta and period.
    """

    sensitivity_results = {}
    lift_series = {}

    total_steps = sum(len(periods) * len(deltas) for _ in results_by_size)
    step = 0

    for size, result in results_by_size.items():
        if cancellation_callback and cancellation_callback():
            logger.info("🚫 SIMULATION CANCELLED: During evaluate_sensitivity")
            return None, None

        if isinstance(result, list):
            if not result:
                logger.warning(f"Skipping size {size} - no groups available")
                continue
            actual_result = result[0]
        else:
            actual_result = result

        if (
            "Actual Target Metric (y)" not in actual_result
            or "Predictions" not in actual_result
            or actual_result["Actual Target Metric (y)"] is None
            or actual_result["Predictions"] is None
        ):
            logger.warning(f"Skipping size {size} due to missing or null values")
            continue

        y_real = np.array(actual_result["Actual Target Metric (y)"]).flatten()
        y_control = np.array(actual_result["Predictions"]).flatten()

        results_by_period = {}

        for period in periods:
            if cancellation_callback and cancellation_callback():
                logger.info("🚫 SIMULATION CANCELLED: During period evaluation")
                return None, None
            results = []

            for delta in deltas:
                if cancellation_callback and cancellation_callback():
                    logger.info("🚫 SIMULATION CANCELLED: During delta evaluation")
                    return None, None
                logger.debug(
                    f"Running simulation for size={size}, period={period}, delta={delta}"
                )
                res = run_simulation(
                    delta,
                    y_real,
                    y_control,
                    period,
                    n_permutations_per_test,
                    significance_level,
                    test_type,
                    inference_type,
                    size_block,
                    n_power_simulations,
                )
                results.append(res)

                step += 1
                if is_streamlit_context() and progress_bar:
                    try:
                        progress_bar.progress(min(step / total_steps, 1.0))
                    except Exception as e:
                        logger.debug(f"Progress update failed: {e}")
                if is_streamlit_context() and status_text:
                    try:
                        status_text.text(
                            f"Evaluating groups: {int((step / total_steps) * 100)}% complete ⏳"
                        )
                    except Exception as e:
                        logger.debug(f"Status update failed: {e}")

            statistical_power = [
                (res[0], res[1], res[2], res[4]) for res in results
            ]  # (delta, power, power_ci, p_value)
            mde = next(
                (
                    delta
                    for delta, power, ci, p_value in statistical_power
                    if power >= 0.8
                ),
                None,
            )

            p_value = None
            power_ci = None
            power = None
            if mde is not None:
                for delta, power, ci, p_value in statistical_power:
                    if delta == mde:
                        p_value = p_value
                        power_ci = ci
                        power = power
                        break

            # Format values safely for logging
            p_value_str = f"{p_value:.4f}" if p_value is not None else "None"
            power_str = f"{power:.4f}" if power is not None else "None"
            power_ci_str = (
                f"({power_ci[0]:.4f} - {power_ci[1]:.4f})"
                if power_ci is not None
                else "None"
            )

            logger.info(
                f"Period {period} completed for size {size}. MDE found: {mde} with p-value: {p_value_str}, power: {power_str}"
            )

            for delta, _, ci, adjusted_series, p_value in results:
                lift_series[(size, delta, period)] = adjusted_series

            results_by_period[period] = {
                "Statistical Power": statistical_power,
                "MDE": mde,
                "P-Value": p_value,
                "MDE_CI": power_ci,
                "Power": power,
            }

        sensitivity_results[size] = results_by_period

    logger.info("evaluate_sensitivity completed successfully.")
    return sensitivity_results, lift_series


def transform_results_data(results_by_size):
    """
    Transforms the data to ensure compatibility with the heatmap.
    Handles both single-cell (dict of dicts) and multi-cell (dict of lists) results.
    """
    transformed_data = {}

    for size, data in results_by_size.items():
        if isinstance(data, list):
            if data:
                group_data = data[0]
                transformed_data[size] = {
                    "Best Treatment Group": ", ".join(
                        group_data["Best Treatment Group"]
                    ),
                    "Control Group": ", ".join(group_data["Control Group"]),
                    "MAPE": float(group_data["MAPE"]),
                    "SMAPE": float(group_data["SMAPE"]),
                    "Actual Target Metric (y)": (
                        group_data["Actual Target Metric (y)"].tolist()
                        if hasattr(group_data["Actual Target Metric (y)"], "tolist")
                        else group_data["Actual Target Metric (y)"]
                    ),
                    "Predictions": (
                        group_data["Predictions"].tolist()
                        if hasattr(group_data["Predictions"], "tolist")
                        else group_data["Predictions"]
                    ),
                    "Weights": (
                        group_data["Weights"].tolist()
                        if hasattr(group_data["Weights"], "tolist")
                        else group_data["Weights"]
                    ),
                    "Holdout Percentage": float(group_data["Holdout Percentage"]),
                }
        else:
            transformed_data[size] = {
                "Best Treatment Group": ", ".join(data["Best Treatment Group"]),
                "Control Group": ", ".join(data["Control Group"]),
                "MAPE": float(data["MAPE"]),
                "SMAPE": float(data["SMAPE"]),
                "Actual Target Metric (y)": (
                    data["Actual Target Metric (y)"].tolist()
                    if hasattr(data["Actual Target Metric (y)"], "tolist")
                    else data["Actual Target Metric (y)"]
                ),
                "Predictions": (
                    data["Predictions"].tolist()
                    if hasattr(data["Predictions"], "tolist")
                    else data["Predictions"]
                ),
                "Weights": (
                    data["Weights"].tolist()
                    if hasattr(data["Weights"], "tolist")
                    else data["Weights"]
                ),
                "Holdout Percentage": float(data["Holdout Percentage"]),
            }

    return transformed_data


def run_geo_analysis_streamlit_app(
    data,
    maximum_treatment_percentage,
    significance_level,
    deltas_range,
    periods_range,
    excluded_locations,
    progress_bar_1=None,
    status_text_1=None,
    progress_bar_2=None,
    status_text_2=None,
    n_permutations_per_test=3000,
    n_power_simulations=40,
    multicell_config=None,
    test_type="sum",
    inference_type="iid",
    cancellation_callback=None,
):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        excluded_locations (list): List of states to exclude from the analysis.
        maximum_treatment_percentage (float): Maximum treatment percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        n_permutations (int, optional): Number of permutations for sensitivity evaluation. Default is 5000.
        multicell_config (dict, optional): Configuration for multi-cell mode. Default is None.

    Returns:
        fig: MDE visualization figure.
        tuple: Tuple containing periods
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensitivity_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
    """
    logger.info("Starting run_geo_analysis_streamlit_app............")

    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
        print("Simulation in progress........")

    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)

    # Step 1: Generate market correlations
    logger.info("Step 1: Generating market correlations.....")
    if cancellation_callback and cancellation_callback():
        logger.info("🚫 SIMULATION CANCELLED: During market correlations step")
        return None
    correlation_matrix = market_correlations(data)
    logger.info(f"Market correlations generated successfully.")

    # Step 2: Find the best groups for control and treatment
    logger.info("Step 2: Finding best groups for control and treatment.....")
    if cancellation_callback and cancellation_callback():
        logger.info("🚫 SIMULATION CANCELLED: Before BetterGroups step")
        return None
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        maximum_treatment_percentage=maximum_treatment_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1,
        multicell_config=multicell_config,
        cancellation_callback=cancellation_callback,
    )

    if simulation_results is None:
        logger.error("BetterGroups returned None, stopping execution")
        return None

    logger.info(
        f"BetterGroups completed successfully. Results for {len(simulation_results)} sizes"
    )

    # Step 3: Evaluate sensitivity for different deltas and periods
    logger.info("Step 3: Evaluating sensitivity for different deltas and periods.....")
    if cancellation_callback and cancellation_callback():
        logger.info("🚫 SIMULATION CANCELLED: Before sensitivity evaluation step")
        print("🚫 SIMULATION CANCELLED: Before sensitivity evaluation step")
        return None
    sensitivity_results, series_lifts = evaluate_sensitivity(
        simulation_results,
        deltas,
        periods,
        n_permutations_per_test,
        significance_level,
        test_type=test_type,
        inference_type=inference_type,
        progress_bar=progress_bar_2,
        status_text=status_text_2,
        n_power_simulations=n_power_simulations,
        cancellation_callback=cancellation_callback,
    )

    if sensitivity_results is not None:
        logger.info("Sensitivity evaluation completed successfully.")
    else:
        logger.warning("Sensitivity evaluation returned None")

    logger.info("run_geo_analysis_streamlit_app completed successfully")
    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts,
    }


def run_geo_analysis(
    data,
    maximum_treatment_percentage,
    significance_level,
    deltas_range,
    periods_range,
    excluded_locations,
    progress_bar_1=None,
    status_text_1=None,
    progress_bar_2=None,
    status_text_2=None,
    n_permutations_per_test=3000,
    n_power_simulations=40,
    test_type="sum",
    inference_type="iid",
):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        excluded_locations (list): List of states to exclude from the analysis.
        maximum_treatment_percentage (float): Maximum treatment percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        n_permutations (int, optional): Number of permutations for sensitivity evaluation. Default is 5000.

    Returns:
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensitivity_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
    """
    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
        logger.info("Simulation in progress........")

    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)

    # Step 1: Generate market correlations
    correlation_matrix = market_correlations(data)

    # Step 2: Find the best groups for control and treatment
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        maximum_treatment_percentage=maximum_treatment_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1,
    )

    # Step 3: Evaluate sensitivity for different deltas and periods
    sensitivity_results, series_lifts = evaluate_sensitivity(
        simulation_results,
        deltas,
        periods,
        n_permutations_per_test,
        significance_level,
        test_type=test_type,
        inference_type=inference_type,
        progress_bar=progress_bar_2,
        status_text=status_text_2,
        n_power_simulations=n_power_simulations,
    )
    if sensitivity_results is not None:
        logger.info("Complete.")

    # Step 4: Generate MDE visualizations
    fig = plot_mde_results(simulation_results, sensitivity_results, periods)

    fig.show()

    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts,
    }

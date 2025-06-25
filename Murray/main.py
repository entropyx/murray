import concurrent.futures
from math import comb
import numpy as np
import cvxpy as cp
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, RegressorMixin
from Murray.plots import plot_mde_results
from Murray.auxiliary import market_correlations, handle_duplicates
import concurrent.futures
from sklearn.linear_model import Ridge
from logger_config import get_logger
import os
import warnings

# Suppress Streamlit ScriptRunContext warnings
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*", category=UserWarning)

logger = get_logger("main")

def is_streamlit_context():
    """Check if we're running in a Streamlit context."""
    return 'STREAMLIT_SERVER_PORT' in os.environ or 'STREAMLIT_SERVER_ADDRESS' in os.environ

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
    logger.debug(f"select_treatments called: treatment_size={treatment_size}, excluded_locations={excluded_locations}")

    missing_locations = [location for location in excluded_locations if location not in similarity_matrix.index or location not in similarity_matrix.columns]
    

    if missing_locations:
        logger.error(f"The following locations are not present in the similarity matrix: {missing_locations}")
        raise KeyError(f"The following locations are not present in the similarity matrix: {missing_locations}")
    
    

    similarity_matrix_filtered = similarity_matrix.loc[
        ~similarity_matrix.index.isin(excluded_locations),
        ~similarity_matrix.columns.isin(excluded_locations)
    ]
    
    logger.debug(f"Filtered similarity matrix shape: {similarity_matrix_filtered.shape}")

    
    if treatment_size > similarity_matrix_filtered.shape[1]:
        logger.error(f"The treatment size ({treatment_size}) exceeds the available number of columns ({similarity_matrix_filtered.shape[1]}).")
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
        logger.info(f"Limiting combinations from {max_combinations} to {n_combinations}")

    logger.debug(f"Generating {n_combinations} combinations")

    combinations = set()

    while len(combinations) < n_combinations:
        sample_columns = np.random.choice(
            similarity_matrix_filtered.columns,
            size=treatment_size,
            replace=False
        )
        sample_group = tuple(sorted(sample_columns))
        combinations.add(sample_group)

    logger.debug(f"Generated {len(combinations)} unique combinations")
    return [list(comb) for comb in combinations]



def select_controls(correlation_matrix, treatment_group, min_correlation=0.8, fallback_n=1):
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
    logger.debug(f"select_controls called: treatment_group={treatment_group}, min_correlation={min_correlation}")
    
    control_group = set()
    
    for treatment_location in treatment_group:
        if treatment_location not in correlation_matrix.index:
            logger.warning(f"Treatment location {treatment_location} not found in correlation matrix")
            continue
        treatment_row = correlation_matrix.loc[treatment_location]

        
        similar_states = treatment_row[
            (treatment_row >= min_correlation) & (~treatment_row.index.isin(treatment_group))
        ].sort_values(ascending=False).index.tolist()

        if not similar_states:
            logger.debug(f"No states meet min_correlation {min_correlation} for {treatment_location}, using fallback")
            similar_states = (
                treatment_row[~treatment_row.index.isin(treatment_group)]
                .sort_values(ascending=False)
                .head(fallback_n)
                .index.tolist()
            )
            

        control_group.update(similar_states)
        logger.debug(f"Added {len(similar_states)} control states for {treatment_location}")

    logger.debug(f"Final control group: {list(control_group)}")
    return list(control_group)


class SyntheticControl(BaseEstimator, RegressorMixin):
    def __init__(self, 
                 regularization_strength_l1=0.1, 
                 regularization_strength_l2=0.1, 
                 seasonality=None, 
                 delta=1.0,
                 use_ridge_adjustment=False,
                 ridge_alpha=1.0):
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
            raise ValueError("The optimization did not converge. Status: " + problem.status)

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
                raise ValueError("The time vector is required to predict with the Ridge adjustment.")
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
            raise ValueError("The number of control locations must match the number of weights.")
        
        # Find indices where weights are above the threshold
        significant_indices = np.where(self.w_ >= min_weight_threshold)[0]
        
        if len(significant_indices) == 0:
            # If no weights meet the threshold, keep the one with the highest weight
            significant_indices = [np.argmax(self.w_)]
        
        filtered_control_group = [control_group[i] for i in significant_indices]
        filtered_weights = self.w_[significant_indices]
        
        # Renormalize weights to sum to 1
        if np.sum(filtered_weights) > 0:
            filtered_weights = filtered_weights / np.sum(filtered_weights)
        
        return filtered_control_group, filtered_weights


def smape(A, F):
    denominator = np.abs(A) + np.abs(F)
    denominator = np.where(denominator == 0, 1e-8, denominator)
    return 100 / len(A) * np.sum(2 * np.abs(F - A) / denominator)

def evaluate_group(treatment_group, data, total_Y, correlation_matrix, min_holdout, df_pivot):
    """
    Evaluates a treatment group and returns error metrics.
    """
    logger.debug(f"Starting evaluation for treatment group: {treatment_group}")
    
    treatment_Y = data[data['location'].isin(treatment_group)]['Y'].sum()
    holdout_percentage = (1 - (treatment_Y / total_Y)) * 100

    logger.debug(f"Treatment Y: {treatment_Y}, Holdout percentage: {holdout_percentage:.2f}%")

    if holdout_percentage < min_holdout:
        logger.debug(f"Holdout percentage {holdout_percentage:.2f}% below minimum {min_holdout}%, skipping")
        return None

    logger.debug("Selecting control group")
    control_group = select_controls(
        correlation_matrix=correlation_matrix,
        treatment_group=treatment_group,
        min_correlation=0.8
    )
    logger.debug(f"Control group selected: {control_group}")

    if not control_group:
        logger.warning(f"No control group found for treatment group: {treatment_group}")
        return (treatment_group, [], float('inf'), float('inf'), None, None, None, None)

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
    time_test  = time_index[split_index:]

    logger.debug("Fitting synthetic control model")
    model = SyntheticControl(
        use_ridge_adjustment=True,  
        ridge_alpha=1.0             
    )
    model.fit(X_train, y_train, time_train=time_train)
    logger.debug("Model fitted successfully")

    logger.debug("Making predictions")
    counterfactual_test, weights = model.predict(X_test, time_index=time_test)
    counterfactual_full, weights = model.predict(X_scaled, time_index=time_index)
    counterfactual_full = counterfactual_full.reshape(-1,1)
    counterfactual_full_original = scaler_y.inverse_transform(counterfactual_full)
    y_original = scaler_y.inverse_transform(y_scaled)
    counterfactual_full_original = counterfactual_full_original.flatten()
    y_original = y_original.flatten()

    # Filter control group based on weights
    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    logger.debug("Calculating metrics")
    MAPE = np.mean(np.abs((y_original[split_index:] - counterfactual_full_original[split_index:]) / (y_original[split_index:] + 1e-10))) * 100
    SMAPE_value = smape(y_original[split_index:], counterfactual_full_original[split_index:])

    # Calculate observed conformity
    observed_conformity = np.mean(y_original - counterfactual_full_original)

    return (treatment_group, filtered_control_group, MAPE, SMAPE_value, y_original, counterfactual_full_original, filtered_weights, observed_conformity)

def BetterGroups(similarity_matrix, excluded_locations, data, correlation_matrix, maximum_treatment_percentage=0.50, progress_updater=None, status_updater=None):
    """
    Simulates possible treatment groups and evaluates their performance.

    Parameters:
        similarity_matrix (pd.DataFrame): Similarity matrix between locations.
        excluded_locations (list): List of locations to exclude from treatment combinations.
        data (pd.DataFrame): Dataset with columns 'time', 'location', and 'Y'.
        correlation_matrix (pd.DataFrame): Correlation matrix between locations.
        maximum_treatment_percentage (float): Maximum percentage of data to reserve as treatment.
        progress_updater: Function or method to update progress.
        status_updater: Function or method to update status.

    Returns:
        dict: Simulation results, organized by treatment group size.
            Each entry contains the best treatment group, control group, MAPE,
            SMAPE, actual target metric, predictions, weights, and the holdout percentage.
    """
    logger.info("Starting BetterGroups function")
    logger.info(f"Input data shape: {data.shape}")
    logger.info(f"Excluded locations: {excluded_locations}")
    logger.info(f"Maximum treatment percentage: {maximum_treatment_percentage}")

    unique_locations = data['location'].unique()
    no_locations = len(unique_locations)
    logger.info(f"Number of locations: {no_locations}")
    max_group_size = round(no_locations * 0.45)
    logger.info(f"Maximum group size: {max_group_size}")
    min_elements_in_treatment = round(no_locations * 0.15)
    logger.info(f"Minimum elements in treatment: {min_elements_in_treatment}")
    min_holdout = 100 - (maximum_treatment_percentage * 100)
    total_Y = data['Y'].sum()
    logger.info(f"Total Y value: {total_Y}")
    logger.info(f"Minimum holdout percentage: {min_holdout}%")
    
    logger.info(f"Parameters: no_locations={no_locations}, max_group_size={max_group_size}, min_elements_in_treatment={min_elements_in_treatment}")
    logger.info(f"min_holdout={min_holdout}, total_Y={total_Y}")
    
    if total_Y == 0:
        logger.warning("Total Y is zero, returning None")
        return None
    
    logger.info("Creating pivot table")
    
    # Check for duplicate entries and handle them
    data = handle_duplicates(data, subset=['time', 'location'], agg_method='mean')
    
    df_pivot = data.pivot(index='time', columns='location', values='Y')
    logger.info(f"Pivot table created with shape: {df_pivot.shape}")
    
    
    possible_groups = []
    logger.info("Generating possible treatment groups...")
    for size in range(min_elements_in_treatment, max_group_size + 1):
        logger.info(f"Generating groups for size {size}...")
        groups = select_treatments(similarity_matrix, size, excluded_locations)
        possible_groups.extend(groups)
        logger.info(f"Generated {len(groups)} groups for size {size}")
    
    logger.info(f"Total possible groups generated: {len(possible_groups)}")
    
    if not possible_groups:
        logger.warning("No possible groups generated, returning None")
        return None

    total_groups = len(possible_groups)
    results = []
    logger.info(f"Starting evaluation of {total_groups} groups using ProcessPoolExecutor")
    
    logger.info(f"Starting evaluation of {total_groups} groups using ThreadPoolExecutor")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        logger.info("ProcessPoolExecutor created, submitting tasks...")
        futures = executor.map(
            evaluate_group,
            possible_groups,
            [data] * total_groups,
            [total_Y] * total_groups,
            [correlation_matrix] * total_groups,
            [min_holdout] * total_groups,
            [df_pivot] * total_groups,
            chunksize=5
        )
        logger.info("Tasks submitted, starting to collect results...")
        
        for idx, result in enumerate(futures):
            logger.debug(f"Processing result {idx + 1}/{total_groups}")
            results.append(result)
            
            if is_streamlit_context() and progress_updater:
                try:
                    progress_updater.progress((idx + 1) / total_groups)
                except Exception as e:
                    logger.debug(f"Progress update failed: {e}")
            if is_streamlit_context() and status_updater:
                try:
                    status_updater.text(f"Finding the best groups: {int((idx + 1) / total_groups * 100)}% complete ⏳")
                except Exception as e:
                    logger.debug(f"Status update failed: {e}")
            
            if (idx + 1) % 10 == 0:
                logger.info(f"Processed {idx + 1}/{total_groups} groups")
    
    logger.info(f"All groups processed. Results count: {len(results)}")
    
    results_by_size = {}
    logger.info("Organizing results by size...")
    for size in range(min_elements_in_treatment, max_group_size + 1):
        logger.info(f"Processing results for size {size}...")
        best_results = [result for result in results if result is not None and len(result[0]) == size]
        logger.info(f"Found {len(best_results)} valid results for size {size}")
        
        if best_results:
            best_result = min(best_results, key=lambda x: (x[2], -x[3]))
            best_treatment_group, best_control_group, best_MAPE, best_SMAPE, y, predictions, weights, observed_conformity = best_result
            
            treatment_Y = data[data['location'].isin(best_treatment_group)]['Y'].sum()
            
            # Add validation to prevent division by zero
            if total_Y > 0:
                holdout_percentage = ((total_Y - treatment_Y) / total_Y) * 100
            else:
                holdout_percentage = 0.0

            results_by_size[size] = {
                'Best Treatment Group': best_treatment_group,
                'Control Group': best_control_group,
                'MAPE': best_MAPE,
                'SMAPE': best_SMAPE,
                'Actual Target Metric (y)': y,
                'Predictions': predictions,
                'Weights': weights,
                'Holdout Percentage': holdout_percentage,
                'observed_conformity': observed_conformity
            }
            logger.info(f"Best result for size {size}: MAPE={best_MAPE:.4f}, SMAPE={best_SMAPE:.4f}, Holdout={holdout_percentage:.2f}%")

    if not results or all(result is None for result in results):
        logger.warning("No valid results found, returning None")
        return None
    
    logger.info(f"BetterGroups completed successfully. Returning results for {len(results_by_size)} sizes")
    return results_by_size if results_by_size else None



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
    conformity = np.mean(y_real[start_treatment:end_treatment]) - \
                np.mean(y_control[start_treatment:end_treatment])
    return conformity

def compute_residuals(y_treatment, y_control):
    """
    Compute residuals between treatment and control series
    """

    y_treatment = np.array(y_treatment).flatten()
    y_control = np.array(y_control).flatten()
    return y_treatment - y_control


def simulate_power(y_real, y_control, delta, period, n_permutations=1000, significance_level=0.05, inference_type="iid", stat_func=None):
    """
    Simulates statistical power using conformal inference and returns the adjusted series.

    Args:
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        delta (float): Effect size applied.
        period (int): Duration of the treatment period.
        n_permutations (int): Number of permutations.
        significance_level (float): Significance level.
        inference_type (str): Type of conformal inference ("iid" or "block").

    Returns:
        tuple: Delta, statistical power, and the adjusted series with the applied effect.
    """
    logger.debug(f"Starting simulate_power: delta={delta}, period={period}, n_permutations={n_permutations}")
    
    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()
    
    start_treatment = len(y_real) - period
    end_treatment = start_treatment + period
    
    logger.debug(f"Treatment period: {start_treatment} to {end_treatment}")
    
    y_with_lift = apply_lift(y_real, delta, start_treatment, end_treatment)
    residuals = compute_residuals(y_with_lift, y_control)
    treatment_residuals = residuals[start_treatment:]
    
    def stat_func(x):
        return np.sum(x)
    
    observed_stat = stat_func(treatment_residuals)
    logger.debug(f"Observed statistic: {observed_stat}")
    
    logger.debug("Starting permutation test")
    null_stats = []
    for i in range(n_permutations):
        if i % 1000 == 0 and i > 0:
            logger.debug(f"Completed {i}/{n_permutations} permutations")
        permuted_residuals = np.random.permutation(residuals)
        permuted = permuted_residuals[start_treatment:]
        null_stats.append(stat_func(permuted))
    
    null_stats = np.array(null_stats)
    
    p_value = np.mean(null_stats >= observed_stat)
    power = np.mean(p_value < significance_level)
    
    logger.debug(f"Permutation test completed: p_value={p_value:.4f}, power={power:.4f}")

    return delta, power, y_with_lift,p_value

def run_simulation(delta, y_real, y_control, period, n_permutations, significance_level, inference_type="iid", size_block=None):
    """
    Wrapper function to run a single simulation of statistical power.
    """
    logger.debug(f"Starting simulation: delta={delta}, period={period}, n_permutations={n_permutations}")
    
    # Asegurarse de que y_real y y_control son arrays de numpy
    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()
    
    try:
        result = simulate_power(
            y_real=y_real,
            y_control=y_control,
            delta=delta,
            period=period,
            n_permutations=n_permutations,
            significance_level=significance_level,
            inference_type=inference_type,
        )
        logger.debug(f"Simulation completed successfully: delta={delta}, power={result[1]:.4f}")
        return result
    except Exception as e:
        logger.error(f"Simulation failed for delta={delta}, period={period}: {str(e)}")
        raise

def evaluate_sensitivity(results_by_size, deltas, periods, n_permutations, significance_level=0.05, inference_type="iid",  size_block=None, progress_bar=None, status_text=None):
    """
    Evaluates sensitivity of results to different treatment periods and deltas using permutations.

    Args:
        results_by_size (dict): Results organized by sample size.
        deltas (list): List of delta values to evaluate.
        periods (list): List of treatment periods to evaluate.
        n_permutations (int): Number of permutations.
        significance_level (float): Significance level.
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int): Size of blocks for block shuffling (if applicable).

    Returns:
        dict: Sensitivity results by size and period.
        dict: Adjusted series for each delta and period.
    """
    logger.info("Starting evaluate_sensitivity function")
    logger.info(f"Parameters: deltas={len(deltas)}, periods={len(periods)}, n_permutations={n_permutations}")
    
    sensitivity_results = {}
    lift_series = {}
    

    total_steps = sum(len(periods) * len(deltas)  for _ in results_by_size)
    step =  0
    
    logger.info(f"Total steps to process: {total_steps}")

    for size, result in results_by_size.items():
        logger.info(f"Processing size {size}")
        
        if ('Actual Target Metric (y)' not in result or 
            'Predictions' not in result or
            result['Actual Target Metric (y)'] is None or 
            result['Predictions'] is None):
            logger.warning(f"Skipping size {size} due to missing or null values")
            continue

        y_real = np.array(result['Actual Target Metric (y)']).flatten()
        y_control = np.array(result['Predictions']).flatten()
        
        logger.info(f"Data prepared for size {size}: y_real shape={y_real.shape}, y_control shape={y_control.shape}")

        results_by_period = {}

        for period in periods:
            logger.info(f"Processing period {period} for size {size}")
            results = []  

            
            for delta in deltas:
                logger.debug(f"Running simulation for size={size}, period={period}, delta={delta}")
                res = run_simulation(delta, y_real, y_control, period, n_permutations, significance_level, inference_type, size_block)
                results.append(res)

                
                step += 1
                # Only update progress if we're in a Streamlit context and have valid updaters
                if is_streamlit_context() and progress_bar:
                    try:
                        progress_bar.progress(min(step / total_steps,1.0))
                    except Exception as e:
                        logger.debug(f"Progress update failed: {e}")
                if is_streamlit_context() and status_text:
                    try:
                        status_text.text(f"Evaluating groups: {int((step / total_steps) * 100)}% complete ⏳")
                    except Exception as e:
                        logger.debug(f"Status update failed: {e}")
                
                if step % 10 == 0:
                    logger.info(f"Completed {step}/{total_steps} simulations")

            
            statistical_power = [(res[0], res[1], res[3]) for res in results]
            mde = next((delta for delta, power, p_value in statistical_power if power >= 0.85), None)
            
            
            mde_p_value = None
            if mde is not None:
                for delta, power, p_value in statistical_power:
                    if delta == mde:
                        mde_p_value = p_value
                        break
            
            logger.info(f"Period {period} completed for size {size}. MDE found: {mde} with p-value: {mde_p_value}")

            for delta, _, adjusted_series,p_value in results:
                lift_series[(size, delta, period)] = adjusted_series

            results_by_period[period] = {
                'Statistical Power': statistical_power,
                'MDE': mde,
                'P-Value': mde_p_value
            }

        sensitivity_results[size] = results_by_period
        logger.info(f"Size {size} completed. Results for {len(results_by_period)} periods")

    logger.info("evaluate_sensitivity completed successfully")
    return sensitivity_results, lift_series

def transform_results_data(results_by_size):
    """
    Transforms the data to ensure compatibility with the heatmap.
    """
    transformed_data = {}
    for size, data in results_by_size.items():
        transformed_data[size] = {
            'Best Treatment Group': ', '.join(data['Best Treatment Group']),
            'Control Group': ', '.join(data['Control Group']),
            'MAPE': float(data['MAPE']),
            'SMAPE': float(data['SMAPE']),
            'Actual Target Metric (y)': data['Actual Target Metric (y)'].tolist(),
            'Predictions': data['Predictions'].tolist(),
            'Weights': data['Weights'].tolist(),
            'Holdout Percentage': float(data['Holdout Percentage'])
        }
    return transformed_data

def run_geo_analysis_streamlit_app(data, maximum_treatment_percentage, significance_level, deltas_range, periods_range, excluded_locations, progress_bar_1=None, status_text_1=None, progress_bar_2=None, status_text_2=None ,n_permutations=10000):
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
        fig: MDE visualization figure.
        tuple: Tuple containing periods
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensitivity_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
    """
    logger.info("Starting run_geo_analysis_streamlit_app")
    logger.info(f"Input data shape: {data.shape}")
    logger.info(f"Parameters: max_treatment_pct={maximum_treatment_percentage}, significance_level={significance_level}")
    logger.info(f"deltas_range={deltas_range}, periods_range={periods_range}, n_permutations={n_permutations}")
    logger.info(f"excluded_locations={excluded_locations}")
    
    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
      logger.info("Simulation in progress........")
    
    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)
    
    logger.info(f"Generated periods: {periods}")
    logger.info(f"Generated deltas: {deltas}")

    # Step 1: Generate market correlations
    logger.info("Step 1: Generating market correlations")
    correlation_matrix = market_correlations(data)
    logger.info(f"Correlation matrix created with shape: {correlation_matrix.shape}")

    

    # Step 2: Find the best groups for control and treatment
    logger.info("Step 2: Finding best groups for control and treatment")
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        maximum_treatment_percentage=maximum_treatment_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1
    )
    
    if simulation_results is None:
        logger.error("BetterGroups returned None, stopping execution")
        return None
    
    logger.info(f"BetterGroups completed. Results for {len(simulation_results)} sizes")

    # Step 3: Evaluate sensitivity for different deltas and periods
    logger.info("Step 3: Evaluating sensitivity for different deltas and periods")
    sensitivity_results, series_lifts = evaluate_sensitivity(
        simulation_results, deltas, periods, n_permutations, significance_level,progress_bar=progress_bar_2, status_text=status_text_2
    )
    
    if sensitivity_results is not None:
      logger.info("Sensitivity evaluation completed successfully")
    else:
      logger.warning("Sensitivity evaluation returned None")
      
    
    

    
    

    logger.info("run_geo_analysis_streamlit_app completed successfully")
    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts
    }


def run_geo_analysis(data, maximum_treatment_percentage, significance_level, deltas_range, periods_range, excluded_locations, progress_bar_1=None, status_text_1=None, progress_bar_2=None, status_text_2=None ,n_permutations=10000):
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
        status_updater=status_text_1
    )

    # Step 3: Evaluate sensitivity for different deltas and periods
    sensitivity_results, series_lifts = evaluate_sensitivity(
        simulation_results, deltas, periods, n_permutations, significance_level,progress_bar=progress_bar_2, status_text=status_text_2
    )
    if sensitivity_results is not None:
      logger.info("Complete.")
      
    # Step 4: Generate MDE visualizations
    fig = plot_mde_results(simulation_results, sensitivity_results, periods)

    fig.show()


    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts
    }
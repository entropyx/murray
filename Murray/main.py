import concurrent.futures
from math import comb
import numpy as np
import cvxpy as cp
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, RegressorMixin
from Murray.plots import plot_mde_results
from Murray.auxiliary import market_correlations
import concurrent.futures
from sklearn.linear_model import Ridge


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

    missing_locations = [location for location in excluded_locations if location not in similarity_matrix.index or location not in similarity_matrix.columns]
    

    if missing_locations:
        raise KeyError(f"The following locations are not present in the similarity matrix: {missing_locations}")
    
    

    similarity_matrix_filtered = similarity_matrix.loc[
        ~similarity_matrix.index.isin(excluded_locations),
        ~similarity_matrix.columns.isin(excluded_locations)
    ]

    
    if treatment_size > similarity_matrix_filtered.shape[1]:
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


    combinations = set()

    while len(combinations) < n_combinations:
        sample_columns = np.random.choice(
            similarity_matrix_filtered.columns,
            size=treatment_size,
            replace=False
        )
        sample_group = tuple(sorted(sample_columns))
        combinations.add(sample_group)

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
    control_group = set()
    
    for treatment_location in treatment_group:
        if treatment_location not in correlation_matrix.index:
            continue
        treatment_row = correlation_matrix.loc[treatment_location]

        
        similar_states = treatment_row[
            (treatment_row >= min_correlation) & (~treatment_row.index.isin(treatment_group))
        ].sort_values(ascending=False).index.tolist()

        if not similar_states:
            similar_states = (
                treatment_row[~treatment_row.index.isin(treatment_group)]
                .sort_values(ascending=False)
                .head(fallback_n)
                .index.tolist()
            )
            

        control_group.update(similar_states)

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


def smape(A, F):
    denominator = np.abs(A) + np.abs(F)
    denominator = np.where(denominator == 0, 1e-8, denominator)
    return 100 / len(A) * np.sum(2 * np.abs(F - A) / denominator)

def evaluate_group(treatment_group, data, total_Y, correlation_matrix, min_holdout, df_pivot):
    """
    Evaluates a treatment group and returns error metrics.
    """
    treatment_Y = data[data['location'].isin(treatment_group)]['Y'].sum()
    holdout_percentage = (1 - (treatment_Y / total_Y)) * 100

    if holdout_percentage < min_holdout:
        return None

    control_group = select_controls(
        correlation_matrix=correlation_matrix,
        treatment_group=treatment_group,
        min_correlation=0.8
    )

    if not control_group:
        return (treatment_group, [], float('inf'), float('inf'), None, None, None, None)

   
    X = df_pivot[control_group].values  
    y = df_pivot[treatment_group].sum(axis=1).values  

    time_index = np.arange(len(df_pivot))

    scaler_x = MinMaxScaler()
    scaler_y = MinMaxScaler()

    X_scaled = scaler_x.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))

    split_index = int(len(X_scaled) * 0.8)

    X_train, X_test = X_scaled[:split_index], X_scaled[split_index:]
    y_train, y_test = y_scaled[:split_index], y_scaled[split_index:]

    time_train = time_index[:split_index]
    time_test  = time_index[split_index:]

    model = SyntheticControl(
        use_ridge_adjustment=True,  
        ridge_alpha=1.0             
    )
    model.fit(X_train, y_train, time_train=time_train)

    counterfactual_test, weights = model.predict(X_test, time_index=time_test)
    counterfactual_full, weights = model.predict(X_scaled, time_index=time_index)
    counterfactual_full = counterfactual_full.reshape(-1,1)
    counterfactual_full_original = scaler_y.inverse_transform(counterfactual_full)
    y_original = scaler_y.inverse_transform(y_scaled)
    counterfactual_full_original = counterfactual_full_original.flatten()
    y_original = y_original.flatten()

    weights = model.w_

    MAPE = np.mean(np.abs((y_original[split_index:] - counterfactual_full_original[split_index:]) / (y_original[split_index:] + 1e-10))) * 100
    SMAPE_value = smape(y_original[split_index:], counterfactual_full_original[split_index:])

    # Calculate observed conformity
    observed_conformity = np.mean(y_original - counterfactual_full_original)

    return (treatment_group, control_group, MAPE, SMAPE_value, y_original, counterfactual_full_original, weights, observed_conformity)

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

    unique_locations = data['location'].unique()
    no_locations = len(unique_locations)
    max_group_size = round(no_locations * 0.45)
    min_elements_in_treatment = round(no_locations * 0.15)
    min_holdout = 100 - (maximum_treatment_percentage * 100)
    total_Y = data['Y'].sum()
    
    if total_Y == 0:
        return None
    
    df_pivot = data.pivot(index='time', columns='location', values='Y')
    
    
    possible_groups = []
    for size in range(min_elements_in_treatment, max_group_size + 1):
        groups = select_treatments(similarity_matrix, size, excluded_locations)
        possible_groups.extend(groups)
    
    if not possible_groups:
        return None

    total_groups = len(possible_groups)
    results = []
    
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
        futures = executor.map(
            evaluate_group,
            possible_groups,
            [data] * total_groups,
            [total_Y] * total_groups,
            [correlation_matrix] * total_groups,
            [min_holdout] * total_groups,
            [df_pivot] * total_groups,
            chunksize=10
        )
        for idx, result in enumerate(futures):
            results.append(result)
            if progress_updater:
                progress_updater.progress((idx + 1) / total_groups)
            if status_updater:
                status_updater.text(f"Finding the best groups: {int((idx + 1) / total_groups * 100)}% complete ⏳")
    
    results_by_size = {}
    for size in range(min_elements_in_treatment, max_group_size + 1):
        best_results = [result for result in results if result is not None and len(result[0]) == size]
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

    if not results or all(result is None for result in results):
        return None
        
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
    
    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()
    
    start_treatment = len(y_real) - period
    end_treatment = start_treatment + period
    
    y_with_lift = apply_lift(y_real, delta, start_treatment, end_treatment)
    residuals = compute_residuals(y_with_lift, y_control)
    treatment_residuals = residuals[start_treatment:]
    
    def stat_func(x):
        return np.sum(x)
    
    observed_stat = stat_func(treatment_residuals)
    
    null_stats = []
    for _ in range(n_permutations):
        permuted_residuals = np.random.permutation(residuals)
        permuted = permuted_residuals[start_treatment:]
        null_stats.append(stat_func(permuted))
    null_stats = np.array(null_stats)
    
    p_value = np.mean(null_stats >= observed_stat)
    power = np.mean(p_value < significance_level)

    return delta, power, y_with_lift

def run_simulation(delta, y_real, y_control, period, n_permutations, significance_level, inference_type="iid", size_block=None):
    """
    Wrapper function to run a single simulation of statistical power.
    """
    # Asegurarse de que y_real y y_control son arrays de numpy
    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()
    
    return simulate_power(
        y_real=y_real,
        y_control=y_control,
        delta=delta,
        period=period,
        n_permutations=n_permutations,
        significance_level=significance_level,
        inference_type=inference_type,
    )

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
    sensitivity_results = {}
    lift_series = {}
    

    total_steps = sum(len(periods) * len(deltas)  for _ in results_by_size)
    step =  0

    for size, result in results_by_size.items():
        if ('Actual Target Metric (y)' not in result or 
            'Predictions' not in result or
            result['Actual Target Metric (y)'] is None or 
            result['Predictions'] is None):
            print(f"Skipping size {size} due to missing or null values")
            continue

        y_real = np.array(result['Actual Target Metric (y)']).flatten()
        y_control = np.array(result['Predictions']).flatten()

        results_by_period = {}

        for period in periods:
            results = []  

            
            for delta in deltas:
                res = run_simulation(delta, y_real, y_control, period, n_permutations, significance_level, inference_type, size_block)
                results.append(res)

                
                step += 1
                if progress_bar:
                    progress_bar.progress(min(step / total_steps,1.0))
                if status_text:
                    status_text.text(f"Evaluating groups: {int((step / total_steps) * 100)}% complete ⏳")

            
            statistical_power = [(res[0], res[1]) for res in results]
            mde = next((delta for delta, power in statistical_power if power >= 0.85), None)

            for delta, _, adjusted_series in results:
                lift_series[(size, delta, period)] = adjusted_series

            results_by_period[period] = {
                'Statistical Power': statistical_power,
                'MDE': mde
            }

        sensitivity_results[size] = results_by_period

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
    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
      print("Simulation in progress........")
    
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
      print("Complete.")
      
    
    

    
    

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
      print("Simulation in progress........")
    
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
      print("Complete.")
      
    # Step 4: Generate MDE visualizations
    fig = plot_mde_results(simulation_results, sensitivity_results, periods)

    fig.show()


    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts
    }
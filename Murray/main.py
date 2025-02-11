import concurrent.futures
from math import comb
import numpy as np
import cvxpy as cp
from sklearn.preprocessing import MinMaxScaler
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_is_fitted
from .plots import plot_mde_results
from .auxiliary import market_correlations




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
    if n_combinations > 500:
        n_combinations = 500


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



def select_controls(correlation_matrix, treatment_group, min_correlation=0.8):
    """
    Dynamically selects control group states based on correlation values.

    Args:
        correlation_matrix (pd.DataFrame): Correlation matrix between states.
        treatment_group (list): List of states in the treatment group.
        min_correlation (float): Minimum correlation threshold to consider a state as part of the control group.

    Returns:
        list: List of states selected as the control group.
    """
    control_group = set()

    for treatment_location in treatment_group:
        if treatment_location not in correlation_matrix.index:
            continue
        treatment_row = correlation_matrix.loc[treatment_location]

        similar_states = treatment_row[
            (treatment_row >= min_correlation) &
            (~treatment_row.index.isin(treatment_group))
        ].sort_values(ascending=False).index.tolist()

        control_group.update(similar_states)

    return list(control_group)

class SyntheticControl(BaseEstimator, RegressorMixin):
    def __init__(self, regularization_strength_l1=0.1, regularization_strength_l2=0.1, seasonality=None, delta=1.0):
        """
        Args:
            regularization_strength_l1: Strength of the L1 regularization (Lasso).
            regularization_strength_l2: Strength of the L2 regularization (Ridge).
            seasonality: DataFrame with the calculated seasonality, indexed by time.
            delta: Parameter for the Huber loss.
        """
        self.regularization_strength_l1 = regularization_strength_l1
        self.regularization_strength_l2 = regularization_strength_l2
        self.seasonality = seasonality
        self.delta = delta

    def _prepare_data(self, X, time_index=None):
        """
        Combines the original features with seasonality if available.
        
        Args:
            X: Input features
            time_index: Index of timestamps if seasonality is used
            
        Returns:
            numpy.ndarray: Processed feature matrix
        """
        X = np.array(X)
        if self.seasonality is not None and time_index is not None:
            if len(time_index) != X.shape[0]:
                raise ValueError("The size of the time index does not match X.")
            seasonal_values = self.seasonality.loc[time_index].to_numpy().reshape(-1, 1)
            X = np.hstack([X, seasonal_values])
        return X

    def squared_loss(self, x):
        """Compute squared loss."""
        return cp.sum_squares(x)

    def fit(self, X, y):
        """
        Fit the synthetic control model.
        
        Args:
            X: Training features
            y: Target values
            
        Returns:
            self: The fitted model
        """
        X = self._prepare_data(X)
        y = np.ravel(y)

        if X.shape[0] != y.shape[0]:
            raise ValueError("The number of rows in X must match the size of y.")

        w = cp.Variable(X.shape[1])

        # Elastic Net Regularization (L1 + L2)
        regularization_l1 = self.regularization_strength_l1 * cp.norm1(w)
        regularization_l2 = self.regularization_strength_l2 * cp.norm2(w)

        errors = X @ w - y
        objective = cp.Minimize(self.squared_loss(errors) + regularization_l2)

        # Constraints
        constraints = [cp.sum(w) == 1, w >= 0]

        problem = cp.Problem(objective, constraints)
        problem.solve(solver=cp.SCS, verbose=False)

        if problem.status != cp.OPTIMAL:
            problem.solve(solver=cp.ECOS, verbose=False)

        if problem.status != cp.OPTIMAL:
            raise ValueError("Optimization did not converge. Status: " + problem.status)

        self.X_ = X
        self.y_ = y
        self.w_ = w.value
        self.is_fitted_ = True
        return self

    def predict(self, X):
        """
        Make predictions using the fitted model.
        
        Args:
            X: Features to predict on
            
        Returns:
            tuple: (predictions, weights)
        """
        check_is_fitted(self)
        X = self._prepare_data(X)
        return X @ self.w_, self.w_


def BetterGroups(similarity_matrix, excluded_locations, data, correlation_matrix, min_holdout=70,progress_updater=None, status_updater=None):
    """
    Simulates possible treatment groups and evaluates their performance.


    Parameters:
        similarity_matrix (pd.DataFrame): Similarity matrix between locations.
        excluded_locations (list): List of locations to exclude from treatment combinations.
        data (pd.DataFrame): Dataset with columns 'time', 'location', and 'Y'.
        correlation_matrix (pd.DataFrame): Correlation matrix between locations.
        min_holdout (float): Minimum percentage of data to reserve as holdout (untreated).


    Returns:
        dict: Simulation results, organized by treatment group size.
              Each entry contains the best treatment group, control group, MAE,
              actual target metrics, predictions, weights, and holdout percentage.
    """
    results_by_size = {}
    no_locations = int(len(data['location'].unique()))
    max_group_size = round(no_locations * 0.5)
    min_elements_in_treatment = round(no_locations * 0.2)

    def smape(A, F):
        denominator = np.abs(A) + np.abs(F)
        denominator = np.where(denominator == 0, 1e-8, denominator)  
        return 100 / len(A) * np.sum(2 * np.abs(F - A) / denominator)

    total_Y = data['Y'].sum()
    possible_groups = []
    for size in range(min_elements_in_treatment, max_group_size + 1):
        groups = select_treatments(similarity_matrix, size, excluded_locations)
        possible_groups.extend(groups)

    if not possible_groups:
        return None

    def evaluate_group(treatment_group):
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
            return (treatment_group, [], float('inf'), float('inf'), None, None, None)

        df_pivot = data.pivot(index='time', columns='location', values='Y')
        X = df_pivot[control_group].values
        y = df_pivot[list(treatment_group)].sum(axis=1).values

        model = SyntheticControl()

        #----------------------------------------------------------------------------------

        scaler_x = MinMaxScaler()
        scaler_y = MinMaxScaler()

        X_scaled = scaler_x.fit_transform(X)
        y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))

        split_index = int(len(X_scaled) * 0.8)
        X_train, X_test = X_scaled[:split_index], X_scaled[split_index:]
        y_train, y_test = y_scaled[:split_index], y_scaled[split_index:]

        model = SyntheticControl()
        model.fit(X_train, y_train)

        predictions_val, weights = model.predict(X_test)

        contrafactual_train = (weights @ X_train.T).reshape(-1, 1)
        contrafactual_test = (weights @ X_test.T).reshape(-1, 1)
        contrafactual_full = np.vstack((contrafactual_train, contrafactual_test))

        contrafactual_full_original = scaler_y.inverse_transform(contrafactual_full)
        predictions = contrafactual_full_original.flatten()

        y_original = scaler_y.inverse_transform(y_scaled).flatten()

        MAPE = np.mean(np.abs((y_original - predictions) / (y_original + 1e-10))) * 100
        SMAPE = smape(y_original, predictions)

        return (treatment_group, control_group, MAPE, SMAPE, y_original, predictions, weights)

        #----------------------------------------------------------------------------------
    total_groups = len(possible_groups)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = []
        for idx, result in enumerate(executor.map(evaluate_group, possible_groups)):
            results.append(result)
            if progress_updater:
                progress_updater.progress((idx + 1) / total_groups)
            
            
            if status_updater:
                status_updater.text(f"Finding the best groups: {int((idx + 1) / total_groups * 100)}% complete ⏳")


    total_Y = data['Y'].sum()

    for size in range(min_elements_in_treatment, max_group_size + 1):
        best_results = [result for result in results if result is not None and len(result[0]) == size]

        if best_results:
            best_result = min(best_results, key=lambda x: (x[2], -x[3]))
            best_treatment_group, best_control_group, best_MAPE, best_SMAPE, y, predictions, weights = best_result

            treatment_Y = data[data['location'].isin(best_treatment_group)]['Y'].sum()
            holdout_percentage = ((total_Y - treatment_Y) / total_Y) * 100

            results_by_size[size] = {
                'Best Treatment Group': best_treatment_group,
                'Control Group': best_control_group,
                'MAPE': best_MAPE,
                'SMAPE': best_SMAPE,
                'Actual Target Metric (y)': y,
                'Predictions': predictions,
                'Weights': weights,
                'Holdout Percentage': holdout_percentage
            }

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
    
    y_with_lift = np.array(y).copy()
    
    
    
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

def simulate_power(y_real, y_control, delta, period, n_permutaciones=1000, significance_level=0.05, inference_type="iid", size_block=None):
    """
    Simulates statistical power using conformal inference and returns the adjusted series.

    Args:
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        delta (float): Effect size applied.
        period (int): Duration of the treatment period.
        n_permutaciones (int): Number of permutations.
        significance_level (float): Significance level.
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int): Size of blocks for block shuffling (if applicable).

    Returns:
        tuple: Delta, statistical power, and the adjusted series with the applied effect.
    """
    start_treatment = len(y_real) - period
    end_treatment = start_treatment + period
    
    y_with_lift = apply_lift(y_real, delta, start_treatment, end_treatment)
    observed_conformity = calculate_conformity(y_with_lift, y_control, start_treatment, end_treatment)
    
    combined = np.concatenate([y_real, y_control])
    conformidades_nulas = []

    for _ in range(n_permutaciones):
        if inference_type == "iid":
            np.random.shuffle(combined)
        elif inference_type == "block":
            if size_block is None:
                size_block = max(1, len(combined) // 10)
            for i in range(0, len(combined), size_block):
                np.random.shuffle(combined[i:i+size_block])

        perm_treatment = combined[:len(y_real)]
        perm_control = combined[len(y_real):]

        conformidad_perm = calculate_conformity(
            perm_treatment, perm_control, start_treatment, end_treatment)
        conformidades_nulas.append(conformidad_perm)

    p_value = np.mean(np.abs(conformidades_nulas) >= np.abs(observed_conformity))
    power = np.mean(p_value < significance_level)

    return delta, power, y_with_lift

def run_simulation(delta, y_real, y_control, period, n_permutaciones, significance_level, inference_type="iid", size_block=None):
    """
    Wrapper function to run a single simulation of statistical power.

    Args:
        delta (float): Effect size.
        y_real (numpy.ndarray): Actual target metrics.
        y_control (numpy.ndarray): Control metrics.
        period (int): Treatment period duration.
        n_permutaciones (int): Number of permutations.
        significance_level (float): Significance level.
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int, optional): Size of blocks for block shuffling. Defaults to None.

    Returns:
        tuple: Simulation results including delta, power, and adjusted series.
    """
    return simulate_power(
        y_real=y_real,
        y_control=y_control,
        delta=delta,
        period=period,
        n_permutaciones=n_permutaciones,
        significance_level=significance_level,
        inference_type=inference_type,
        size_block=size_block
    )

def evaluate_sensitivity(results_by_size, deltas, periods, n_permutaciones, significance_level=0.05, inference_type="iid",  size_block=None, progress_bar=None, status_text=None):
    """
    Evaluates sensitivity of results to different treatment periods and deltas using permutations.

    Args:
        results_by_size (dict): Results organized by sample size.
        deltas (list): List of delta values to evaluate.
        periods (list): List of treatment periods to evaluate.
        n_permutaciones (int): Number of permutations.
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
                res = run_simulation(delta, y_real, y_control, period, n_permutaciones, significance_level, inference_type, size_block)
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

def run_geo_analysis(data, minimum_holdout_percentage, significance_level, deltas_range, periods_range, excluded_locations, progress_bar_1=None, status_text_1=None, progress_bar_2=None, status_text_2=None ,n_permutaciones=500):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        excluded_locations (list): List of states to exclude from the analysis.
        minimum_holdout_percentage (float): Minimum holdout percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        n_permutaciones (int, optional): Number of permutations for sensitivity evaluation. Default is 5000.

    Returns:
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "fig": MDE visualization figure.
            - "config": Configuration for the MDE visualization.
            - "results_by_size": Results from group optimization.
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
        min_holdout=minimum_holdout_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1
    )

    # Step 3: Evaluate sensitivity for different deltas and periods
    sensitivity_results, series_lifts = evaluate_sensitivity(
        simulation_results, deltas, periods, n_permutaciones, significance_level,progress_bar=progress_bar_2, status_text=status_text_2
    )
    if sensitivity_results is not None:
      print("Complete.")
      
    # Step 4: Generate MDE visualizations
    fig = plot_mde_results(simulation_results, sensitivity_results, periods)

    


    return periods,fig, {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts
    }


import warnings
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error,mean_absolute_error,mean_absolute_percentage_error
from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
from sklearn.preprocessing import MinMaxScaler
import concurrent.futures
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from math import comb
import cvxpy as cp
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_array, check_is_fitted
from plots import plot_mde_results
from auxiliary import market_correlations

def select_treatments(similarity_matrix, treatment_size, excluded_states=set()):
    """
    Selects n combinations of treatments based on a similarity DataFrame, excluding certain states
    from the treatment selection but allowing their inclusion in the control.

    Args:
        similarity_matrix (pd.DataFrame): DataFrame containing correlations between locations in a standard matrix format
        treatment_size (int): Number of treatments to select for each combination.
        excluded_states (set): Set of states to exclude from the treatment selection.

    Returns:
        list: A list of unique combinations, each combination being a list of states.
    """
    missing_states = [state for state in excluded_states if state not in similarity_matrix.index or state not in similarity_matrix.columns]
    
    if missing_states:
        raise KeyError(f"The following states are not present in the similarity matrix: {missing_states}")
    
    # Remove excluded states from both rows and columns
    similarity_matrix_filtered = similarity_matrix.loc[
        ~similarity_matrix.index.isin(excluded_states),
        ~similarity_matrix.columns.isin(excluded_states)
    ]

    # Verify that the treatment size is valid
    if treatment_size > similarity_matrix_filtered.shape[1]:
        raise ValueError(
            f"The treatment size ({treatment_size}) exceeds the available number of columns "
            f"({similarity_matrix_filtered.shape[1]})."
        )

    # Maximum number of combinations
    n = similarity_matrix_filtered.shape[1]
    r = treatment_size
    max_combinations = comb(n, r)

    n_combinaciones = max_combinations
    if n_combinaciones > 5000:
      n_combinaciones = 5000

    combinaciones = set()

    while len(combinaciones) < n_combinaciones:
        sample_columns = np.random.choice(
            similarity_matrix_filtered.columns,
            size=treatment_size,
            replace=False
        )

        
        sample_group = tuple(sorted(sample_columns))
        combinaciones.add(sample_group)


    return [list(comb) for comb in combinaciones]



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
        """
        X = np.array(X)
        if self.seasonality is not None and time_index is not None:
            if len(time_index) != X.shape[0]:
                raise ValueError("The size of the time index does not match X.")
            seasonal_values = self.seasonality.loc[time_index].to_numpy().reshape(-1, 1)
            X = np.hstack([X, seasonal_values])
        return X

    def squared_loss(self, x):
        return cp.sum_squares(x)

    def fit(self, X, y):
        X = self._prepare_data(X)
        y = np.ravel(y)

        if X.shape[0] != y.shape[0]:
            raise ValueError("The number of rows in X must match the size of y.")

        w = cp.Variable(X.shape[1])

        # Elastic Net Regularization (L1 + L2)
        regularization_l1 = self.regularization_strength_l1 * cp.norm1(w)
        regularization_l2 = self.regularization_strength_l2 * cp.norm2(w)

        
        errors = X @ w - y
        objective = cp.Minimize(self.squared_loss(errors) + regularization_l1 + regularization_l2)

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
        check_is_fitted(self)
        X = self._prepare_data(X)
        return X @ self.w_, self.w_


def BetterGroups(similarity_matrix, excluded_states, data, correlation_matrix,min_holdout=70):
    """
    Simulates possible treatment groups and evaluates their performance.

    Parameters:
        similarity_matrix (pd.DataFrame): Similarity matrix between locations.
        n_combinaciones (int): Number of unique combinations of treatment groups to generate.
        min_holdout (float): minimum percentage of data to reserve as holdout (untreated).
        excluded_states (list): List of states to exclude from treatment combinations.
        data (pd.DataFrame): Dataset with columns 'time', 'location', and 'Y'.
        correlation_matrix (pd.DataFrame): Correlation matrix between locations.

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
      return 100/len(A) * np.sum(2 * np.abs(F - A) / (np.abs(A) + np.abs(F)))

    
    total_Y = data['Y'].sum()
    possible_groups = []
    for size in range(min_elements_in_treatment, max_group_size + 1):
        groups = select_treatments(similarity_matrix, size, excluded_states)
        possible_groups.extend(groups)

    
    if not possible_groups:
        return None

    
    def evaluate_group(treatment_group):
        treatment_Y = data[data['location'].isin(treatment_group)]['Y'].sum()
        holdout_percentage = (1 - (treatment_Y / total_Y)) * 100


        # Filter based on the minimum holdout percentage
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

        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,random_state=42)

      
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
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(
            tqdm(executor.map(evaluate_group, possible_groups), total=len(possible_groups), desc="Finding the best groups")
        )

    
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
    Applies a lift (delta) to a specific period of the time series.

    Args:
        y (numpy array or pandas series): Time series data.
        delta (float): Percentage lift to apply.
        start_treatment (int): Start index of the treatment period.
        end_treatment (int): End index of the treatment period.

    Returns:
        numpy array or pandas series: Adjusted series with the applied lift.
    """
    y_with_lift = y.astype(float).copy()
    y_with_lift[start_treatment:end_treatment] *= (1 + delta)
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
    conformidad = np.mean(y_real[start_treatment:end_treatment]) - \
                  np.mean(y_control[start_treatment:end_treatment])
    return conformidad

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
    conformidad_observada = calculate_conformity(y_with_lift, y_control,start_treatment, end_treatment)
    combined = np.concatenate([y_real, y_control])
    conformidades_nulas = []

    for _ in range(n_permutaciones):
        if inference_type == "iid":
            np.random.shuffle(combined)
        elif inference_type == "block":
            if tamano_bloque is None:
                tamano_bloque = max(1, len(combined) // 10)
            for i in range(0, len(combined), tamano_bloque):
                np.random.shuffle(combined[i:i+tamano_bloque])

        perm_treatment = combined[:len(y_real)]
        perm_control = combined[len(y_real):]

        conformidad_perm = calculate_conformity(
            perm_treatment, perm_control, start_treatment, end_treatment)
        conformidades_nulas.append(conformidad_perm)

    p_value = np.mean(np.abs(conformidades_nulas) >= np.abs(conformidad_observada))
    power = np.mean(p_value < significance_level)

    return delta, power, y_with_lift

def run_simulation(delta, y_real, y_control, period, n_permutaciones, significance_level, inference_type="iid", size_block=None):
    """
    Wrapper function to run a single simulation of statistical power.

    Args:
        delta (float): Effect size.
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        period (int): Treatment period duration.
        n_permutaciones (int): Number of permutations.
        significance_level (float): Significance level.
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int): Size of blocks for block shuffling (if applicable).

    Returns:
        tuple: Simulation results including delta, power, and adjusted series.
    """
    return simulate_power(
        y_real, y_control, delta, period,
        n_permutaciones=n_permutaciones,
        significance_level=significance_level,
        inference_type=inference_type,
        size_block=size_block
    )

def evaluate_sensitivity(results_by_size, deltas, periods, n_permutaciones, significance_level=0.05, inference_type="iid", size_block=None):
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

    total_periods = sum(len(periods) for _ in results_by_size)
    with tqdm(total=total_periods, desc="Evaluating groups", leave=True) as pbar:
        for size, result in results_by_size.items():
            if ('Actual Target Metric (y)' not in result or 'Predictions' not in result or
                    result['Actual Target Metric (y)'] is None or result['Predictions'] is None):
                print(f"Skipping size {size} due to missing or null values")
                continue

            y_real = np.array(result['Actual Target Metric (y)']).flatten()
            y_control = np.array(result['Predictions']).flatten()

            results_by_period = {}

            for period in periods:
                with ProcessPoolExecutor() as executor:
                    results = list(executor.map(run_simulation, deltas,
                                                [y_real] * len(deltas),
                                                [y_control] * len(deltas),
                                                [period] * len(deltas),
                                                [n_permutaciones] * len(deltas),
                                                [significance_level] * len(deltas),
                                                [inference_type] * len(deltas),
                                                [size_block] * len(deltas)))

                statistical_power = [(res[0], res[1]) for res in results]
                mde = next((delta for delta, power in statistical_power if power >= 0.85), None)

                for delta, _, adjusted_series in results:
                    lift_series[(size, delta, period)] = adjusted_series

                results_by_period[period] = {
                    'Statistical Power': statistical_power,
                    'MDE': mde
                }
                pbar.update(1)

            sensitivity_results[size] = results_by_period

    return sensitivity_results, lift_series


def run_geo_analysis(data, excluyed_states, minimum_holdout_percentage, significance_level, deltas_range, periods_range, n_permutaciones=5000):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        excluyed_states (list): List of states to exclude from the analysis.
        minimum_holdout_percentage (float): Minimum holdout percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        n_permutaciones (int, optional): Number of permutations for sensitivity evaluation. Default is 1000.

    Returns:
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensivility_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
    """
    
    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)


    # Step 1: Generate market correlations
    correlation_matrix = market_correlations(data, excluyed_states)


    # Step 2: Find the best groups for control and treatment
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        holdout=minimum_holdout_percentage,
        excluded_states=excluyed_states,
        data=data,
        correlation_matrix=correlation_matrix
    )


    # Step 3: Evaluate sensitivity for different deltas and periods
    sensivility_results, series_lifts = evaluate_sensitivity(
        simulation_results, deltas, periods, n_permutaciones, significance_level
    )


    # Step 4: Generate MDE visualizations
    plot_mde_results(simulation_results, sensivility_results, periods)

    # Convert series_lifts to numpy arrays
    for key, value in series_lifts.items():
        series_lifts[key] = [np.array(value)]

    # Return the complete analysis results
    return {
        "simulation_results": simulation_results,
        "sensivility_results": sensivility_results,
        "series_lifts": series_lifts
    }

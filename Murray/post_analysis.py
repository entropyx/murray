import numpy as np
from sklearn.preprocessing import MinMaxScaler
from Murray.main import select_controls,SyntheticControl
from Murray.auxiliary import market_correlations
import pandas as pd

def run_geo_evaluation(data_input, start_treatment,end_treatment,treatment_group,spend,n_permutations=500000,inference_type='iid',significance_level=0.1):
        
        random_sate = data_input['location'].unique()[0]
        filtered_data = data_input[data_input['location'] == random_sate]
        start_treatment = pd.to_datetime(start_treatment, dayfirst=True)
        end_treatment = pd.to_datetime(end_treatment,dayfirst=True)
        filtered_data['time'] = pd.to_datetime(filtered_data['time'])
        start_idx = (filtered_data['time'].dt.date == start_treatment.date()).idxmax()
        end_idx = (filtered_data['time'].dt.date == end_treatment.date()).idxmax()
        start_position_treatment = filtered_data.index.get_loc(start_idx)
        end_position = filtered_data.index.get_loc(end_idx)
        end_position_treatment = end_position + 1 
        
        

        def smape(A, F):
          return 100/len(A) * np.sum(2 * np.abs(F - A) / (np.abs(A) + np.abs(F+1e-10)))

        correlation_matrix = market_correlations(data_input
                                                 )

        control_group = select_controls(
            correlation_matrix=correlation_matrix,
            treatment_group=treatment_group,
            min_correlation=0.8
        )

        period = end_position_treatment - start_position_treatment
        df_pivot = data_input.pivot(index='time', columns='location', values='Y')
        X = df_pivot[control_group].values  
        y = df_pivot[treatment_group].sum(axis=1).values  

        time_index = np.arange(len(df_pivot))

        scaler_x = MinMaxScaler()
        scaler_y = MinMaxScaler()

        X_scaled = scaler_x.fit_transform(X)
        y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))

        

        X_train, X_test = X_scaled[:start_position_treatment], X_scaled[start_position_treatment:]
        y_train, y_test = y_scaled[:start_position_treatment], y_scaled[start_position_treatment:]

        time_train = time_index[:start_position_treatment]
        time_test  = time_index[start_position_treatment:]

        model = SyntheticControl(
        use_ridge_adjustment=True,  
        ridge_alpha=1.0             
    )
        model.fit(X_train, y_train, time_train=time_train)

        counterfactual_test = model.predict(X_test, time_index=time_test)
        counterfactual_full = model.predict(X_scaled, time_index=time_index).reshape(-1,1)
        counterfactual_full_original = scaler_y.inverse_transform(counterfactual_full)
        y_original = scaler_y.inverse_transform(y_scaled)
        counterfactual_full_original = counterfactual_full_original.flatten()
        y_original = y_original.flatten()

        predictions = counterfactual_full_original
        weights = model.w_
        
        MAPE = np.mean(np.abs((y_original - predictions) / (y_original + 1e-10))) * 100
        SMAPE = smape(y_original, predictions)

        percenge_lift = ((np.sum(y[start_position_treatment:]) - np.sum(predictions[start_position_treatment:])) / np.abs(np.sum(predictions[start_position_treatment:]))) * 100

        def compute_residuals(y_treatment, y_control):
            return y_treatment - y_control

        residuals = compute_residuals(y,predictions)
        treatment_residuals = residuals[start_position_treatment:]

        def stat_func(x):
            return np.sum(x)
        

    
        observed_stat = stat_func(treatment_residuals)
        
        
        null_stats = []

        for _ in range(n_permutations):
            permuted_residuals = np.random.permutation(residuals)
            permuted = permuted_residuals[start_position_treatment:]
            null_stats.append(stat_func(permuted))
        null_stats = np.array(null_stats)
        
        
        p_value = np.mean(abs(null_stats) >= abs(observed_stat))
        power = np.mean(p_value < significance_level)

        length_treatment = len(treatment_group)
        results_evaluation = {
            'MAPE': MAPE,
            'SMAPE': SMAPE,
            'predictions': predictions,
            'treatment': y,
            'p_value': p_value,
            'power': power,
            'percenge_lift': percenge_lift,
            'control_group': control_group,
            'observed_stat': observed_stat,
            'null_stats': null_stats,
            'weights': weights,
            'period': period,
            'spend': spend,
            'length_treatment': length_treatment
        }


        return results_evaluation
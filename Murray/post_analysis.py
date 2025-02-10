import numpy as np
from sklearn.preprocessing import MinMaxScaler
from .main import select_controls,apply_lift,SyntheticControl
from .auxiliary import market_correlations


def post_analysis(data_input, start_treatment,end_treatment,treatment_group,lift=0.1,n_permutaciones=5000,inference_type='iid',significance_level=0.1):

        def smape(A, F):
          return 100/len(A) * np.sum(2 * np.abs(F - A) / (np.abs(A) + np.abs(F+1e-10)))

        correlation_matrix = market_correlations(data_input
                                                 )

        control_group = select_controls(
            correlation_matrix=correlation_matrix,
            treatment_group=treatment_group,
            min_correlation=0.8
        )


        df_pivot = data_input.pivot(index='time', columns='location', values='Y')
        X = df_pivot[control_group].values  
        y = df_pivot[list(treatment_group)].sum(axis=1).values  
        y_lift = apply_lift(y,lift,start_treatment,end_treatment)
        
        scaler_x = MinMaxScaler()
        scaler_y = MinMaxScaler()

        X_scaled = scaler_x.fit_transform(X)  
        y_scaled = scaler_y.fit_transform(y.reshape(-1, 1))  

        X_train, X_test = X_scaled[:start_treatment], X_scaled[start_treatment:]
        y_train, y_test = y_scaled[:start_treatment], y_scaled[start_treatment:]

        
        model = SyntheticControl()
        model.fit(X_train, y_train)

        
        predictions_val, weights = model.predict(X_test)

        
        y_train_pred = model.predict(X_train)[0].reshape(-1, 1)
        predictions_val_original = scaler_y.inverse_transform(predictions_val.reshape(-1, 1))
        y_train_original = scaler_y.inverse_transform(y_train_pred)

        
        predictions = np.vstack((y_train_original, predictions_val_original)).flatten()

        
        y_original = scaler_y.inverse_transform(y_scaled).flatten()

        
        MAPE = np.mean(np.abs((y_original - predictions) / (y_original + 1e-10))) * 100
        SMAPE = smape(y_original, predictions)

        percenge_lift = ((np.sum(y_lift[start_treatment:]) - np.sum(predictions_val_original)) / np.abs(np.sum(predictions_val_original))) * 100


        conformidad_observada = np.mean(y_lift[start_treatment:]) - np.mean(predictions_val_original)
        combined = np.concatenate([y_lift, predictions])
        
        conformidades_nulas = []
        for _ in range(n_permutaciones):
            if inference_type == "iid":
                np.random.shuffle(combined)
            elif inference_type == "block":
                block_size = len(combined) // 10
                np.random.shuffle(combined.reshape(-1, block_size))
            
            
            perm_treatment = combined[np.random.choice(len(combined), len(y), replace=False)]
            perm_control = combined[np.random.choice(len(combined), len(y), replace=False)]

            conformidad_perm = np.mean(perm_treatment[start_treatment:]) - np.mean(perm_control[start_treatment:])
            conformidades_nulas.append(conformidad_perm)

        
        p_value = np.mean(np.abs(conformidades_nulas) >= np.abs(conformidad_observada))
        power = np.mean(p_value < significance_level)

        
        

        return y_lift,predictions,p_value,power,percenge_lift,control_group,conformidad_observada,conformidades_nulas
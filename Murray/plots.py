import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
from sklearn.metrics import mean_absolute_percentage_error

def plot_geodata(merged_data):
    """
    Plots a time-series line chart of conversions (Y) over time, grouped by location.

    Args:
        merged_data: pandas.DataFrame
            A DataFrame containing the following columns:
            - 'time': Timestamps or dates
            - 'Y': Conversion value
            - 'location': Categorical column to group and differentiate lines by color
    """
    # Create figure with specified size
    plt.figure(figsize=(24, 10))
    
    # Plot time series lines
    sns.lineplot(x='time', y='Y', hue='location', data=merged_data, linewidth=1)

    # Add location labels at the end of each line
    last_points = merged_data.groupby('location').last().reset_index()
    for _, row in last_points.iterrows():
        plt.text(row['time'], row['Y'], row['location'], 
                color='black', fontsize=12, ha='left', va='center')

    # Format axes and labels
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Conversions', fontsize=12)
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)
    plt.legend([], frameon=False)
    
    plt.show()

def plot_metrics(geo_test):
    """
    Plots MAPE and SMAPE metrics for each group size.

    Args:
        geo_test (dict): A dictionary containing the simulation results, including predictions and actual metrics.

    Returns:
        None: Displays plots for MAPE and SMAPE metrics by group size.
    """

    metrics = {'Size': [], 'MAPE': [], 'SMAPE': []}
    results_by_size = geo_test['simulation_results']

    # Calculate MAPE and SMAPE for each group size
    for size, result in results_by_size.items():
        y = result['Actual Target Metric (y)']
        predictions = result['Predictions']

        mape = mean_absolute_percentage_error(y, predictions)
        smape = 100/len(y) * np.sum(2 * np.abs(predictions - y) / (np.abs(y) + np.abs(predictions)))

        metrics['Size'].append(size)
        metrics['MAPE'].append(mape)
        metrics['SMAPE'].append(smape)

    # Plot MAPE and SMAPE metrics
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(25, 6))

    ax1.plot(metrics['Size'], metrics['MAPE'], marker='o', color='b')
    ax1.set_title('MAPE by Group Size')
    ax1.set_xlabel('Group Size')
    ax1.set_ylabel('MAPE')

    ax2.plot(metrics['Size'], metrics['SMAPE'], marker='o', color='r')
    ax2.set_title('SMAPE by Group Size')
    ax2.set_xlabel('Group Size')
    ax2.set_ylabel('SMAPE')

    plt.tight_layout()
    plt.show()

def plot_counterfactuals(geo_test):
    """
    Plots the counterfactuals (actual vs. predicted values) for each group size.

    Args:
        geo_test (dict): A dictionary containing simulation results with actual and predicted metrics.

    Returns:
        None: Displays plots for each group size showing counterfactuals.
    """
    results_by_size = geo_test['simulation_results']

    for size, result in results_by_size.items():
        real_y = result['Actual Target Metric (y)']
        predictions = result['Predictions']

        plt.figure(figsize=(25, 6))
        plt.plot(real_y, label='Actual (Treatment)', color='blue', linewidth=2)
        plt.plot(predictions, label='Predicted (Counterfactual)', color='red', 
                linestyle='--', linewidth=2)
        plt.xlabel('Time')
        plt.ylabel('Metric Value')
        plt.title(f'Counterfactual for Group Size {size}')
        plt.legend()
        plt.grid(True)
        plt.show()


def plot_mde_results(sensitivity_results, periods):
    """
    Plots Minimum Detectable Effect (MDE) results.
    
    Args:
        sensitivity_results (dict): Results from sensitivity analysis
        periods (list): List of periods evaluated
    """
    plt.figure(figsize=(12, 6))
    
    for size, period_results in sensitivity_results.items():
        mde_values = []
        for period in periods:
            if period in period_results:
                mde = period_results[period]['MDE'] 
                mde_values.append(mde if mde is not None else np.nan)
            else:
                mde_values.append(np.nan)
        
        plt.plot(periods, mde_values, marker='o', label=f'Size {size}')
    
    plt.xlabel('Treatment Period Length')
    plt.ylabel('Minimum Detectable Effect (MDE)')
    plt.title('MDE by Treatment Group Size and Period Length')
    plt.legend()
    plt.grid(True)
    plt.show()


def print_locations(geo_test, holdout_percentage=None, num_locations=None):
    """
    Extracts treatment and control locations based on holdout percentage or number of locations.

    Args:
        geo_test (dict): Dictionary containing simulation results.
        holdout_percentage (float, optional): Holdout percentage to match.
        num_locations (int, optional): Number of locations to match.

    Returns:
        None: Prints the treatment and control locations.
    """
    results_by_size = geo_test['simulation_results']
    treatment_locations = []
    control_locations = []

    for size, result in results_by_size.items():
        current_holdout = result['Holdout Percentage'].round(2)

        if holdout_percentage is not None and current_holdout == holdout_percentage:
            treatment_locations.extend(result['Best Treatment Group'])
            control_locations.extend(result['Control Group'])

        if num_locations is not None and len(result['Best Treatment Group']) == num_locations:
            treatment_locations.extend(result['Best Treatment Group'])
            control_locations.extend(result['Control Group'])

    print(f"Treatment Locations: {treatment_locations}")
    print(f"Control Locations: {control_locations}")


def print_weights(geo_test, holdout_percentage=None, num_locations=None):
    """
    Extracts control group weights based on holdout percentage or number of locations.

    Args:
        geo_test (dict): Dictionary containing simulation results.
        holdout_percentage (float, optional): The holdout percentage to filter by.
        num_locations (int, optional): The number of locations to filter by.

    Returns:
        pd.DataFrame: A DataFrame with control locations and their corresponding weights, sorted in descending order.
    """
    results_by_size = geo_test['simulation_results']
    control_weights = []
    control_locations = []

    for size, result in results_by_size.items():
        current_holdout = result['Holdout Percentage'].round(2)
        if holdout_percentage is not None and current_holdout == holdout_percentage:
            control_weights.extend(result['Weights'])
            control_locations.extend(result['Control Group'])
        if num_locations is not None and len(result['Best Treatment Group']) == num_locations:
            control_weights.extend(result['Weights'])
            control_locations.extend(result['Control Group'])

    weights = pd.DataFrame({
        'Control Location': control_locations,
        'Weights': control_weights
    })

    weights = weights.sort_values(by="Weights", ascending=False).reset_index(drop=True)

    return weights


def plot_impact(geo_test, periodo_especifico, top_n):
        """
        Generates graphs for the top-N cases with the lowest MDE values in a specific period.

        Args:
            results (dict): Dictionary with results including sensitivity, simulations, and treated series.
            specific_period (int): Period in which the MDE is to be analyzed.
            top_n (int): Number of cases with the lowest MDE to plot.

        Returns:
            None: Displays the corresponding graphs.
        """


        
        sensibilidad_resultados = geo_test['sensivility_results']
        results_by_size = geo_test['simulation_results']
        series_lifts = geo_test['series_lifts']
        periodos = next(iter(sensibilidad_resultados.values())).keys()

        
        if periodo_especifico not in periodos:
            raise ValueError(f"The period {periodo_especifico} is not in the evaluated periods list.")

        
        mde_holdout_pairs = []
        for size_key, resultados_por_periodo in sensibilidad_resultados.items():
            if periodo_especifico in resultados_por_periodo:
                mde = resultados_por_periodo[periodo_especifico].get('MDE', None)

                
                resultados_size = results_by_size.get(size_key, None)
                holdout_percentage = resultados_size.get('Holdout Percentage', None) if resultados_size else None

                if mde is not None and holdout_percentage is not None:
                    mde_holdout_pairs.append((mde, holdout_percentage, size_key))

        if not mde_holdout_pairs:
            print("DEBUG: No MDE-Holdout pairs found.")
            return

        
        mde_holdout_pairs = sorted(mde_holdout_pairs, key=lambda x: x[0])[:top_n]
        

        for i, (mde, holdout_percentage, size_key) in enumerate(mde_holdout_pairs):
            available_deltas = [delta for s, delta, period in series_lifts.keys() if s == size_key and period == periodo_especifico]

            if not available_deltas:
                print(f"DEBUG: No available deltas for size {size_key} and period {periodo_especifico}.")
                continue

            
            delta_specific = mde  
            closest_delta = min(available_deltas, key=lambda x: abs(x - delta_specific))
            comb = (size_key, closest_delta, periodo_especifico)
            

            
            resultados_size = results_by_size.get(size_key, None)
            y_real = resultados_size['Predictions'].flatten() if resultados_size else None

            if y_real is None:
                print(f"DEBUG: No y_real found for combination {comb}.")
                continue

            
            serie_tratamiento = series_lifts.get(comb, [None])[0]

            
            if len(serie_tratamiento) != len(y_real):
                raise ValueError("The treatment and counterfactual series have different lengths.")

            
            diferencia_puntual = serie_tratamiento - y_real
            efecto_acumulativo = ([0] * (len(serie_tratamiento) - periodo_especifico)) + (np.cumsum(diferencia_puntual[len(serie_tratamiento)-periodo_especifico:])).tolist()


            
            fig, axes = plt.subplots(3, 1, figsize=(15, 9.5), sharex=True)

            # Panel 1: Observed data vs counterfactual prediction
            axes[0].plot(y_real, label='Control Group', linestyle='--', color='blue')
            axes[0].plot(serie_tratamiento, label='Treatment Group', linestyle='-', color='orange')
            axes[0].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1, label='Treatment Period')
            axes[0].set_title(f'Holdout: {holdout_percentage:.2f}% - MDE: {mde:.2f}')
            axes[0].set_ylabel('Original')
            axes[0].legend()
            axes[0].grid()

            # Panel 2: Point difference
            axes[1].plot(diferencia_puntual, label='Point Difference (Causal Effect)', color='green')
            axes[1].axhline(0, color='black', linestyle='--', linewidth=1)  
            axes[1].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1)
            #axes[1].set_title('Point Difference (Treatment - Counterfactual)')
            axes[1].set_ylabel('Point Difference')
            axes[1].grid()

            # Panel 3: Cumulative effect
            axes[2].plot(efecto_acumulativo, label='Cumulative Effect', color='red')
            axes[2].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1)
            #axes[2].set_title('Cumulative Effect of Treatment')
            axes[2].set_xlabel('Days')
            axes[2].set_ylabel('Cumulative Effect')
            axes[2].grid()

            
            plt.tight_layout()
            plt.show()
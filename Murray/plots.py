import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.dates as mdates
from sklearn.metrics import mean_absolute_percentage_error
import plotly.graph_objects as go
from matplotlib import pyplot as plt



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
    
    fig, ax = plt.subplots(figsize=(24, 10))  
    
    
    sns.lineplot(x='time', y='Y', hue='location', data=merged_data, linewidth=1, ax=ax)


    last_points = merged_data.groupby('location').last().reset_index()
    for _, row in last_points.iterrows():
        ax.text(row['time'], row['Y'], row['location'], 
                color='black', fontsize=12, ha='left', va='center')

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Conversions', fontsize=12)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)
    ax.legend([], frameon=False)


    return fig

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

    
    for size, result in results_by_size.items():
        y = result['Actual Target Metric (y)']
        predictions = result['Predictions']

        mape = mean_absolute_percentage_error(y, predictions)
        smape = 100/len(y) * np.sum(2 * np.abs(predictions - y) / (np.abs(y) + np.abs(predictions)))

        metrics['Size'].append(size)
        metrics['MAPE'].append(mape)
        metrics['SMAPE'].append(smape)

    
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




def plot_mde_results(results_by_size, sensitivity_results, periods):
    """
    Generates an interactive heatmap for the MDE (Minimum Detectable Effect) values using Plotly.
    Compatible with Streamlit.
    """
    
    holdout_by_location = {
        size: data['Holdout Percentage']
        for size, data in results_by_size.items()
    }
    sorted_sizes = sorted(holdout_by_location.keys(), key=lambda x: holdout_by_location[x])

    
    heatmap_data = pd.DataFrame()
    for size in sorted_sizes:
        row = []
        period_results = sensitivity_results.get(size, {})
        for period in periods:
            mde = period_results.get(period, {}).get('MDE', None)
            row.append(mde if mde is not None else None)
        heatmap_data[size] = row
    
    heatmap_data = heatmap_data.T
    heatmap_data.columns = [f"Day-{i}" for i in periods]
    heatmap_data.index = [f"{holdout_by_location.get(size, 0):.2f}%" for size in sorted_sizes]
    heatmap_data.index.name = "Holdout (%)"
    
    y_labels = heatmap_data.index.tolist()
    z_values = heatmap_data.values.tolist()
    annotations = [[f"{val:.2%}" if val is not None else "" for val in row] for row in z_values]

    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=heatmap_data.columns.tolist(),
        y=y_labels,
        colorscale="RdYlGn_r",
        colorbar=dict(title="MDE (%)"),
        hoverongaps=False,
        text=annotations,
        hoverinfo="text",
        showscale=True,
        xgap=1,
        ygap=1
    ))

    fig.update_layout(
        dragmode=False,
        xaxis=dict(title="Treatment Periods", 
                   tickmode="array", 
                   tickvals=list(range(len(heatmap_data.columns.tolist()))), 
                   ticktext=heatmap_data.columns.tolist()),
        yaxis=dict(title="Holdout (%)", 
                   tickmode="array", 
                   tickvals=list(range(len(y_labels))), 
                   ticktext=y_labels,
                   type='category')
    )

    return fig



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
        "Control Location": control_locations,
        "Weights": control_weights
    })

    
    weights = weights.sort_values(by="Weights", ascending=False).reset_index(drop=True)
    return weights



def plot_impact(geo_test, periodo_especifico, holdout_target):
        """
        Generates graphs for a specific holdout percentage in a specific period.

        Args:
            geo_test (dict): Dictionary with results including sensitivity, simulations, and treated series.
            periodo_especifico (int): Period in which the MDE is to be analyzed.
            holdout_target (float): Target holdout percentage to plot.

        Returns:
            fig: matplotlib figure object with the plots
        """
        sensibilidad_resultados = geo_test['sensitivity_results']
        results_by_size = geo_test['simulation_results']
        series_lifts = geo_test['series_lifts']
        periodos = next(iter(sensibilidad_resultados.values())).keys()

        if periodo_especifico not in periodos:
            raise ValueError(f"The period {periodo_especifico} is not in the evaluated periods list.")

        
        target_size_key = None
        target_mde = None
        for size_key, result in results_by_size.items():

            current_holdout = result['Holdout Percentage']
            if abs(current_holdout - holdout_target) < 0.01: 
                target_size_key = size_key
                target_mde = sensibilidad_resultados[size_key][periodo_especifico].get('MDE', None)
                break


        if target_size_key is None:
            print(f"DEBUG: No data found for holdout percentage {holdout_target}%")
            return None

        
        available_deltas = [delta for s, delta, period in series_lifts.keys() 
                          if s == target_size_key and period == periodo_especifico]


        if not available_deltas:
            print(f"DEBUG: No available deltas for holdout {holdout_target}% and period {periodo_especifico}.")
            return None

        
        delta_specific = target_mde
        closest_delta = min(available_deltas, key=lambda x: abs(x - delta_specific))
        comb = (target_size_key, closest_delta, periodo_especifico)


        resultados_size = results_by_size[target_size_key]
        y_real = resultados_size['Predictions'].flatten()
        serie_tratamiento = series_lifts[comb]


        diferencia_puntual = serie_tratamiento - y_real
        efecto_acumulativo = ([0] * (len(serie_tratamiento) - periodo_especifico) + 
                             np.cumsum(diferencia_puntual[len(serie_tratamiento)-periodo_especifico:]).tolist())


        fig, axes = plt.subplots(3, 1, figsize=(15, 9.5), sharex=True)


        # Panel 1: Observed data vs counterfactual prediction
        axes[0].plot(y_real, label='Control Group', linestyle='--', color='blue')
        axes[0].plot(serie_tratamiento, label='Treatment Group', linestyle='-', color='orange')
        axes[0].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1, label='Treatment Period')
        axes[0].set_title(f'Holdout: {holdout_target:.2f}% - MDE: {target_mde:.2f}')
        axes[0].set_ylabel('Original')
        axes[0].legend()
        axes[0].grid()

        # Panel 2: Point difference
        axes[1].plot(diferencia_puntual, label='Point Difference (Causal Effect)', color='green')
        axes[1].axhline(0, color='black', linestyle='--', linewidth=1)
        axes[1].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1)
        axes[1].set_ylabel('Point Difference')
        axes[1].grid()

        # Panel 3: Cumulative effect
        axes[2].plot(efecto_acumulativo, label='Cumulative Effect', color='red')
        axes[2].axvspan(len(y_real) - periodo_especifico, len(y_real), color='gray', alpha=0.1)
        axes[2].set_xlabel('Days')
        axes[2].set_ylabel('Cumulative Effect')
        axes[2].grid()

        plt.tight_layout()
        return fig
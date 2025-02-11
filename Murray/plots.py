import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error
from plotly.subplots import make_subplots
import scipy.stats as stats
import matplotlib.dates as mdates
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors



#Color palette
blue = "#3e7cb1"           
green = "#87D8AD"         
red = "#dd2d4a"
purple_dark = "#1B0043"
black_secondary = "#4D4C50"
purple_light = "#BBB2C7"
heatmap_green = "#84DA35"
heatmap_red = "#DA3835"

custom_colors = ["#3E7CB1", "#6596C1", 
                     "#C5D8EB", "#5F4D7B", "#211F24", '#4D4C50',
                     '#1B0043', '#DD2D4A',"#C3EBD6",'#87D8AD']



def generate_gradient_palette(start_color, end_color, num_colors):
    """Genera una lista de colores en gradiente desde start_color hasta end_color."""
    cmap = mcolors.LinearSegmentedColormap.from_list("custom_gradient", [start_color, end_color], N=num_colors)
    return [mcolors.to_hex(cmap(i/num_colors)) for i in range(num_colors)]

def plot_geodata(merged_data,custom_colors=custom_colors):

    """
    Plots a time-series line chart of conversions (Y) over time, grouped by location.

    Args:
        merged_data: pandas.DataFrame
            A DataFrame containing the following columns:
            - 'time': Timestamps or dates
            - 'Y': Conversion value
            - 'location': Categorical column to group and differentiate lines by color
    """


    
    fig = go.Figure()



    for i, (location, data) in enumerate(merged_data.groupby('location')):
        fig.add_trace(go.Scatter(
            x=data['time'],
            y=data['Y'],
            mode='lines',
            name=location,
            line=dict(width=1, color=custom_colors[i % len(custom_colors)])  # Usa colores en ciclo
        ))


    last_points = merged_data.groupby('location').last().reset_index()


    for _, row in last_points.iterrows():
        fig.add_trace(go.Scatter(
            x=[row['time']],
            y=[row['Y']],
            mode='text',
            text=row['location'],
            textposition='middle right',
            showlegend=False,
            textfont=dict(
                size=12,
                color='black')
        ))


    fig.update_layout(


        xaxis_title="Date",
        xaxis_title_font=dict(size=16, color='black'),
        xaxis=dict(tickformat="%b %Y", tickangle=45),
        xaxis_tickfont=dict(size=12, color='black'),
        xaxis_linecolor='#0d0808',
        xaxis_color='#0d0808',
        xaxis_showgrid=True,




        yaxis_title="Conversions",
        yaxis_title_font=dict(size=16, color='black'),
        yaxis_tickfont=dict(size=12, color='black'),
        yaxis_linecolor='#0d0808',
        yaxis_color='#0d0808',
        yaxis_showgrid=True,


        margin=dict(l=50, r=50, t=50, b=50),
        showlegend=False,
        #paper_bgcolor='white',
        

    )

    return fig



def plot_metrics(geo_test):

    """
    Plots MAPE and SMAPE metrics for each group size.

    Args:
        geo_test (dict): A dictionary containing the simulation results, including predictions and actual metrics.

    Returns:
        None: Displays plots for MAPE and SMAPE metrics by group size.
    """


    from plotly.subplots import make_subplots

    metrics = {
        'Size': [],
        'MAPE': [],
        'SMAPE': []
    }


    results_by_size = geo_test['simulation_results']


    for size, result in results_by_size.items():
        y = result['Actual Target Metric (y)']
        predictions = result['Predictions']

        mape = mean_absolute_percentage_error(y, predictions)
        smape = 100 / len(y) * np.sum(2 * np.abs(predictions - y) / (np.abs(y) + np.abs(predictions)))

        metrics['Size'].append(size)
        metrics['MAPE'].append(mape)
        metrics['SMAPE'].append(smape)

    fig = make_subplots(rows=1, cols=2, subplot_titles=["MAPE by Group Size", "SMAPE by Group Size"])


    fig.add_trace(go.Scatter(
        x=metrics['Size'],
        y=metrics['MAPE'],
        mode='lines+markers',
        name='MAPE',
        marker=dict(color=blue)), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=metrics['Size'],
        y=metrics['SMAPE'],
        mode='lines+markers',
        name='SMAPE',
        marker=dict(color=black_secondary)), row=1, col=2)

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=50, r=50, t=50, b=50))


    fig.update_xaxes(title_text="Group Size", row=1, col=1)
    fig.update_xaxes(title_text="Group Size", row=1, col=2)


    fig.update_yaxes(title_text="MAPE", row=1, col=1)
    fig.update_yaxes(title_text="SMAPE", row=1, col=2)


    return fig





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

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            y=real_y,
            mode='lines',
            name='Actual (Treatment)',
            line=dict(color=purple_dark, width=2)))

        fig.add_trace(go.Scatter(
            y=predictions,
            mode='lines',
            name='Predicted (Counterfactual)',
            line=dict(color=black_secondary, width=2, dash='dash')))

        fig.update_layout(
            title=f'Counterfactual for Group Size {size}',
            xaxis_title="Time",
            yaxis_title="Metric Value",
            template="plotly_white",

            legend_title="Legend",
            margin=dict(l=50, r=50, t=50, b=50))

        return fig




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
            row.append(mde if mde is not None else np.nan)
        heatmap_data[size] = row


    heatmap_data = heatmap_data.T
    heatmap_data.columns = [f"Day-{i}" for i in periods]
    heatmap_data.index = [f"{holdout_by_location.get(size, 0):.2f}%" for size in sorted_sizes]
    heatmap_data.index.name = "Holdout (%)"

    y_labels = heatmap_data.index.tolist()
    x_labels = heatmap_data.columns.tolist()
    z_values = heatmap_data.values.tolist()
    annotations = [[f"{val:.2%}" if not np.isnan(val) else "" for val in row] for row in z_values]

    fig = go.Figure()
    custom_colorscale = [[0,heatmap_green], [1,heatmap_red]]





    fig.add_trace(go.Heatmap(
        z=z_values,
        x=x_labels,
        y=y_labels,
        colorscale=custom_colorscale,
        colorbar=dict(title="MDE (%)"),
        colorbar_tickfont=dict(size=12, color='black'),
        hoverongaps=False,
        text=annotations, 
        texttemplate="%{text}",  
        textfont={"size": 12, "color": "black"},
        hoverinfo="text",
        showscale=True,
        xgap=1,
        ygap=1
    ))


    scatter_x, scatter_y = np.meshgrid(range(len(x_labels)), range(len(y_labels)))
    scatter_x = scatter_x.flatten()
    scatter_y = scatter_y.flatten()


    fig.add_trace(go.Scatter(
        x=[x_labels[i] for i in scatter_x],
        y=[y_labels[i] for i in scatter_y],
        mode="markers",
        marker=dict(size=10, opacity=0),
        hoverinfo="none"
    ))


    fig.update_layout(
        margin=dict(l=90, r=10, t=20, b=75),
        dragmode=False,
        xaxis=dict(title="Treatment Periods",
                   title_font=dict(size=16, color='black'),
                   tickmode="array",
                   tickvals=list(range(len(x_labels))),
                   ticktext=x_labels,
                   showgrid=True,
                   tickfont=dict(size=12, color='black')),

        yaxis=dict(title="Holdout (%)",
                   title_font=dict(size=16, color='black'),
                   tickmode="array",
                   tickvals=list(range(len(y_labels))),
                   ticktext=y_labels,
                   type='category',
                   showgrid=True,
                   tickfont=dict(size=12, color='black'))
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



def plot_impact_streamlit_app(geo_test, periodo_especifico, holdout_target):
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
            raise ValueError("No matching data found.")

        
        available_deltas = [
            delta for s, delta, period in series_lifts.keys() 
            if s == target_size_key and period == periodo_especifico
        ]

        if not available_deltas:
            print(f"DEBUG: No available deltas for holdout {holdout_target}% and period {periodo_especifico}.")
            raise ValueError("No available deltas found.")

        
        delta_specific = target_mde
        closest_delta = min(available_deltas, key=lambda x: abs(x - delta_specific))
        comb = (target_size_key, closest_delta, periodo_especifico)

        
        resultados_size = results_by_size[target_size_key]
        y_real = resultados_size['Predictions'].flatten()
        serie_tratamiento = series_lifts[comb]

        
        point_difference = serie_tratamiento - y_real
        cumulative_effect = ([0] * (len(serie_tratamiento) - periodo_especifico) + 
                              np.cumsum(point_difference[len(serie_tratamiento)-periodo_especifico:]).tolist())
        

        star_treatment = len(y_real) - periodo_especifico
        y_treatment = y_real[star_treatment:]



        mean_y_real = np.mean(y_treatment)
        std_dev_y_real = np.std(y_treatment)
        std_error_y_real = std_dev_y_real / np.sqrt(len(y_treatment))
        x_confiance_band = list(range((len(y_real) - periodo_especifico), len(y_real)))
        upper_bound = y_treatment + 1.96 * std_error_y_real
        lower_bound = y_treatment - 1.96 * std_error_y_real

        mean_point_difference = np.mean(point_difference)
        std_dev_point_difference = np.std(point_difference)
        std_error_point_difference = std_dev_point_difference / np.sqrt(len(y_treatment))
        upper_bound_pd = point_difference[star_treatment:] + 1.96 * std_error_point_difference
        lower_bound_pd = point_difference[star_treatment:] - 1.96 * std_error_point_difference

        mean_cumulative_effect = np.mean(cumulative_effect)
        std_dev_cumulative_effect = np.std(cumulative_effect)
        std_error_cumulative_effect = std_dev_cumulative_effect / np.sqrt(len(y_treatment))
        upper_bound_ce = cumulative_effect[star_treatment:] + 1.96 * std_error_cumulative_effect
        lower_bound_ce = cumulative_effect[star_treatment:] - 1.96 * std_error_cumulative_effect



        att = np.mean(serie_tratamiento[star_treatment:] - y_real[star_treatment:])
        incremental = np.sum(serie_tratamiento[star_treatment:] - y_real[star_treatment:])


        


        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            subplot_titles=[
                                f'Holdout: {holdout_target:.2f}% - MDE: {target_mde:.2f}',
                                "Point Difference (Causal Effect)",
                                "Cumulative Effect"
                            ])

        # Panel 1: Observed data vs counterfactual prediction
        fig.add_trace(go.Scatter(
            y=y_real,
            mode='lines',
            name='Control Group',
            line=dict(color=black_secondary, dash='dash',width=1),
            showlegend=True  
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            y=serie_tratamiento,
            mode='lines',
            name='Treatment Group',
            line=dict(color=purple_dark,width=1),
            showlegend=True
        ), row=1, col=1)

        # Confiance band 1
        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=upper_bound,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),  
            showlegend=False
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=lower_bound,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.3)',
            showlegend=False
        ), row=1, col=1)


        # Panel 2: Point Difference (Causal Effect)
        fig.add_trace(go.Scatter(
            y=point_difference,
            mode='lines',
            name='Point Difference (Causal Effect)',
            line=dict(color=purple_dark,width=1),
            showlegend=False
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=[0, len(y_real)],
            y=[0, 0],
            mode='lines',
            name="Zero Reference",
            line=dict(color='gray', dash='dash'),
            showlegend=False  
        ), row=2, col=1)

        # Confiance band 2
        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=upper_bound_pd,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),  
            showlegend=False
        ), row=2, col=1)

        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=lower_bound_pd,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.3)',
            showlegend=False 
        ), row=2, col=1)


        # Panel 3: Cumulative Effect
        fig.add_trace(go.Scatter(
            y=cumulative_effect,
            mode='lines',
            name='Cumulative Effect',
            line=dict(color=purple_dark,width=1),
            showlegend=False  
        ), row=3, col=1)

        # Confiance band 3
        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=upper_bound_ce,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),  
            showlegend=False
        ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=x_confiance_band,
            y=lower_bound_ce,
            mode='lines',
            name='95% CI',
            line=dict(color='rgba(0,0,0,0)'),
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.3)',
            showlegend=False 
        ), row=3, col=1)


        
        for i in range(1, 4):
            fig.add_vline(x=star_treatment, line=dict(color="black", dash="dash"), row=i, col=1)


        
        fig.update_layout(
            height=900,
            width=1000,
            template="plotly_white",
            xaxis_title="Days",
            margin=dict(l=50, r=50, t=50, b=50),

            
            legend=dict(
                x=0.02,
                y=0.98,
                traceorder="normal",
                bgcolor="rgba(255,255,255,0.6)",
            ),
            legend_tracegroupgap=10  
        )

        
        fig.update_yaxes(title_text="Original", row=1, col=1)
        fig.update_yaxes(title_text="Point Difference", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative Effect", row=3, col=1)




        return att, incremental,fig


def plot_impact_graphs(geo_test, periodo_especifico, holdout_target):
  att, incremental, fig = plot_impact_streamlit_app(geo_test, periodo_especifico, holdout_target)
  return fig

def print_incremental_results(geo_test, periodo_especifico, holdout_target):
    title = "Incremental Results"
    att, incremental, fig = plot_impact_streamlit_app(geo_test, periodo_especifico, holdout_target)
    print("=" * 30)
    print(title.center(30))
    print("=" * 30)
    print(f"ATT: {round(att,2)}")
    print(f"Lift total: {round(incremental,2)}")
    print("=" * 30)




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




def plot_impact_evaluation(results_evaluation):
    """
    Plot the impact evaluation results using Plotly
    
    Args:
        counterfactual (array): Control group values
        treatment (array): Treatment group values
        period (int): Treatment period length
    """

    counterfactual = results_evaluation['predictions']
    treatment = results_evaluation['treatment']
    period = results_evaluation['period']

    point_difference = treatment - counterfactual
    cumulative_effect = ([0] * (len(treatment) - period)) + (np.cumsum(point_difference[len(treatment)-period:])).tolist()


    star_treatment = len(counterfactual) - period
    y_treatment = counterfactual[star_treatment:]
    point_difference_treatment = point_difference[star_treatment:]
    cumulative_effect_treatment = cumulative_effect[star_treatment:]

    mean_y_real = np.mean(y_treatment)
    std_dev_y_real = np.std(y_treatment)
    std_error_y_real = std_dev_y_real / np.sqrt(len(y_treatment))
    upper_bound = y_treatment + 1.96 * std_error_y_real
    lower_bound = y_treatment - 1.96 * std_error_y_real


    mean_point_difference = np.mean(point_difference_treatment)
    std_dev_point_difference = np.std(point_difference_treatment)
    std_error_point_difference = std_dev_point_difference / np.sqrt(len(y_treatment))
    upper_bound_pd = point_difference_treatment + 1.96 * std_error_point_difference
    lower_bound_pd = point_difference_treatment - 1.96 * std_error_point_difference


    mean_cumulative_effect = np.mean(cumulative_effect_treatment)
    std_dev_cumulative_effect = np.std(cumulative_effect_treatment)
    std_error_cumulative_effect = std_dev_cumulative_effect / np.sqrt(len(y_treatment))
    upper_bound_ce = cumulative_effect_treatment + 1.96 * std_error_cumulative_effect
    lower_bound_ce = cumulative_effect_treatment - 1.96 * std_error_cumulative_effect




    att = np.mean(treatment[star_treatment:] - counterfactual[star_treatment:])
    incremental = np.sum(treatment[star_treatment:] - counterfactual[star_treatment:])

    
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=[
                            "Observed Data vs Counterfactual",
                            "Point Difference (Causal Effect)",
                            "Cumulative Effect"
                        ])

    # Panel 1: Observed data vs counterfactual prediction
    fig.add_trace(go.Scatter(
        y=counterfactual,
        mode='lines',
        name='Control Group',
        line=dict(color=black_secondary, dash='dash',width=1),
        showlegend=True
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        y=treatment,
        mode='lines',
        name='Treatment Group',
        line=dict(color=purple_dark,width=1),
        showlegend=True
    ), row=1, col=1)



    # Confidence band 1
    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=upper_bound,
        mode='lines',
        name='95% CI)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=lower_bound,
        mode='lines',
        name='95% CI',
        line=dict(color='rgba(0,0,0,0)'),
        fill='tonexty',
        fillcolor='rgba(128,128,128,0.3)',
        showlegend=False
    ), row=1, col=1)

    # Panel 2: Point Difference 
    fig.add_trace(go.Scatter(
        y=point_difference,
        mode='lines',
        name='Point Difference (Causal Effect)',
        line=dict(color=purple_dark,width=1),
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=[0, len(counterfactual)],
        y=[0, 0],
        mode='lines',
        name="Zero Reference",
        line=dict(color='gray', dash='dash'),
        showlegend=False
    ), row=2, col=1)

    # Confidence band 2
    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=upper_bound_pd,
        mode='lines',
        name='95% CI)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=lower_bound_pd,
        mode='lines',
        name='95% CI',
        line=dict(color='rgba(0,0,0,0)'),
        fill='tonexty',
        fillcolor='rgba(128,128,128,0.3)',
        showlegend=False
    ), row=2, col=1)
    


    # Panel 3: Cumulative Effect
    fig.add_trace(go.Scatter(
        y=cumulative_effect,
        mode='lines',
        name='Cumulative Effect',
        line=dict(color=purple_dark,width=1),
        showlegend=False,
    ), row=3, col=1)

    # Confidence band 3
    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=upper_bound_ce,
        mode='lines',
        name='95% CI)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False
    ), row=3, col=1)

    fig.add_trace(go.Scatter(
        x=list(range(star_treatment, len(counterfactual))),
        y=lower_bound_ce,
        mode='lines',
        name='95% CI',
        line=dict(color='rgba(0,0,0,0)'),
        fill='tonexty',
        fillcolor='rgba(128,128,128,0.3)',
        showlegend=False
    ), row=3, col=1)


    
    for i in range(1, 4):
        fig.add_vline(x=star_treatment, line=dict(color="black", dash="dash"), row=i, col=1)

    fig.update_layout(
        height=900,
        width=1000,
        showlegend=True,
        template="plotly_white",
        margin=dict(l=20, r=20, t=20, b=20),

        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor="rgba(255,255,255,0.6)",
        )
    )

    
    fig.update_xaxes(color= '#0d0808',linecolor= '#0d0808',showgrid=True,row=1, col=1)
    fig.update_xaxes(color= '#0d0808',linecolor= '#0d0808',showgrid=True,row=2, col=1)
    fig.update_xaxes(title_text="Days",title_font=dict(size=16, color='black'),tickfont=dict(size=12, color='black'),linecolor= '#0d0808',color= '#0d0808',showgrid=True,row=3, col=1)
    
    fig.update_yaxes(title_text="Original",title_font=dict(size=16, color='black'),tickfont=dict(size=12, color='black'),color= '#0d0808',linecolor= '#0d0808',showgrid=True, row=1, col=1)
    fig.update_yaxes(title_text="Point Difference",title_font=dict(size=16, color='black'),tickfont=dict(size=12, color='black'),color= '#0d0808',linecolor= '#0d0808',showgrid=True, row=2, col=1)
    fig.update_yaxes(title_text="Cumulative Effect",title_font=dict(size=16, color='black'),tickfont=dict(size=12, color='black'),color= '#0d0808',linecolor= '#0d0808',showgrid=True, row=3, col=1)

  

    return fig, round(att,2), round(incremental,2)

def plot_impact_graphs_evaluation(results_evaluation):
    fig, att, incremental = plot_impact_evaluation(results_evaluation)
    return fig

def print_incremental_results_evaluation(results_evaluation):
    
    fig, att, incremental = plot_impact_evaluation(results_evaluation)
    title = "Incremental Results"
    print("=" * 30)
    print(title.center(30))
    print("=" * 30)
    print(f"ATT: {round(att,2)}")
    print(f"Lift total: {round(incremental,2)}")


    print("=" * 30)

def plot_permutation_test(results_evaluation, nivel_significancia=0.1):
    """
    Plot the permutation test results using Plotly with KDE density curve.
    
    Args:
        conformidades_nulas (array): Distribution of null conformities.
        conformidad_observada (float): Observed conformity score.
        nivel_significancia (float): Significance level (default: 0.1).
    
    Returns:
        fig: Plotly figure.
    """

    conformidades_nulas = results_evaluation['conformidades_nulas']
    conformidad_observada = results_evaluation['conformidad_observada']
    

    upper_bound = np.percentile(conformidades_nulas, 100 * (1 - (nivel_significancia / 2)))
    


    kde = stats.gaussian_kde(conformidades_nulas)
    x_kde = np.linspace(min(conformidades_nulas), max(conformidades_nulas), 300)
    y_kde = kde(x_kde)


    max_hist_y = max(kde(conformidades_nulas))  


    fig = go.Figure()


    fig.add_trace(go.Histogram(
        x=conformidades_nulas,
        nbinsx=30,
        histnorm='probability density',
        name="Null Conformities",

        marker=dict(color=blue,line=dict(color="black",width=1)),
        opacity=0.6
    ))


    fig.add_trace(go.Scatter(
        x=x_kde,
        y=y_kde,
        mode="lines",
        name="KDE Density",
        showlegend=False,

        line=dict(color="darkblue", width=2)
    ))



    fig.add_trace(go.Scatter(
        x=[conformidad_observada, conformidad_observada],
        y=[0, max_hist_y],  
        mode="lines",
        name="Observed Conformity",
        line=dict(color="black", dash="dash", width=1.5)
    ))

    def hex_to_rgba(hex_color, alpha=0.4):
      """Convierte un color HEX a RGBA con transparencia controlada."""
      hex_color = hex_color.lstrip("#")
      r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
      return f"rgba({r},{g},{b},{alpha})"



    fig.add_trace(go.Scatter(
        x=[upper_bound, max(conformidades_nulas), max(conformidades_nulas), upper_bound],

        y=[0, 0, max_hist_y, max_hist_y],  
        fill="toself",
        fillcolor=hex_to_rgba(purple_light, 0.3),  
        line=dict(color="rgba(255,0,0,0)"),
        name="Significance Zone"
    ))


    fig.update_layout(
        title="Permutation Test",
        xaxis_title="Conformity Score",
        yaxis_title="Density",
        template="plotly_white",

        bargap=0

    )

    return fig


#####################################################################################################
####################################PLOTS FOR REPORTS################################################
#####################################################################################################

def plot_geodata_report(merged_data,custom_colors=custom_colors):

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
    sns.lineplot(x='time', y='Y', hue='location', data=merged_data, linewidth=1, ax=ax,palette=custom_colors)
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


def plot_metrics_report(geo_test):

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

    ax1.plot(metrics['Size'], metrics['MAPE'], marker='o', color=blue)
    ax1.set_title('MAPE by Group Size')
    ax1.set_xlabel('Group Size')
    ax1.set_ylabel('MAPE')

    ax2.plot(metrics['Size'], metrics['SMAPE'], marker='o', color=black_secondary)
    ax2.set_title('SMAPE by Group Size')
    ax2.set_xlabel('Group Size')
    ax2.set_ylabel('SMAPE')

    plt.tight_layout()

    return fig





def plot_impact_report(geo_test, periodo_especifico, holdout_target):
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
    
    star_treatment = len(y_real) - periodo_especifico
    y_treatment = y_real[star_treatment:]
    
    mean_y_real = np.mean(y_treatment)
    std_dev_y_real = np.std(y_treatment)
    std_error_y_real = std_dev_y_real / np.sqrt(len(y_treatment))
    upper_bound = y_treatment + 1.96 * std_error_y_real
    lower_bound = y_treatment - 1.96 * std_error_y_real


    std_dev_effect = np.std(diferencia_puntual[star_treatment:])
    std_error_effect = std_dev_effect / np.sqrt(len(diferencia_puntual[star_treatment:]))
    upper_bound_effect = diferencia_puntual[star_treatment:] + 1.96 * std_error_effect
    lower_bound_effect = diferencia_puntual[star_treatment:] - 1.96 * std_error_effect


    std_dev_cumulative = np.std(efecto_acumulativo[star_treatment:])
    std_error_cumulative = std_dev_cumulative / np.sqrt(len(efecto_acumulativo[star_treatment:]))
    upper_bound_cumulative = efecto_acumulativo[star_treatment:] + 1.96 * std_error_cumulative
    lower_bound_cumulative = efecto_acumulativo[star_treatment:] - 1.96 * std_error_cumulative


    att = np.mean(serie_tratamiento[star_treatment:] - y_real[star_treatment:])
    incremental = np.sum(serie_tratamiento[star_treatment:] - y_real[star_treatment:])

    fig, axes = plt.subplots(3, 1, figsize=(15, 9.5), sharex=True)


    # Panel 1: Data vs Counterfactual Prediction
    axes[0].plot(y_real, label='Control Group', linestyle='--', color=black_secondary, linewidth=1)
    axes[0].plot(serie_tratamiento, label='Treatment Group', linestyle='-', color=purple_dark, linewidth=1)
    axes[0].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
    axes[0].fill_between(range(len(y_real)-periodo_especifico, len(y_real)), lower_bound, upper_bound, color='gray', alpha=0.2)
    axes[0].set_title(f'Holdout: {holdout_target:.2f}% - MDE: {target_mde:.2f}')
    axes[0].yaxis.set_label_position('right')
    axes[0].set_ylabel('Original')
    axes[0].legend()
    axes[0].grid(True)

    # Panel 2: Point Difference 
    axes[1].plot(diferencia_puntual, label='Point Difference (Causal Effect)', color=purple_dark, linewidth=1)
    axes[1].fill_between(range(len(y_real)-periodo_especifico, len(y_real)), lower_bound_effect, upper_bound_effect, color='gray', alpha=0.2)

    axes[1].plot([0, len(y_real)], [0, 0], color='gray', linestyle='--', linewidth=2)
    axes[1].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
    axes[1].set_ylabel('Point Difference')
    axes[1].yaxis.set_label_position('right')
    axes[1].legend()
    axes[1].grid(True)

    # Panel 3: Cumulative Effect
    axes[2].plot(efecto_acumulativo, label='Cumulative Effect', color=purple_dark, linewidth=1)
    axes[2].fill_between(range(len(y_real)-periodo_especifico, len(y_real)), lower_bound_cumulative, upper_bound_cumulative, color='gray', alpha=0.2)
    axes[2].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
    axes[2].set_xlabel('Days')
    axes[2].yaxis.set_label_position('right')
    axes[2].set_ylabel('Cumulative Effect')
    axes[2].legend()
    axes[2].grid(True)

    plt.tight_layout()
    
    return fig, round(att,2), round(incremental,2)




def plot_impact_evaluation_report(results_evaluation):
        """
        Plot the impact evaluation results
        

        Args:
            counterfactual (array): Control group values
            treatment (array): Treatment group values
            period (int): Treatment period length
        """
        counterfactual = results_evaluation['predictions']
        treatment = results_evaluation['treatment']
        period = results_evaluation['period']

        point_difference = treatment - counterfactual
        cumulative_effect = ([0] * (len(treatment) - period)) + (np.cumsum(point_difference[len(treatment)-period:])).tolist()
        star_treatment = len(counterfactual) - period


        y_treatment = counterfactual[star_treatment:]
        point_difference_treatment = point_difference[star_treatment:]
        cumulative_effect_treatment = cumulative_effect[star_treatment:]

        mean_y_real = np.mean(y_treatment)
        std_dev_y_real = np.std(y_treatment)
        std_error_y_real = std_dev_y_real / np.sqrt(len(y_treatment))
        upper_bound = y_treatment + 1.96 * std_error_y_real
        lower_bound = y_treatment - 1.96 * std_error_y_real

        mean_point_difference = np.mean(point_difference_treatment)
        std_dev_point_difference = np.std(point_difference_treatment)
        std_error_point_difference = std_dev_point_difference / np.sqrt(len(y_treatment))
        upper_bound_pd = point_difference_treatment + 1.96 * std_error_point_difference
        lower_bound_pd = point_difference_treatment - 1.96 * std_error_point_difference


        mean_cumulative_effect = np.mean(cumulative_effect_treatment)
        std_dev_cumulative_effect = np.std(cumulative_effect_treatment)
        std_error_cumulative_effect = std_dev_cumulative_effect / np.sqrt(len(y_treatment))
        upper_bound_ce = cumulative_effect_treatment + 1.96 * std_error_cumulative_effect
        lower_bound_ce = cumulative_effect_treatment - 1.96 * std_error_cumulative_effect


        att = np.mean(treatment[star_treatment:] - counterfactual[star_treatment:])
        incremental = np.sum(treatment[star_treatment:] - counterfactual[star_treatment:])


        fig, axes = plt.subplots(3, 1, figsize=(15, 9.5), sharex=True)


        # Panel 1: Observed data vs counterfactual prediction
        axes[0].plot(counterfactual, label='Control Group', linestyle='--', color=black_secondary,linewidth=1)
        axes[0].plot(treatment, label='Treatment Group', linestyle='-', color=purple_dark,linewidth=1)
        axes[0].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
        axes[0].fill_between(range((star_treatment), len(counterfactual)),  lower_bound, upper_bound, color='gray', alpha=0.2)
        axes[0].yaxis.set_label_position('right')
        axes[0].set_ylabel('Original')
        axes[0].legend()
        axes[0].grid(True)

        # Panel 2: Point difference
        axes[1].plot(point_difference, label='Point Difference (Causal Effect)', color=purple_dark, linewidth=1)
        axes[1].fill_between(range((star_treatment), len(counterfactual)), lower_bound_pd, upper_bound_pd, color='gray', alpha=0.2)
        axes[1].plot([0, len(counterfactual)], [0, 0], color='gray', linestyle='--', linewidth=2)
        axes[1].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
        axes[1].set_ylabel('Point Difference')
        axes[1].yaxis.set_label_position('right')
        axes[1].legend()

        axes[1].grid(True)


        # Panel 3: Cumulative effect
        axes[2].plot(cumulative_effect, label='Cumulative Effect', color=purple_dark, linewidth=1)
        axes[2].fill_between(range((star_treatment), len(counterfactual)), lower_bound_ce, upper_bound_ce, color='gray', alpha=0.2)
        axes[2].axvline(x=star_treatment, color='black', linestyle='--', linewidth=1.5)
        axes[2].set_xlabel('Days')
        axes[2].yaxis.set_label_position('right')
        axes[2].set_ylabel('Cumulative Effect')
        axes[2].legend()
        axes[2].grid(True)

        plt.tight_layout()
        return fig,round(att,2), round(incremental,2)

def plot_permutation_test_report(results_evaluation, nivel_significancia=0.1):
    
    """
    Plot the permutation test results
    
    Args:
        results_evaluation (dict): Dictionary with results including predictions, treatment, period, and conformity scores
        nivel_significancia (float): Significance level for the permutation test
    """

    conformidades_nulas = results_evaluation['conformidades_nulas']
    conformidad_observada = results_evaluation['conformidad_observada']


    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(conformidades_nulas, bins=30, kde=True, color=blue, alpha=0.6, label='Null Conformities', ax=ax)
    ax.axvline(conformidad_observada, color='black', linestyle='--', linewidth=1.5, label='Observed Conformity')
    upper_bound = np.percentile(conformidades_nulas, 100 * (1 - (nivel_significancia / 2)))
    ax.axvspan(upper_bound, max(conformidades_nulas), color=purple_light, alpha=0.2,label='Significance Zone')
    ax.set_xlabel("Conformity Score", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title("Permutation Test", fontsize=14)
    ax.legend()


    return fig 
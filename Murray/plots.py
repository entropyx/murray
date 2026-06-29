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
import matplotlib.ticker as ticker
from millify import millify
from statsmodels.stats.diagnostic import acorr_ljungbox
import matplotlib.ticker as mticker
from logger_config import get_logger


logger = get_logger("plots")

# Color palette
blue = "#3e7cb1"
green = "#87D8AD"
red = "#dd2d4a"
purple_dark = "#1B0043"
black_secondary = "#4D4C50"
purple_light = "#BBB2C7"
heatmap_green = "#84DA35"
heatmap_red = "#DA3835"

custom_colors = [
    "#3E7CB1",
    "#6596C1",
    "#C5D8EB",
    "#5F4D7B",
    "#211F24",
    "#4D4C50",
    "#1B0043",
    "#DD2D4A",
    "#C3EBD6",
    "#87D8AD",
]


def generate_gradient_palette(start_color, end_color, num_colors):
    """Generates a gradient color list from start_color to end_color."""
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_gradient", [start_color, end_color], N=num_colors
    )
    return [mcolors.to_hex(cmap(i / num_colors)) for i in range(num_colors)]


def plot_geodata(merged_data, custom_colors=custom_colors):
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

    y_min = merged_data["Y"].min()
    y_max = merged_data["Y"].max()

    locator = ticker.MaxNLocator(nbins=6)
    ticks = locator.tick_values(y_min, y_max)

    tick_texts = [millify(x, precision=1) for x in ticks]

    for i, (location, data) in enumerate(merged_data.groupby("location")):
        fig.add_trace(
            go.Scatter(
                x=data["time"],
                y=data["Y"],
                mode="lines",
                name=location,
                line=dict(width=1, color=custom_colors[i % len(custom_colors)]),
            )
        )

    last_points = merged_data.groupby("location").last().reset_index()

    for _, row in last_points.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row["time"]],
                y=[row["Y"]],
                mode="text",
                text=row["location"],
                textposition="middle right",
                showlegend=False,
                textfont=dict(size=12, color="black"),
            )
        )

    fig.update_layout(
        xaxis_title="Date",
        xaxis_title_font=dict(size=16, color="black"),
        xaxis=dict(tickformat="%b %Y", tickangle=45),
        xaxis_tickfont=dict(size=12, color="black"),
        xaxis_linecolor="#0d0808",
        xaxis_color="#0d0808",
        xaxis_showgrid=True,
        yaxis_title="Conversions",
        yaxis_title_font=dict(size=16, color="black"),
        yaxis_tickfont=dict(size=12, color="black"),
        yaxis_linecolor="#0d0808",
        yaxis_color="#0d0808",
        yaxis_showgrid=True,
        yaxis=dict(ticktext=tick_texts, tickvals=ticks, range=[y_min, y_max]),
        margin=dict(l=50, r=50, t=50, b=50),
        dragmode=False,
        showlegend=False,
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

    metrics = {"Size": [], "MAPE": [], "SMAPE": []}

    results_by_size = geo_test["simulation_results"]

    for size, result in results_by_size.items():
        treatment = result["Actual Target Metric (y)"]
        counterfactual = result["Predictions"]

        mape = mean_absolute_percentage_error(treatment, counterfactual)
        smape = (
            100
            / len(treatment)
            * np.sum(
                2
                * np.abs(counterfactual - treatment)
                / (np.abs(treatment) + np.abs(counterfactual))
            )
        )

        metrics["Size"].append(size)
        metrics["MAPE"].append(mape)
        metrics["SMAPE"].append(smape)

    fig = make_subplots(
        rows=1, cols=2, subplot_titles=["MAPE by Group Size", "SMAPE by Group Size"]
    )

    fig.add_trace(
        go.Scatter(
            x=metrics["Size"],
            y=metrics["MAPE"],
            mode="lines+markers",
            name="Value",
            marker=dict(color=blue),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=metrics["Size"],
            y=metrics["SMAPE"],
            mode="lines+markers",
            name="Value",
            marker=dict(color=black_secondary),
        ),
        row=1,
        col=2,
    )

    # fig.update_layout(
    #    template="plotly_white",
    #    margin=dict(l=50, r=50, t=50, b=50))

    fig.update_xaxes(title_text="Group Size", row=1, col=1)
    fig.update_xaxes(title_text="Group Size", row=1, col=2)

    fig.update_yaxes(title_text="Value", row=1, col=1)
    fig.update_yaxes(title_text="Value", row=1, col=2)

    return fig


def plot_counterfactuals(geo_test):
    """
    Plots the counterfactuals (actual vs. predicted values) for each group size.

    Args:
        geo_test (dict): A dictionary containing simulation results with actual and predicted metrics.

    Returns:
        None: Displays plots for each group size showing counterfactuals.
    """

    results_by_size = geo_test["simulation_results"]

    for size, result in results_by_size.items():
        treatment = result["Actual Target Metric (y)"]
        counterfactual = result["Predictions"]

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                y=treatment,
                mode="lines",
                name="Actual (Treatment)",
                line=dict(color=purple_dark, width=2),
            )
        )

        fig.add_trace(
            go.Scatter(
                y=counterfactual,
                mode="lines",
                name="Predicted (Counterfactual)",
                line=dict(color=black_secondary, width=2, dash="dash"),
            )
        )

        fig.update_layout(
            title=f"Counterfactual for Group Size {size}",
            xaxis_title="Time",
            yaxis_title="Metric Value",
            template="plotly_white",
            legend_title="Legend",
            margin=dict(l=50, r=50, t=50, b=50),
        )

        return fig


def plot_mde_results(results_by_size, sensitivity_results, periods):
    """
    Generates an interactive heatmap showing penalized MDE values that account for
    counterfactual quality and time period.
    Args:
        results_by_size: Dictionary containing simulation results
        sensitivity_results: Dictionary containing sensitivity results
        periods: List of periods to evaluate

    Returns:
        fig: Interactive heatmap figure
    """
    holdout_by_location = {
        size: data["Holdout Percentage"] for size, data in results_by_size.items()
    }

    sorted_sizes = sorted(
        holdout_by_location.keys(), key=lambda x: holdout_by_location[x]
    )

    def calculate_penalty_score(mde, period_idx, total_periods, size, results_by_size):
        """
        Calculates a score based on MDE, counterfactual quality (MAPE, SMAPE), p-value, statistical power, and time period.
        Longer periods are considered better as they provide more statistical confidence.
        Returns both the score and its components for hover information.
        """
        if pd.isna(mde):
            return None, None, None, None, None, None, None

        # Quality metrics
        mape = results_by_size[size].get("MAPE", 0)
        smape = results_by_size[size].get("SMAPE", 0)

        # Statistical metrics
        p_value = results_by_size[size].get("p_value", 1.0)  
        power = results_by_size[size].get("power", 0.0)      

        # Normalize metrics
        mape_factor = min(mape / 100, 1)
        smape_factor = min(smape / 100, 1)
        quality_score = (mape_factor + smape_factor) / 2

        # Normalize p-value (lower is better)
        p_value_score = 1 - min(p_value, 1)  
        
        # Normalize power (higher is better)
        power_score = min(power, 1)

        # MDE factor
        mde_factor = min(mde, 1)

        # Time factor - longer periods are better
        time_score = (period_idx + 1) / total_periods  

        # Calculate final score
        quality_weight = 0.20
        p_value_weight = 0.15
        power_weight = 0.55
        mde_weight = 0.09
        time_weight = 0.01

        final_score = (
            quality_weight * quality_score
            + p_value_weight * p_value_score
            + power_weight * power_score
            + mde_weight * (1 - mde_factor)  
            + time_weight * (1 - time_score)  
        )

        return final_score, mde, mape, smape, p_value, power, time_score

    heatmap_data = pd.DataFrame()
    hover_data = []

    for size in sorted_sizes:
        row = []
        hover_row = []
        period_results = sensitivity_results.get(size, {})

        for period_idx, period in enumerate(periods):
            mde = period_results.get(period, {}).get("MDE", None)
            score, original_mde, mape, smape, p_value, power, time_score = calculate_penalty_score(
                mde, period_idx, len(periods), size, results_by_size
            )
            row.append(score)
            hover_row.append(
                {
                    "MDE": f"{original_mde:.2%}" if original_mde is not None else "N/A",
                    "MAPE": f"{mape:.2f}%" if mape is not None else "N/A",
                    "SMAPE": f"{smape:.2f}%" if smape is not None else "N/A",
                    "P-Value": f"{p_value:.4f}" if p_value is not None else "N/A",
                    "Statistical Power": f"{power:.2%}" if power is not None else "N/A",
                    "Period Score": f"{time_score*100:.0f}%" if time_score is not None else "N/A"  
                }
            )
        heatmap_data[size] = row
        hover_data.append(hover_row)

    total_values = heatmap_data.size
    nan_values = heatmap_data.isna().sum().sum()
    nan_ratio = nan_values / total_values if total_values > 0 else 1

    if nan_ratio == 1:
        logger.error(
            "No satisfactory results found. The heatmap does not contain values (MDE) with the entered data."
        )
        raise ValueError(
            "No satisfactory results found. The heatmap does not contain values (MDE) with the entered data."
        )
    elif nan_ratio > 0.8:
        logger.error(
            "The analysis shows few satisfactory results. You can try modifying the parameters or entering a different target column."
        )
        raise ValueError(
            "The analysis shows few satisfactory results. You can try modifying the parameters or entering a different target column."
        )

    heatmap_data = heatmap_data.T
    heatmap_data.columns = [f"Day-{i}" for i in periods]
    heatmap_data.index = [
        f"{holdout_by_location.get(size, 0):.2f}%" for size in sorted_sizes
    ]
    heatmap_data.index.name = "Treatment percentage (%)"

    y_labels = heatmap_data.index.tolist()
    x_labels = heatmap_data.columns.tolist()
    y_axis = [f"{100 - float(value.strip('%')):.2f}%" for value in y_labels]
    z_values = heatmap_data.values.tolist()

    annotations = [
        [f"{val:.2%}" if not pd.isna(val) else "" for val in row] for row in z_values
    ]

    fig = go.Figure()
    custom_colorscale = [[0, heatmap_green], [1, heatmap_red]]

    fig.add_trace(
        go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale=custom_colorscale,
            colorbar=dict(title="Quality Score"),
            colorbar_tickfont=dict(size=12, color="black"),
            hoverongaps=True,
            text=annotations,
            texttemplate="%{text}",
            textfont={"size": 12, "color": "black"},
            hovertemplate=(
                "Treatment size: %{customdata}<br>"
                + "Combined Score: %{text}<br>"
                + "MDE: %{customdata:MDE}<br>"
                + "MAPE: %{customdata:MAPE}<br>"
                + "SMAPE: %{customdata:SMAPE}<br>"
                + "P-Value: %{customdata:P-Value}<br>"
                + "Statistical Power: %{customdata:Statistical Power}<br>"
                + "Period Score: %{customdata:Period Score}<br>"
                + "<extra></extra>"
            ),
            showscale=True,
            xgap=1,
            ygap=1,
        )
    )

    scatter_x, scatter_y = np.meshgrid(range(len(x_labels)), range(len(y_labels)))
    scatter_x = scatter_x.flatten()
    scatter_y = scatter_y.flatten()

    fig.add_trace(
        go.Scatter(
            x=[x_labels[i] for i in scatter_x],
            y=[y_labels[i] for i in scatter_y],
            mode="markers",
            marker=dict(size=10, opacity=0),
            hoverinfo="none",
        )
    )

    fig.update_layout(
        margin=dict(l=90, r=10, t=20, b=75),
        dragmode=False,
        xaxis=dict(
            title="Treatment Periods",
            title_font=dict(size=16, color="black"),
            tickmode="array",
            tickvals=list(range(len(x_labels))),
            ticktext=x_labels,
            showgrid=True,
            tickfont=dict(size=12, color="black"),
        ),
        yaxis=dict(
            title="Treatment percentage (%)",
            title_font=dict(size=16, color="black"),
            tickmode="array",
            tickvals=list(range(len(y_labels))),
            ticktext=y_axis,
            type="category",
            showgrid=True,
            tickfont=dict(size=12, color="black"),
        ),
    )

    custom_data = []
    for s in sorted_sizes:
        custom_data.append([s] * len(periods))

    fig.data[0].customdata = custom_data
    fig.data[0].hovertemplate = "Treatment size: %{customdata}<br><extra></extra>"
    fig.data[0].hoverinfo = "skip"

    return fig


def print_weights(geo_test, treatment_percentage=None, num_locations=None):
    """
    Extracts control group weights based on holdout percentage or number of locations.

    Args:
        geo_test (dict): Dictionary containing simulation results.
        holdout_percentage (float, optional): The holdout percentage to filter by.
        num_locations (int, optional): The number of locations to filter by.

    Returns:
        pd.DataFrame: A DataFrame with control locations and their corresponding weights, sorted in descending order.
    """
    results_by_size = geo_test["simulation_results"]
    control_weights = []
    control_locations = []
    holdout_percentage = 100 - treatment_percentage

    for size, result in results_by_size.items():
        current_holdout = result["Holdout Percentage"].round(2)

        if holdout_percentage is not None and current_holdout == holdout_percentage:
            control_weights.extend(result["Weights"])
            control_locations.extend(result["Control Group"])

        if (
            num_locations is not None
            and len(result["Best Treatment Group"]) == num_locations
        ):
            control_weights.extend(result["Weights"])
            control_locations.extend(result["Control Group"])

    weights = pd.DataFrame(
        {"Control Location": control_locations, "Weights": control_weights}
    )

    weights = weights.sort_values(by="Weights", ascending=False).reset_index(drop=True)
    return weights


def print_locations(geo_test, treatment_percentage=None, num_locations=None):
    """
    Extracts treatment and control locations based on holdout percentage or number of locations.

    Args:
        geo_test (dict): Dictionary containing simulation results.
        holdout_percentage (float, optional): Holdout percentage to match.
        num_locations (int, optional): Number of locations to match.

    Returns:
        None: Prints the treatment and control locations.
    """
    holdout_percentage = 100 - treatment_percentage

    results_by_size = geo_test["simulation_results"]
    treatment_locations = []
    control_locations = []

    for size, result in results_by_size.items():
        current_holdout = result["Holdout Percentage"].round(2)

        if holdout_percentage is not None and current_holdout == holdout_percentage:
            treatment_locations.extend(result["Best Treatment Group"])
            control_locations.extend(result["Control Group"])

        if (
            num_locations is not None
            and len(result["Best Treatment Group"]) == num_locations
        ):
            treatment_locations.extend(result["Best Treatment Group"])
            control_locations.extend(result["Control Group"])

    print(f"Treatment Locations: {treatment_locations}")
    print(f"Control Locations: {control_locations}")


def plot_permutation_test(results_evaluation, Significance_level=0.1):
    """
    Plot the permutation test results using Plotly with KDE density curve.

    Args:
        null_stats (array): Distribution of null stats.
        observed_stat (float): Observed stat score.
        Significance_level (float): Significance level (default: 0.1).

    Returns:
        fig: Plotly figure.
    """

    null_stats = results_evaluation["null_stats"]
    observed_stat = results_evaluation["observed_stat"]

    upper_bound = np.percentile(null_stats, 100 * (1 - (Significance_level / 2)))
    lower_bound = np.percentile(null_stats, 100 * (Significance_level / 2))

    kde = stats.gaussian_kde(null_stats)
    x_kde = np.linspace(min(null_stats), max(null_stats), 300)
    y_kde = kde(x_kde)

    max_hist_y = max(kde(null_stats))

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=null_stats,
            nbinsx=30,
            histnorm="probability density",
            name="Null Distribution",
            marker=dict(color=blue, line=dict(color="black", width=1)),
            opacity=0.6,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=x_kde,
            y=y_kde,
            mode="lines",
            name="KDE Density",
            showlegend=False,
            line=dict(color="darkblue", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[observed_stat, observed_stat],
            y=[0, max_hist_y],
            mode="lines",
            name=f"Observed Difference: {observed_stat:.2f}",
            line=dict(color="black", dash="dash", width=1.5),
        )
    )

    def hex_to_rgba(hex_color, alpha=0.4):
        """Convierte un color HEX a RGBA con transparencia controlada."""
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return f"rgba({r},{g},{b},{alpha})"

    fig.add_trace(
        go.Scatter(
            x=[upper_bound, max(null_stats), max(null_stats), upper_bound],
            y=[0, 0, max_hist_y, max_hist_y],
            fill="toself",
            fillcolor=hex_to_rgba(purple_light, 0.3),
            line=dict(color="rgba(255,0,0,0)"),
            name="Upper Significance Zone",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[
                min(null_stats),
                lower_bound,
                lower_bound,
                min(null_stats),
                min(null_stats),
            ],
            y=[0, 0, max_hist_y, max_hist_y, 0],
            fill="toself",
            fillcolor=hex_to_rgba(purple_light, 0.3),
            line=dict(color="rgba(255,0,0,0)"),
            name="Lower Significance Zone",
        )
    )

    fig.update_layout(
        title="Permutation Test - Treatment vs Control Difference",
        xaxis_title="Difference (Treatment - Control)",
        yaxis_title="Density",
        template="plotly_white",
        bargap=0,
    )

    return fig


#####################################################################################################
####################################PLOTS FOR REPORTS################################################
#####################################################################################################


def plot_geodata_report(merged_data, custom_colors=custom_colors):
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
    sns.lineplot(
        x="time",
        y="Y",
        hue="location",
        data=merged_data,
        linewidth=1,
        ax=ax,
        palette=custom_colors,
    )
    last_points = merged_data.groupby("location").last().reset_index()
    for _, row in last_points.iterrows():
        ax.text(
            row["time"],
            row["Y"],
            row["location"],
            color="black",
            fontsize=12,
            ha="left",
            va="center",
        )

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Conversions", fontsize=12)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=45)
    ax.legend([], frameon=False)

    import matplotlib.ticker as mticker

    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: millify(x, precision=1))
    )

    return fig


def plot_metrics_report(geo_test):
    """
    Plots MAPE and SMAPE metrics for each group size.

    Args:
        geo_test (dict): A dictionary containing the simulation results, including predictions and actual metrics.

    Returns:
        None: Displays plots for MAPE and SMAPE metrics by group size.
    """

    metrics = {"Size": [], "MAPE": [], "SMAPE": []}
    results_by_size = geo_test["simulation_results"]

    for size, result in results_by_size.items():
        y = result["Actual Target Metric (y)"]
        predictions = result["Predictions"]

        mape = mean_absolute_percentage_error(y, predictions)
        smape = (
            100
            / len(y)
            * np.sum(2 * np.abs(predictions - y) / (np.abs(y) + np.abs(predictions)))
        )

        metrics["Size"].append(size)
        metrics["MAPE"].append(mape)
        metrics["SMAPE"].append(smape)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(25, 6))

    ax1.plot(metrics["Size"], metrics["MAPE"], marker="o", color=blue)
    ax1.set_title("MAPE by Group Size")
    ax1.set_xlabel("Group Size")
    ax1.set_ylabel("MAPE")

    ax2.plot(metrics["Size"], metrics["SMAPE"], marker="o", color=black_secondary)
    ax2.set_title("SMAPE by Group Size")
    ax2.set_xlabel("Group Size")
    ax2.set_ylabel("SMAPE")

    ax1.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: millify(x, precision=1))
    )
    ax2.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: millify(x, precision=1))
    )

    plt.tight_layout()
    return fig


def plot_permutation_test_report(results_evaluation, Significance_level=0.1):
    """
    Plot the permutation test results

    Args:
        results_evaluation (dict): Dictionary with results including predictions, treatment, period, and stats scores
        Significance_level (float): Significance level for the permutation test
    """

    null_stats = results_evaluation["null_stats"]
    observed_stat = results_evaluation["observed_stat"]

    sns.set_theme(style="whitegrid")

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.histplot(
        null_stats, bins=30, kde=True, color=blue, alpha=0.6, label="Null Distribution", ax=ax
    )
    ax.axvline(
        observed_stat,
        color="black",
        linestyle="--",
        linewidth=1.5,
        label=f"Observed Difference: {observed_stat:.2f}",
    )
    lower_bound = np.percentile(null_stats, 100 * (Significance_level / 2))
    upper_bound = np.percentile(null_stats, 100 * (1 - (Significance_level / 2)))
    ax.axvspan(
        min(null_stats),
        lower_bound,
        color=purple_light,
        alpha=0.2,
        label="Significance Zone (Lower)",
    )
    ax.axvspan(
        upper_bound,
        max(null_stats),
        color=purple_light,
        alpha=0.2,
        label="Significance Zone (Upper)",
    )
    ax.set_xlabel("Difference (Treatment - Control)", fontsize=12)
    ax.set_ylabel("Frequency", fontsize=12)
    ax.set_title("Permutation Test - Treatment vs Control Difference")
    ax.legend()

    return fig


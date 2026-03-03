import numpy as np
from sklearn.preprocessing import MinMaxScaler
from Murray.main import select_controls, SyntheticControl
from Murray.auxiliary import market_correlations, handle_duplicates
from Murray.plots import calculate_confidence_bands, calculate_optimal_noise_scale
import pandas as pd
from logger_config import get_logger

logger = get_logger("post_analysis")


def run_geo_evaluation(
    data_input,
    start_treatment,
    end_treatment,
    treatment_group,
    spend,
    n_permutations=50000,
    inference_type="iid",
    significance_level=0.1,
    excluded_control_locations=None,
):
    logger.info("Starting run_geo_evaluation")
    logger.info(f"Input data shape: {data_input.shape}")
    logger.info(f"Treatment group: {treatment_group}")
    logger.info(f"Start treatment: {start_treatment}, End treatment: {end_treatment}")
    logger.info(
        f"n_permutations: {n_permutations}, significance_level: {significance_level}"
    )

    random_sate = data_input["location"].unique()[0]
    filtered_data = data_input[data_input["location"] == random_sate].copy()
    start_treatment = pd.to_datetime(start_treatment)
    end_treatment = pd.to_datetime(end_treatment)
    filtered_data["time"] = pd.to_datetime(filtered_data["time"])
    start_idx = (filtered_data["time"].dt.date == start_treatment.date()).idxmax()
    end_idx = (filtered_data["time"].dt.date == end_treatment.date()).idxmax()
    start_position_treatment = filtered_data.index.get_loc(start_idx)
    end_position = filtered_data.index.get_loc(end_idx)
    end_position_treatment = end_position + 1

    logger.info(
        f"Treatment period positions: {start_position_treatment} to {end_position_treatment}"
    )

    def smape(A, F):
        return (
            100 / len(A) * np.sum(2 * np.abs(F - A) / (np.abs(A) + np.abs(F + 1e-10)))
        )

    logger.info("Generating correlation matrix...")
    correlation_matrix = market_correlations(data_input)

    logger.info("Selecting control group...")
    control_group = select_controls(
        correlation_matrix=correlation_matrix,
        treatment_group=treatment_group,
        min_correlation=0.8,
        excluded_control_locations=excluded_control_locations,
    )
    logger.info(f"Control group selected: {control_group}")

    period = end_position_treatment - start_position_treatment

    # Check for duplicate entries and handle them
    data_input = handle_duplicates(
        data_input, subset=["time", "location"], agg_method="mean"
    )

    df_pivot = data_input.pivot(index="time", columns="location", values="Y")
    logger.info(f"Pivot table shape: {df_pivot.shape}")
    logger.info(f"Available locations: {sorted(df_pivot.columns.tolist())}")

    # For model training, truncate data until end_treatment to avoid using future data
    X_train_data = df_pivot[control_group].iloc[:end_position_treatment].values
    y_train_data = df_pivot[treatment_group].iloc[:end_position_treatment].sum(axis=1).values
    
    # For plotting and full analysis, use complete dataset
    X_full = df_pivot[control_group].values
    y_full = df_pivot[treatment_group].sum(axis=1).values
    
    time_index = np.arange(end_position_treatment)  # Training time index
    time_index_full = np.arange(len(df_pivot))      # Full time index for plotting

    logger.info("Scaling data...")
    scaler_x = MinMaxScaler()
    scaler_y = MinMaxScaler()

    # Scale training data
    X_scaled = scaler_x.fit_transform(X_train_data)
    y_scaled = scaler_y.fit_transform(y_train_data.reshape(-1, 1))

    X_train, X_test = (
        X_scaled[:start_position_treatment],
        X_scaled[start_position_treatment:],
    )
    y_train, y_test = (
        y_scaled[:start_position_treatment],
        y_scaled[start_position_treatment:],
    )

    time_train = time_index[:start_position_treatment]
    time_test = time_index[start_position_treatment:]

    if len(X_train) == 0:
        raise ValueError(
            f"No pre-treatment periods available for training. "
            f"The treatment start date ({start_treatment}) is at or before the beginning of the dataset. "
            f"Please select a later treatment start date."
        )

    logger.info("Fitting synthetic control model...")
    model = SyntheticControl(use_ridge_adjustment=True, ridge_alpha=1.0)
    model.fit(X_train, y_train, time_train=time_train)
    logger.info("Model fitted successfully")

    logger.info("Making predictions...")
    predictions_test, _ = model.predict(X_test, time_index=time_test)
    predictions_truncated, weights = model.predict(X_scaled, time_index=time_index)
    
    # Generate predictions for full dataset (including post-treatment)
    X_full_scaled = scaler_x.transform(X_full)
    predictions_full_complete, _ = model.predict(X_full_scaled, time_index=time_index_full)

    # Filter control group based on weights
    filtered_control_group, filtered_weights = model.filter_controls_by_weights(
        control_group, min_weight_threshold=0.001
    )

    # Process truncated data (for analysis metrics)
    counterfactual_truncated = predictions_truncated.reshape(-1, 1)
    counterfactual_truncated = scaler_y.inverse_transform(counterfactual_truncated)
    treatment_truncated = y_train_data.reshape(-1, 1)
    
    counterfactual = counterfactual_truncated.flatten()
    treatment = treatment_truncated.flatten()
    y_original = scaler_y.inverse_transform(y_scaled)
    y_original = y_original.flatten()
    
    # Process complete data (for plotting with post-treatment)
    counterfactual_full_complete = predictions_full_complete.reshape(-1, 1)
    counterfactual_full_complete = scaler_y.inverse_transform(counterfactual_full_complete)
    treatment_full_complete = y_full.reshape(-1, 1)
    
    counterfactual_complete = counterfactual_full_complete.flatten()
    treatment_complete = treatment_full_complete.flatten()

    logger.info("Calculating metrics...")
    logger.info(f"Data shapes - treatment: {treatment.shape}, counterfactual: {counterfactual.shape}")
    
    MAPE = round(np.mean(np.abs((y_original - counterfactual) / (y_original + 1e-10))) * 100, 2)
    SMAPE = round(smape(y_original, counterfactual), 2)

    # Calculate percentage lift (only during treatment period)
    treatment_period_sum = np.sum(treatment[start_position_treatment:end_position_treatment])
    counterfactual_period_sum = np.sum(counterfactual[start_position_treatment:end_position_treatment])
    lift_difference = treatment_period_sum - counterfactual_period_sum
    
    logger.info(f"Treatment period sum: {treatment_period_sum}")
    logger.info(f"Counterfactual period sum: {counterfactual_period_sum}")
    logger.info(f"Lift difference (treatment - counterfactual): {lift_difference}")
    
    percenge_lift = round((lift_difference / np.abs(counterfactual_period_sum)) * 100, 2)

    def compute_residuals(y_treatment, y_control):
        return y_treatment - y_control

    residuals = compute_residuals(treatment, counterfactual)
    treatment_residuals = residuals[start_position_treatment:end_position_treatment]

    def stat_func(x):
        return np.sum(x)

    observed_stat = stat_func(treatment_residuals)
    logger.info(f"Observed statistic (sum of residuals): {observed_stat}")
    logger.info(f"Manual verification - observed_stat should equal lift_difference: {lift_difference}")

    logger.info(f"Starting permutation test with {n_permutations} permutations...")
    null_stats = []

    for i in range(n_permutations):
        if i % 10000 == 0 and i > 0:
            logger.info(f"Completed {i}/{n_permutations} permutations")
        permuted_residuals = np.random.permutation(residuals)
        permuted = permuted_residuals[start_position_treatment:end_position_treatment]
        null_stats.append(stat_func(permuted))
    null_stats = np.array(null_stats)

    logger.info("Permutation test completed, calculating p-value and power...")
    p_value = round(float(np.mean(abs(null_stats) >= abs(observed_stat))), 2)
    power = round(float(np.mean(p_value < significance_level)), 2)

    length_treatment = len(treatment_group)

    # Calculate holdout percentage - percentage of metric that treatment states represent
    total_metric_sum = df_pivot.sum(axis=1).sum()  # Sum of all locations across all time periods
    treatment_metric_sum = df_pivot[treatment_group].sum(axis=1).sum()  # Sum of treatment locations across all time periods
    holdout_percentage = 100 - round((treatment_metric_sum / total_metric_sum) * 100, 2) 

    logger.info(f"Final results:")
    logger.info(f"  MAPE: {MAPE:.4f}")
    logger.info(f"  SMAPE: {SMAPE:.4f}")
    logger.info(f"  Percentage lift: {percenge_lift:.4f}%")
    logger.info(f"  P-value: {p_value:.6f}")
    logger.info(f"  Power: {power:.4f}")
    logger.info(f"  Holdout percentage: {holdout_percentage:.2f}%")

    results_evaluation = {
        "MAPE": MAPE,
        "SMAPE": SMAPE,
        "counterfactual": np.round(counterfactual, 2),
        "treatment": np.round(treatment, 2),
        "p_value": p_value,
        "power": power,
        "percenge_lift": percenge_lift,
        "control_group": filtered_control_group,
        "observed_stat": round(float(observed_stat), 2),
        "null_stats": np.round(null_stats, 2),
        "weights": np.round(filtered_weights, 2),
        "period": period,
        "spend": round(float(spend), 2),
        "length_treatment": length_treatment,
        "holdout_percentage": holdout_percentage,
        # Complete data for plotting (including post-treatment)
        "counterfactual_complete": np.round(counterfactual_complete, 2),
        "treatment_complete": np.round(treatment_complete, 2),
        "time_index_full": time_index_full,
        # Period information for plotting zones
        "start_position_treatment": start_position_treatment,
        "end_position_treatment": end_position_treatment,
        "total_periods": len(df_pivot),
    }

    logger.info("run_geo_evaluation completed successfully")
    return results_evaluation


def get_evaluation_chart_data(
    data_input,
    start_treatment,
    end_treatment,
    treatment_group,
    significance_level=0.05,
):
    """
    Extract only the data needed for plotting charts from evaluation results.

    Args:
        data_input: Input dataframe
        start_treatment: Treatment start date
        end_treatment: Treatment end date
        treatment_group: List of treatment locations
        significance_level: Significance level for confidence bands

    Returns:
        dict: Dictionary containing all data needed for chart plotting
    """
    logger.info("Starting get_evaluation_chart_data")

    # First run the evaluation to get base results
    results = run_geo_evaluation(
        data_input, start_treatment, end_treatment, treatment_group, spend=0
    )

    # Extract base values
    treatment = results["treatment"]
    counterfactual = results["counterfactual"]
    period = results["period"]
    length_treatment = results["length_treatment"]

    # Get date information
    random_state = data_input["location"].unique()[0]
    filtered_data = data_input[data_input["location"] == random_state].copy()
    filtered_data["time"] = pd.to_datetime(filtered_data["time"])
    dates = filtered_data["time"].dt.date.astype(str).tolist()

    # Calculate treatment start position
    start_treatment = pd.to_datetime(start_treatment)
    start_idx = (filtered_data["time"].dt.date == start_treatment.date()).idxmax()
    start_position_treatment = filtered_data.index.get_loc(start_idx)

    # Calculate derived series
    point_difference = treatment - counterfactual
    cumulative_effect = ([0] * (len(treatment) - period)) + (
        np.cumsum(point_difference[len(treatment) - period:])
    ).tolist()

    # Extract treatment period data
    y_treatment = treatment[start_position_treatment:]
    point_difference_treatment = point_difference[start_position_treatment:]
    cumulative_effect_treatment = cumulative_effect[start_position_treatment:]

    # Calculate confidence bands
    ci = 1 - significance_level
    noise_scale = calculate_optimal_noise_scale(y_treatment, counterfactual)

    lower_bound, upper_bound = calculate_confidence_bands(
        y_treatment, noise_scale=noise_scale, ci=ci
    )
    lower_bound_pd, upper_bound_pd = calculate_confidence_bands(
        point_difference_treatment, ci=ci
    )
    lower_bound_ce, upper_bound_ce = calculate_confidence_bands(
        cumulative_effect_treatment, ci=ci
    )

    # Calculate aggregate values
    lower_bound_value = np.sum(lower_bound)
    upper_bound_value = np.sum(upper_bound)
    prediction_value = np.sum(treatment[start_position_treatment:])

    # Calculate ATT and incremental
    att = np.mean(treatment[start_position_treatment:] - counterfactual[start_position_treatment:])
    att = att / length_treatment
    incremental = np.sum(treatment[start_position_treatment:] - counterfactual[start_position_treatment:])

    # Calculate pre/post treatment data
    pre_treatment = treatment[start_position_treatment - period : start_position_treatment]
    pre_counterfactual = counterfactual[start_position_treatment - period : start_position_treatment]
    post_treatment = treatment[start_position_treatment:]
    post_counterfactual = counterfactual[start_position_treatment:]

    chart_data = {
        # Base series
        "dates": dates,
        "treatment": np.round(treatment, 2).tolist(),
        "counterfactual": np.round(counterfactual, 2).tolist(),
        "point_difference": np.round(point_difference, 2).tolist(),
        "cumulative_effect": np.round(cumulative_effect, 2).tolist(),

        # Treatment period data
        "treatment_dates": dates[start_position_treatment:],
        "y_treatment": np.round(y_treatment, 2).tolist(),
        "point_difference_treatment": np.round(point_difference_treatment, 2).tolist(),
        "cumulative_effect_treatment": np.round(cumulative_effect_treatment, 2).tolist(),

        # Confidence bands
        "lower_bound": np.round(lower_bound, 2).tolist(),
        "upper_bound": np.round(upper_bound, 2).tolist(),
        "lower_bound_pd": np.round(lower_bound_pd, 2).tolist(),
        "upper_bound_pd": np.round(upper_bound_pd, 2).tolist(),
        "lower_bound_ce": np.round(lower_bound_ce, 2).tolist(),
        "upper_bound_ce": np.round(upper_bound_ce, 2).tolist(),

        # Aggregate values
        "lower_bound_value": round(float(lower_bound_value), 2),
        "upper_bound_value": round(float(upper_bound_value), 2),
        "prediction_value": round(float(prediction_value), 2),
        "att": round(float(att), 2),
        "incremental": round(float(incremental), 2),

        # Pre/post treatment periods
        "pre_treatment": np.round(pre_treatment, 2).tolist(),
        "pre_counterfactual": np.round(pre_counterfactual, 2).tolist(),
        "post_treatment": np.round(post_treatment, 2).tolist(),
        "post_counterfactual": np.round(post_counterfactual, 2).tolist(),

        # Metadata
        "start_position_treatment": start_position_treatment,
        "period": period,
        "length_treatment": length_treatment,

        # Include key metrics from original evaluation
        "p_value": results["p_value"],
        "power": results["power"],
        "percenge_lift": results["percenge_lift"],
        "MAPE": results["MAPE"],
        "SMAPE": results["SMAPE"],
        "observed_stat": results["observed_stat"],
        "null_stats": results["null_stats"].tolist(),
        "control_group": results["control_group"],
        "weights": results["weights"],
        "holdout_percentage": results["holdout_percentage"],
    }

    logger.info("get_evaluation_chart_data completed successfully")
    return chart_data

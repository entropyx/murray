import numpy as np
from sklearn.preprocessing import MinMaxScaler
from Murray.main import select_controls, SyntheticControl
from Murray.auxiliary import market_correlations, handle_duplicates
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
    excluded_controls=None,
):
    logger.info("Starting run_geo_evaluation")
    logger.info(f"Input data shape: {data_input.shape}")
    logger.info(f"Treatment group: {treatment_group}")
    logger.info(f"Start treatment: {start_treatment}, End treatment: {end_treatment}")
    logger.info(
        f"n_permutations: {n_permutations}, significance_level: {significance_level}"
    )
    if excluded_controls:
        logger.info(f"Excluded controls: {excluded_controls}")

    random_sate = data_input["location"].unique()[0]
    filtered_data = data_input[data_input["location"] == random_sate].copy()
    start_treatment = pd.to_datetime(start_treatment, dayfirst=True)
    end_treatment = pd.to_datetime(end_treatment, dayfirst=True)
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
        excluded_controls=excluded_controls,
    )
    logger.info(f"Control group selected: {control_group}")

    period = end_position_treatment - start_position_treatment

    # Check for duplicate entries and handle them
    data_input = handle_duplicates(
        data_input, subset=["time", "location"], agg_method="mean"
    )

    df_pivot = data_input.pivot(index="time", columns="location", values="Y")
    logger.info(f"Pivot table shape: {df_pivot.shape}")

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
    
    MAPE = np.mean(np.abs((y_original - counterfactual) / (y_original + 1e-10))) * 100
    SMAPE = smape(y_original, counterfactual)

    # Calculate percentage lift (only during treatment period)
    treatment_period_sum = np.sum(treatment[start_position_treatment:end_position_treatment])
    counterfactual_period_sum = np.sum(counterfactual[start_position_treatment:end_position_treatment])
    lift_difference = treatment_period_sum - counterfactual_period_sum
    
    logger.info(f"Treatment period sum: {treatment_period_sum}")
    logger.info(f"Counterfactual period sum: {counterfactual_period_sum}")
    logger.info(f"Lift difference (treatment - counterfactual): {lift_difference}")
    
    percenge_lift = (lift_difference / np.abs(counterfactual_period_sum)) * 100

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
    p_value = np.mean(abs(null_stats) >= abs(observed_stat))
    power = np.mean(p_value < significance_level)

    length_treatment = len(treatment_group)

    logger.info(f"Final results:")
    logger.info(f"  MAPE: {MAPE:.4f}")
    logger.info(f"  SMAPE: {SMAPE:.4f}")
    logger.info(f"  Percentage lift: {percenge_lift:.4f}%")
    logger.info(f"  P-value: {p_value:.6f}")
    logger.info(f"  Power: {power:.4f}")

    results_evaluation = {
        "MAPE": MAPE,
        "SMAPE": SMAPE,
        "counterfactual": counterfactual,
        "treatment": treatment,
        "p_value": p_value,
        "power": power,
        "percenge_lift": percenge_lift,
        "control_group": filtered_control_group,
        "observed_stat": observed_stat,
        "null_stats": null_stats,
        "weights": filtered_weights,
        "period": period,
        "spend": spend,
        "length_treatment": length_treatment,
        # Complete data for plotting (including post-treatment)
        "counterfactual_complete": counterfactual_complete,
        "treatment_complete": treatment_complete,
        "time_index_full": time_index_full,
        # Period information for plotting zones
        "start_position_treatment": start_position_treatment,
        "end_position_treatment": end_position_treatment,
        "total_periods": len(df_pivot),
    }

    logger.info("run_geo_evaluation completed successfully")
    return results_evaluation

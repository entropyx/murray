import os
import warnings

import numpy as np

from logger_config import get_logger

from .plots import plot_mde_results
from .auxiliary import market_correlations
from .parallel import _limit_blas_threads  # noqa: F401
from .selection import (  # noqa: F401
    select_treatments,
    select_controls,
    select_treatments_exclusive,
    select_controls_exclusive,
)
from .synthetic_control import (  # noqa: F401
    SyntheticControl,
    smape,
    scaled_l2_imbalance,
    _fit_sc_counterfactual,
    _rolling_origin_smapes,
    _select_lambda_ascm,
    _fit_sc_auto,
    _auto_engine_decision,
    select_engine_isolated,
    _ASCM_LAMBDAS,
    _ASCM_MIN_IMPROVEMENT,
)
from .power import (  # noqa: F401
    apply_lift,
    calculate_conformity,
    compute_residuals,
    _auto_block_size,
    _has_serial_dependence,
    _resolve_inference_type,
    _block_permutation,
    _moving_block_bootstrap,
    calculate_minimum_sample_size,
    simulate_power,
    run_simulation,
    _init_simulation_worker,
    _run_simulation_task,
    _select_significant_mde,
    evaluate_sensitivity,
)
from .inference import (  # noqa: F401
    compute_falsification_metrics,
    flag_placebo_bias_vs_mde,
    conformal_att_interval,
    attach_conformal_design_margins,
    conformal_window_margin,
    conformal_pointwise_bands,
)
from .better_groups import (  # noqa: F401
    BetterGroups,
    evaluate_group,
    evaluate_group_exclusive,
    _evaluate_group_isolated,
    _init_bettergroups_worker,
    _evaluate_group_worker,
    _evaluate_group_exclusive_worker,
)
from .multicell import (  # noqa: F401
    _resolve_multicell_feasibility,
    partition_locations_systematic,
    _finalize_multicell_controls,
    _cell_rank_key,
    _results_by_cell_for_sensitivity,
    optimize_global_multicell,
)


warnings.filterwarnings("ignore", message=".*ScriptRunContext.*", category=UserWarning)

logger = get_logger("main")


def is_streamlit_context():
    """Check if we're running in a Streamlit context."""
    return (
        "STREAMLIT_SERVER_PORT" in os.environ
        or "STREAMLIT_SERVER_ADDRESS" in os.environ
    )


def transform_results_data(results_by_size):
    """
    Transforms the data to ensure compatibility with the heatmap.
    Handles both single-cell (dict of dicts) and multi-cell (dict of lists) results.
    """
    transformed_data = {}

    for size, data in results_by_size.items():
        if isinstance(data, list):
            if data:
                group_data = data[0]
                transformed_data[size] = {
                    "Best Treatment Group": ", ".join(
                        group_data["Best Treatment Group"]
                    ),
                    "Control Group": ", ".join(group_data["Control Group"]),
                    "MAPE": float(group_data["MAPE"]),
                    "SMAPE": float(group_data["SMAPE"]),
                    "Actual Target Metric (y)": (
                        group_data["Actual Target Metric (y)"].tolist()
                        if hasattr(group_data["Actual Target Metric (y)"], "tolist")
                        else group_data["Actual Target Metric (y)"]
                    ),
                    "Predictions": (
                        group_data["Predictions"].tolist()
                        if hasattr(group_data["Predictions"], "tolist")
                        else group_data["Predictions"]
                    ),
                    "Weights": (
                        group_data["Weights"].tolist()
                        if hasattr(group_data["Weights"], "tolist")
                        else group_data["Weights"]
                    ),
                    "Holdout Percentage": float(group_data["Holdout Percentage"]),
                }
        else:
            transformed_data[size] = {
                "Best Treatment Group": ", ".join(data["Best Treatment Group"]),
                "Control Group": ", ".join(data["Control Group"]),
                "MAPE": float(data["MAPE"]),
                "SMAPE": float(data["SMAPE"]),
                "Actual Target Metric (y)": (
                    data["Actual Target Metric (y)"].tolist()
                    if hasattr(data["Actual Target Metric (y)"], "tolist")
                    else data["Actual Target Metric (y)"]
                ),
                "Predictions": (
                    data["Predictions"].tolist()
                    if hasattr(data["Predictions"], "tolist")
                    else data["Predictions"]
                ),
                "Weights": (
                    data["Weights"].tolist()
                    if hasattr(data["Weights"], "tolist")
                    else data["Weights"]
                ),
                "Holdout Percentage": float(data["Holdout Percentage"]),
            }

    return transformed_data


def run_geo_analysis_streamlit_app(
    data,
    maximum_treatment_percentage,
    significance_level,
    deltas_range,
    periods_range,
    excluded_locations,
    progress_bar_1=None,
    status_text_1=None,
    progress_bar_2=None,
    status_text_2=None,
    n_permutations_per_test=3000,
    n_power_simulations=40,
    multicell_config=None,
    test_type="sum",
    inference_type="iid",
    global_optimization=False,
    progress_updater=None,
    excluded_control_locations=None,
    alternative="two-sided",
):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        maximum_treatment_percentage (float): Maximum treatment percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        excluded_locations (list): List of states to exclude from the analysis.
        progress_bar_1 (callable): Progress bar updater for group optimization phase.
        status_text_1 (callable): Status text updater for group optimization phase.
        progress_bar_2 (callable): Progress bar updater for sensitivity evaluation phase.
        status_text_2 (callable): Status text updater for sensitivity evaluation phase.
        n_permutations_per_test (int): Number of permutations per test for sensitivity evaluation (default: 3000).
        n_power_simulations (int): Number of power simulations to run (default: 40).
        multicell_config (dict): Configuration for multi-cell mode with 'sizes' and 'top_n' keys.
        test_type (str): Statistical test type ("sum", "mean_diff", "t_test", "median_diff").
        inference_type (str): Type of inference ("iid" or "block").
        global_optimization (bool): Whether to use global optimization for multi-cell mode.

    Returns:
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensitivity_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
        None: If analysis fails due to insufficient data or invalid configuration.

    Note (ISS-9 — engineering defaults, not standards):
        ``top_k=None`` (all eligible donors), ``fpr_gate_multiplier=2.0``,
        ``max_abs_lift_in_zero=3.0`` and ``top_k_finalists=10`` (in BetterGroups) are
        Murray's own engineering defaults, NOT GeoLift/literature standards. GeoLift only
        gives qualitative guidance ("near zero") plus the ``power>0.8`` / ``alpha`` con-
        vention. Read the 3% ``abs_lift_in_zero`` ceiling relative to the achievable MDE
        (see ``flag_placebo_bias_vs_mde``), and tune all four to the dataset.
        ``alternative`` ("greater"/"less") is a PRE-REGISTERED direction choice, not a fix
        for a biased control (the abs_lift_in_zero gate, direction-agnostic, catches drift).
    """
    logger.info("Starting run_geo_analysis_streamlit_app............")
    logger.info("=" * 80)
    logger.info("PARAMETERS:")
    logger.info(f"  - data shape: {data.shape}")
    logger.info(f"  - maximum_treatment_percentage: {maximum_treatment_percentage}")
    logger.info(f"  - significance_level: {significance_level}")
    logger.info(f"  - deltas_range: {deltas_range}")
    logger.info(f"  - periods_range: {periods_range}")
    logger.info(f"  - excluded_locations (treatments): {excluded_locations}")
    logger.info(f"  - excluded_control_locations (control): {excluded_control_locations}")
    logger.info(f"  - multicell_config: {multicell_config}")
    logger.info("=" * 80)

    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
        print("Simulation in progress........")

    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)
    # logger.info(f'Deltas: {deltas}')
    # logger.info(f'Periods: {periods}')

    # Step 1: Generate market correlations
    logger.info("Step 1: Generating market correlations.....")
    if progress_updater:
        progress_updater(0.1, "Generating market correlations")
    correlation_matrix = market_correlations(data)
    logger.info(f"Market correlations generated successfully.")

    # Step 2: Find the best groups for control and treatment
    logger.info("Step 2: Finding best groups for control and treatment.....")
    if progress_updater:
        progress_updater(0.3, "Finding best treatment and control groups")
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        maximum_treatment_percentage=maximum_treatment_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1,
        multicell_config=multicell_config,
        global_optimization=global_optimization,
        excluded_control_locations=excluded_control_locations,
    )

    if simulation_results is None:
        logger.error("BetterGroups returned None, stopping execution")
        return None

    # Improved logging for different modes
    if global_optimization and multicell_config and "global_experiment" in simulation_results:
        cell_count = len(simulation_results["global_experiment"])
        logger.info(f"BetterGroups completed successfully. Global multicell experiment with {cell_count} cells")
        if progress_updater:
            progress_updater(0.7, f"Global multicell optimization completed with {cell_count} cells")
    elif multicell_config:
        total_groups = sum(len(groups) for groups in simulation_results.values())
        logger.info(f"BetterGroups completed successfully. Multicell results for {len(simulation_results)} sizes ({total_groups} total groups)")
        if progress_updater:
            progress_updater(0.7, f"Multicell optimization completed for {len(simulation_results)} sizes ({total_groups} groups)")
    else:
        logger.info(f"BetterGroups completed successfully. Results for {len(simulation_results)} sizes")
        if progress_updater:
            progress_updater(0.7, f"Group optimization completed for {len(simulation_results)} sizes")

    # Step 3: Evaluate sensitivity for different deltas and periods
    logger.info("Step 3: Evaluating sensitivity for different deltas and periods.....")
    if status_text_2:
        status_text_2.text("Starting sensitivity analysis for different deltas and periods")
        
        # Also force advance the stage index directly as backup
        if hasattr(status_text_2, 'progress_updater'):
            status_text_2.progress_updater.current_stage_index = 3
            status_text_2.progress_updater.current_stage = "Sensitivity Analysis"

    # Handle sensitivity analysis for different modes
    try:
        if global_optimization and multicell_config and "global_experiment" in simulation_results:
            logger.info("Detected global optimization results, transforming data for sensitivity analysis")
            # Build the sensitivity input keyed by CELL number (not size) so each cell —
            # including multiple cells of the same size — gets its own sensitivity.
            global_experiment = simulation_results["global_experiment"]
            results_by_cell = _results_by_cell_for_sensitivity(global_experiment)

            logger.info("Starting sensitivity evaluation for global optimization results (keyed by cell)")
            # Run sensitivity analysis per cell; sensitivity_results is keyed by cell number.
            sensitivity_results, series_lifts = evaluate_sensitivity(
                results_by_cell,
                deltas,
                periods,
                n_permutations_per_test,
                significance_level,
                test_type=test_type,
                inference_type=inference_type,
                alternative=alternative,
                progress_bar=progress_bar_2,
                status_text=status_text_2,
            )
        else:
            logger.info("Starting sensitivity evaluation for standard results")
            sensitivity_results, series_lifts = evaluate_sensitivity(
                simulation_results,
                deltas,
                periods,
                n_permutations_per_test,
                significance_level,
                test_type=test_type,
                inference_type=inference_type,
                alternative=alternative,
                progress_bar=progress_bar_2,
                status_text=status_text_2,
            )
        logger.info("evaluate_sensitivity call completed")
    except Exception as e:
        logger.error(f"Error during sensitivity evaluation: {str(e)}", exc_info=True)
        sensitivity_results = None
        series_lifts = None
    if sensitivity_results is not None:
        logger.info("Sensitivity evaluation completed successfully.")
        # Cross-check placebo bias vs the achievable MDE now that both exist (ISS-1 §2.4).
        try:
            flag_placebo_bias_vs_mde(simulation_results, sensitivity_results)
        except Exception as e:
            logger.debug(f"flag_placebo_bias_vs_mde skipped: {e}")
        # Attach the conformal band width per (size, period) for the DESIGN PDFs (B4).
        try:
            attach_conformal_design_margins(
                simulation_results, sensitivity_results, significance_level
            )
        except Exception as e:
            logger.debug(f"attach_conformal_design_margins skipped: {e}")
        if progress_updater:
            progress_updater(1.0, "Analysis completed successfully")
    else:
        logger.warning("Sensitivity evaluation returned None")
        if progress_updater:
            progress_updater(0.95, "Analysis completed with warnings")

    logger.info("run_geo_analysis_streamlit_app completed successfully")
    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts,
    }


def run_geo_analysis(
    data,
    maximum_treatment_percentage,
    significance_level,
    deltas_range,
    periods_range,
    excluded_locations,
    progress_bar_1=None,
    status_text_1=None,
    progress_bar_2=None,
    status_text_2=None,
    n_permutations_per_test=3000,
    n_power_simulations=40,
    test_type="sum",
    inference_type="iid",
    global_optimization=False,
    excluded_control_locations=None,
    alternative="two-sided",
):
    """
    Runs a complete geo analysis pipeline including market correlation, group optimization,
    sensitivity evaluation, and visualization of MDE results.

    Args:
        data (pd.DataFrame): Input data containing metrics for analysis.
        maximum_treatment_percentage (float): Maximum treatment percentage to ensure sufficient control.
        significance_level (float): Significance level for statistical testing.
        deltas_range (tuple): Range of delta values to evaluate as (start, stop, step).
        periods_range (tuple): Range of treatment periods to evaluate as (start, stop, step).
        excluded_locations (list): List of states to exclude from the analysis.
        progress_bar_1 (optional): First progress bar for UI updates.
        status_text_1 (optional): First status text for UI updates.
        progress_bar_2 (optional): Second progress bar for UI updates.
        status_text_2 (optional): Second status text for UI updates.
        n_permutations (int, optional): Number of permutations for sensitivity evaluation. Default is 10000.
        test_type (str, optional): Type of test to perform. Default is "sum".
        inference_type (str, optional): Type of inference to use. Default is "iid".
        global_optimization (bool, optional): Whether to use global optimization mode. Default is False.

    Returns:
        dict: Dictionary containing simulation results, sensitivity results, and adjusted series lifts.
            - "simulation_results": Results from group optimization.
            - "sensitivity_results": Sensitivity results for evaluated deltas and periods.
            - "series_lifts": Adjusted series for each delta and period.
    """
    logger.info("Starting run_geo_analysis............")
    logger.info("=" * 80)
    logger.info("PARAMETERS:")
    logger.info(f"  - data shape: {data.shape}")
    logger.info(f"  - maximum_treatment_percentage: {maximum_treatment_percentage}")
    logger.info(f"  - significance_level: {significance_level}")
    logger.info(f"  - deltas_range: {deltas_range}")
    logger.info(f"  - periods_range: {periods_range}")
    logger.info(f"  - excluded_locations (treatments): {excluded_locations}")
    logger.info(f"  - excluded_control_locations (control): {excluded_control_locations}")
    logger.info("=" * 80)

    if progress_bar_1 or progress_bar_2 or status_text_1 or status_text_2 is None:
        logger.info("Simulation in progress........")

    periods = list(np.arange(*periods_range))
    deltas = np.arange(*deltas_range)

    # Step 1: Generate market correlations
    correlation_matrix = market_correlations(data)

    # Step 2: Find the best groups for control and treatment
    simulation_results = BetterGroups(
        similarity_matrix=correlation_matrix,
        maximum_treatment_percentage=maximum_treatment_percentage,
        excluded_locations=excluded_locations,
        data=data,
        correlation_matrix=correlation_matrix,
        progress_updater=progress_bar_1,
        status_updater=status_text_1,
        excluded_control_locations=excluded_control_locations,
    )

    # Step 3: Evaluate sensitivity for different deltas and periods
    if global_optimization:
        logger.info(
            "Detected global optimization results, generating sensitivity data by size"
        )
        global_experiment = simulation_results["global_experiment"]
        results_by_size = {}

        # Group cells by size to create sensitivity data
        for cell in global_experiment:
            size = cell["Size"]
            if size not in results_by_size:
                results_by_size[size] = []

            result_dict = {
                "Best Treatment Group": cell["Best Treatment Group"],
                "Control Group": cell["Control Group"],
                "MAPE": cell["MAPE"],
                "SMAPE": cell["SMAPE"],
                "Actual Target Metric (y)": cell["Actual Target Metric (y)"],
                "Predictions": cell["Predictions"],
                "Weights": cell["Weights"],
                "observed_conformity": cell["observed_conformity"],
            }
            results_by_size[size].append(result_dict)

        # Run sensitivity analysis on the artificial results_by_size
        sensitivity_results, series_lifts = evaluate_sensitivity(
            results_by_size,
            deltas,
            periods,
            n_permutations_per_test,
            significance_level,
            test_type=test_type,
            inference_type=inference_type,
            alternative=alternative,
            progress_bar=progress_bar_2,
            status_text=status_text_2,
        )
    else:
        # Normal sensitivity analysis for regular results
        sensitivity_results, series_lifts = evaluate_sensitivity(
            simulation_results,
            deltas,
            periods,
            n_permutations_per_test,
            significance_level,
            test_type=test_type,
            inference_type=inference_type,
            alternative=alternative,
            progress_bar=progress_bar_2,
            status_text=status_text_2,
        )
    if sensitivity_results is not None:
        logger.info("Complete.")

    # Step 4: Generate MDE visualizations
    fig = plot_mde_results(simulation_results, sensitivity_results, periods)

    fig.show()

    return {
        "simulation_results": simulation_results,
        "sensitivity_results": sensitivity_results,
        "series_lifts": series_lifts,
    }

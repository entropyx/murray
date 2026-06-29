import concurrent.futures
import os
from math import comb

import numpy as np

from logger_config import get_logger

from .parallel import _limit_blas_threads

logger = get_logger("power")


def apply_lift(y, delta, start_treatment, end_treatment):
    """
    Apply a lift (delta) to a time series y between start_treatment and end_treatment

    Args:
        y (np.array): Original time series
        delta (float): Lift to apply (as a decimal)
        start_treatment (int/str): Start index of treatment period
        end_treatment (int/str): End index of treatment period

    Returns:
        np.array: Time series with lift applied
    """

    y = np.array(y).flatten()
    y_with_lift = y.copy()

    start_idx = max(0, int(start_treatment))
    end_idx = min(len(y_with_lift), int(end_treatment))

    if start_idx < end_idx:
        y_with_lift[start_idx:end_idx] = y_with_lift[start_idx:end_idx] * (1 + delta)
    else:
        raise ValueError("Start index is greater than end index")

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
    conformity = np.mean(y_real[start_treatment:end_treatment]) - np.mean(
        y_control[start_treatment:end_treatment]
    )
    return conformity


def compute_residuals(y_treatment, y_control):
    """
    Compute residuals between treatment and control series
    """

    y_treatment = np.array(y_treatment).flatten()
    y_control = np.array(y_control).flatten()
    return y_treatment - y_control


def _auto_block_size(residuals, max_fraction=0.25):
    """
    Data-driven block length for block permutation / moving-block bootstrap.

    The block must grow with the correlation length of the series (Politis & White
    2004) and with n (~n^(1/3), Hall-Horowitz-Jing 1995). We estimate the correlation
    length as the first ACF lag that enters the white-noise band (|acf| < 2/sqrt(n)),
    floor it at n^(1/3), and cap it at max_fraction*n so at least ~1/max_fraction
    blocks remain. A degenerate (constant) series falls back to the floor.

    Args:
        residuals (array-like): the series whose serial dependence sets the block length.
        max_fraction (float): upper bound on the block as a fraction of n (default 0.25).

    Returns:
        int: block size in [1, max_fraction*n].
    """
    x = np.asarray(residuals, dtype=float).flatten()
    n = len(x)
    if n < 2:
        return 1

    floor = max(1, int(round(n ** (1.0 / 3.0))))
    cap = max(1, int(max_fraction * n))

    x = x - np.mean(x)
    var = float(np.dot(x, x))
    if var <= 0:  # constant series -> no serial dependence
        return min(floor, cap)

    band = 2.0 / np.sqrt(n)
    max_lag = min(n - 1, cap)
    corr_length = 1
    for lag in range(1, max_lag + 1):
        acf = float(np.dot(x[:-lag], x[lag:])) / var
        corr_length = lag
        if abs(acf) < band:
            break

    block = max(floor, corr_length)
    return int(min(max(1, block), cap))


def _has_serial_dependence(residuals, n_lags=None, alpha=0.05):
    """
    Ljung-Box test for autocorrelation in a residual series.

    Returns True when the no-autocorrelation null is rejected at level ``alpha`` (i.e.
    the residuals are serially dependent and an iid permutation would understate the
    null variance, inflating Type-I error). Used to resolve ``inference_type="auto"``.

    Args:
        residuals (array-like): residual series to test.
        n_lags (int): lags to test (default min(10, n//5)).
        alpha (float): significance level for the test.

    Returns:
        bool: True if serial dependence is detected.
    """
    x = np.asarray(residuals, dtype=float).flatten()
    n = len(x)
    if n < 8 or np.var(x) <= 0:
        return False
    if n_lags is None:
        n_lags = max(1, min(10, n // 5))
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox

        lb = acorr_ljungbox(x, lags=[n_lags], return_df=True)
        return bool(float(lb["lb_pvalue"].iloc[-1]) < alpha)
    except Exception as e:  # pragma: no cover - defensive
        logger.debug(f"_has_serial_dependence fell back to iid (no dependence): {e}")
        return False


def _resolve_inference_type(inference_type, residuals):
    """
    Resolve ``"auto"`` to ``"block"`` (serial dependence present) or ``"iid"``.
    Explicit ``"iid"``/``"block"`` choices pass through unchanged.
    """
    if inference_type == "auto":
        return "block" if _has_serial_dependence(residuals) else "iid"
    return inference_type


def _block_permutation(data, block_size):
    """
    Perform block-based permutation for time series data to preserve local temporal structure.

    Args:
        data (numpy array): Time series data to permute
        block_size (int): Size of blocks to permute

    Returns:
        numpy array: Block-permuted data
    """
    data = np.array(data).flatten()
    n = len(data)

    blocks = []
    for i in range(0, n, block_size):
        block = data[i : i + block_size]
        blocks.append(block)

    np.random.shuffle(blocks)

    permuted = np.concatenate(blocks)

    return permuted[:n]


def _moving_block_bootstrap(series, block_size=None):
    """
    Künsch (1989) moving-block bootstrap.

    Resample overlapping blocks of length ``block_size`` with replacement and
    concatenate to the original length. Unlike an iid shuffle, this preserves the
    scale and short-range autocorrelation of the residual process, so Monte-Carlo
    replicas of the residuals are realistic (ISS-8 — replaces the ad-hoc 5%-of-std
    gaussian noise).

    Args:
        series (array-like): the residual process to resample.
        block_size (int): block length; ``None`` derives it via ``_auto_block_size``.

    Returns:
        np.ndarray: a bootstrap replica of the same length as ``series``.
    """
    x = np.asarray(series, dtype=float).flatten()
    n = len(x)
    if n == 0:
        return x.copy()
    if block_size is None:
        block_size = _auto_block_size(x)
    block_size = max(1, min(int(block_size), n))

    n_blocks = int(np.ceil(n / block_size))
    max_start = n - block_size  # inclusive upper bound for overlapping blocks
    pieces = []
    for _ in range(n_blocks):
        start = np.random.randint(0, max_start + 1) if max_start > 0 else 0
        pieces.append(x[start : start + block_size])

    return np.concatenate(pieces)[:n]


def calculate_minimum_sample_size(
    y_real,
    y_control,
    delta,
    period,
    target_power=0.8,
    significance_level=0.05,
    inference_type="iid",
    max_iterations=20,
    tolerance=0.05,
    n_permutations_sample_size=500,
    n_power_simulations_sample_size=30,
    alternative="two-sided",
):
    """
    Calculate minimum sample size needed to achieve target statistical power.

    Uses iterative approach to find the minimum number of time periods needed
    to achieve the target power level for a given effect size.

    Args:
        y_real (numpy array): Actual target metrics (full series)
        y_control (numpy array): Control metrics (full series)
        delta (float): Effect size to detect
        period (int): Treatment period duration
        target_power (float): Target statistical power (default 0.8)
        significance_level (float): Significance level (default 0.05)
        inference_type (str): Type of inference ("iid" or "block")
        max_iterations (int): Maximum number of iterations
        tolerance (float): Tolerance for power convergence
        n_permutations_sample_size (int): Number of permutations per test for sample size calculation (default 500)
        n_power_simulations_sample_size (int): Number of power simulations for sample size calculation (default 30)

    Returns:
        dict: Dictionary containing minimum sample size, achieved power, and iterations
    """
    logger.info(
        f"Calculating minimum sample size for delta={delta}, target_power={target_power}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    min_size = period + 10
    max_size = len(y_real)

    for iteration in range(max_iterations):
        current_size = (min_size + max_size) // 2

        if current_size >= len(y_real):
            logger.warning(
                f"Required sample size exceeds available data length ({len(y_real)})"
            )
            break

        y_real_sub = y_real[:current_size]
        y_control_sub = y_control[:current_size]

        try:
            _, power, power_ci, _, _ = simulate_power(
                y_real_sub,
                y_control_sub,
                delta,
                period,
                n_permutations_per_test=n_permutations_sample_size,
                significance_level=significance_level,
                test_type="sum",
                inference_type=inference_type,
                n_power_simulations=n_power_simulations_sample_size,
                alternative=alternative,
            )

            logger.debug(
                f"Iteration {iteration + 1}: size={current_size}, power={power:.3f}, target={target_power}"
            )

            if abs(power - target_power) <= tolerance:
                logger.info(
                    f"Converged at iteration {iteration + 1}: size={current_size}, power={power:.3f}"
                )
                return {
                    "minimum_sample_size": current_size,
                    "achieved_power": power,
                    "power_ci": power_ci,
                    "iterations": iteration + 1,
                    "converged": True,
                }

            if power < target_power:
                min_size = current_size + 1
            else:
                max_size = current_size - 1

        except Exception as e:
            logger.error(
                f"Error in sample size calculation at iteration {iteration + 1}: {str(e)}"
            )
            break

        if min_size >= max_size:
            break

    final_size = min(max_size, len(y_real))
    try:
        _, final_power, final_ci, _, _ = simulate_power(
            y_real[:final_size],
            y_control[:final_size],
            delta,
            period,
            n_permutations_per_test=n_permutations_sample_size,
            significance_level=significance_level,
            test_type="sum",
            inference_type=inference_type,
            n_power_simulations=n_power_simulations_sample_size,
        )

        logger.info(
            f"Sample size calculation completed: size={final_size}, power={final_power:.3f} (target={target_power})"
        )
        return {
            "minimum_sample_size": final_size,
            "achieved_power": final_power,
            "power_ci": final_ci,
            "iterations": max_iterations,
            "converged": False,
        }

    except Exception as e:
        logger.error(f"Final power calculation failed: {str(e)}")
        return {
            "minimum_sample_size": len(y_real),
            "achieved_power": None,
            "power_ci": None,
            "iterations": max_iterations,
            "converged": False,
        }


def simulate_power(
    y_real,
    y_control,
    delta,
    period,
    n_permutations_per_test=3000,
    significance_level=0.05,
    test_type="sum",
    inference_type="iid",
    stat_func=None,
    n_power_simulations=40,
    block_size="auto",
    alternative="two-sided",
):
    """
    Simulates statistical power using Monte Carlo simulation with permutation tests.

    Power is calculated by:
    1. Simulating multiple datasets under the alternative hypothesis (with effect)
    2. For each simulated dataset, running a permutation test
    3. Calculating the proportion of tests that reject the null hypothesis

    Args:
        y_real (numpy array): Actual target metrics.
        y_control (numpy array): Control metrics.
        delta (float): Effect size applied.
        period (int): Duration of the treatment period.
        n_permutations_per_test (int): Number of permutations per test.
        significance_level (float): Significance level.
        test_type (str): Statistical test type ("sum", "mean_diff", "t_test", "median_diff").
        inference_type (str): Permutation scheme — "iid" (default, GeoLift-aligned, exact
            under exchangeability), "block", or "auto" (Ljung-Box picks block vs iid from
            the residuals). Resolved once from the effect-free base residuals.
        stat_func (callable): Custom test statistic function.
        n_power_simulations (int): Number of Monte Carlo simulations for power calculation.
        block_size (int|"auto"): Block length for block permutation / bootstrap; "auto"
            derives it from the residual correlation length (_auto_block_size).
        alternative (str): p-value direction — "two-sided" (default), "greater" (positive
            lift only) or "less" (negative only). One-sided is a PRE-REGISTERED choice for a
            known effect direction, NOT a fix for a biased control: a drifting control is
            caught by the direction-agnostic abs_lift_in_zero gate, and the false-positive
            rate (power@delta=0) reported here is the honest Type-I check.

    Returns:
        tuple: (delta, power, power_ci, y_with_lift_sample, mean_p_value).
    """
    logger.debug(
        f"Starting simulate_power: delta={delta}, period={period}, n_permutations_per_test={n_permutations_per_test}, n_power_simulations={n_power_simulations}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    start_treatment = len(y_real) - period
    end_treatment = start_treatment + period

    logger.debug(f"Treatment period: {start_treatment} to {end_treatment}")

    # Default test statistic functions
    if stat_func is None:
        if test_type == "mean_diff":
            stat_func = lambda x: np.mean(x)
        elif test_type == "t_test":
            stat_func = lambda x: (
                np.mean(x) / (np.std(x) / np.sqrt(len(x))) if np.std(x) > 0 else 0
            )
        elif test_type == "median_diff":
            stat_func = lambda x: np.median(x)
        else:  # default sum
            stat_func = lambda x: np.sum(x)

    # Resolve the permutation scheme and block length ONCE from the effect-free
    # base residuals (ISS-2/3): "auto" picks block vs iid via Ljung-Box; "auto"
    # block_size derives the length from the residual correlation structure.
    base_residuals = compute_residuals(y_real, y_control)
    inference_type = _resolve_inference_type(inference_type, base_residuals)
    if not isinstance(block_size, (int, np.integer)):
        block_size = _auto_block_size(base_residuals)
    block_size = max(1, int(block_size))

    # Monte Carlo power simulation
    rejected_tests = 0
    p_values = []

    for sim in range(n_power_simulations):
        if sim % 50 == 0 and sim > 0:
            logger.debug(f"Completed {sim}/{n_power_simulations} power simulations")

        # Bootstrap the real residual process (ISS-8): resample blocks of the
        # effect-free base residuals (preserving scale + autocorrelation), rebuild
        # an effect-free treatment series off the control, then inject the effect in
        # the window. Replaces the ad-hoc 5%-of-std gaussian noise, which gave a
        # near-binary, mis-calibrated power@0 (~1.0 for a drifting control).
        boot_residuals = _moving_block_bootstrap(base_residuals, block_size)
        y_treatment_boot = y_control + boot_residuals
        y_with_lift = apply_lift(y_treatment_boot, delta, start_treatment, end_treatment)
        residuals = compute_residuals(y_with_lift, y_control)
        treatment_residuals = residuals[start_treatment:]

        observed_stat = stat_func(treatment_residuals)

        # Permutation test
        null_stats = []
        for i in range(n_permutations_per_test):
            if inference_type == "block":
                # Block-based permutation for time series
                permuted_residuals = _block_permutation(residuals, block_size)
            else:
                # IID permutation
                permuted_residuals = np.random.permutation(residuals)

            permuted = permuted_residuals[start_treatment:]
            null_stats.append(stat_func(permuted))

        null_stats = np.array(null_stats)

        # Directional p-value (ISS-4). "greater"/"less" are a PRE-REGISTERED choice
        # for a known effect direction — NOT a cure for a biased control. A control
        # that drifts is caught by the (direction-agnostic) abs_lift_in_zero gate;
        # one-sided simply refuses to call an opposite-sign deviation a detection.
        if alternative == "greater":
            p_value = round(float(np.mean(null_stats >= observed_stat)), 2)
        elif alternative == "less":
            p_value = round(float(np.mean(null_stats <= observed_stat)), 2)
        else:  # two-sided
            p_value = round(float(np.mean(np.abs(null_stats) >= np.abs(observed_stat))), 2)
        p_values.append(p_value)

        if p_value < significance_level:
            rejected_tests += 1

    power = round(rejected_tests / n_power_simulations, 2)

    # Calculate confidence interval for power estimate
    power_se = np.sqrt(power * (1 - power) / n_power_simulations)
    power_ci = (round(max(0, power - 1.95 * power_se), 2), round(min(1, power + 1.95 * power_se), 2))

    y_with_lift_sample = apply_lift(y_real, delta, start_treatment, end_treatment)

    logger.debug(
        f"Power simulation completed: power={power:.4f}, CI=({power_ci[0]:.4f}, {power_ci[1]:.4f}), mean p-value={np.mean(p_values):.4f}"
    )

    return delta, power, power_ci, y_with_lift_sample, round(float(np.mean(p_values)), 2)


def run_simulation(
    delta,
    y_real,
    y_control,
    period,
    n_permutations_per_test,
    significance_level,
    test_type="sum",
    inference_type="iid",
    size_block=None,
    n_power_simulations=40,
    alternative="two-sided",
):
    """
    Wrapper function to run a single simulation of statistical power.

    Performs a statistical power simulation by comparing real treatment data
    against synthetic control data using permutation testing.

    Args:
        delta (float): Effect size to test for statistical significance.
        y_real (array-like): Real treatment group data.
        y_control (array-like): Control group data for comparison.
        period (int): Number of periods to simulate.
        n_permutations (int): Number of permutations to run for the test.
        significance_level (float): Significance level for the statistical test.
        test_type (str, optional): Type of test to perform. Default is "sum".
        inference_type (str, optional): Type of inference to use. Default is "iid".
        size_block (optional): Block size for inference. Default is None.

    Returns:
        dict: Dictionary containing simulation results including power, p-value, and test statistics.
    """
    logger.debug(
        f"Starting simulation: delta={delta}, period={period}, n_permutations_per_test={n_permutations_per_test}"
    )

    y_real = np.array(y_real).flatten()
    y_control = np.array(y_control).flatten()

    try:
        result = simulate_power(
            y_real=y_real,
            y_control=y_control,
            delta=delta,
            period=period,
            n_permutations_per_test=n_permutations_per_test,
            significance_level=significance_level,
            test_type=test_type,
            inference_type=inference_type,
            block_size=size_block if size_block else "auto",
            n_power_simulations=n_power_simulations,
            alternative=alternative,
        )
        return result
    except Exception as e:
        logger.error(f"Simulation failed for delta={delta}, period={period}: {str(e)}")
        raise


def _init_simulation_worker():
    _limit_blas_threads()


def _run_simulation_task(args):
    """Module-level helper for ProcessPoolExecutor — must be picklable (no lambdas)."""
    (size, period, delta, y_real, y_control,
     n_permutations_per_test, significance_level,
     test_type, inference_type, size_block, n_power_simulations, alternative) = args
    res = run_simulation(
        delta, y_real, y_control, period,
        n_permutations_per_test, significance_level,
        test_type, inference_type, size_block, n_power_simulations, alternative,
    )
    return (size, period, delta, res)


def _select_significant_mde(statistical_power, significance_level, power_threshold=0.8):
    """Pick the MDE: the smallest delta whose statistical power reaches ``power_threshold``
    AND whose p-value is significant (``<= significance_level``). Returns that
    ``(delta, power, ci, p_value)`` row, or ``None`` when no delta is both adequately powered
    and significant — so the MDE only exists when the design would actually detect the effect.
    Used by evaluate_sensitivity for both single-cell and multi-cell sensitivity.
    """
    for delta, power, ci, p_value in statistical_power:
        if (
            power is not None
            and power >= power_threshold
            and p_value is not None
            and p_value <= significance_level
        ):
            return (delta, power, ci, p_value)
    return None


def evaluate_sensitivity(
    results_by_size,
    deltas,
    periods,
    n_permutations_per_test,
    significance_level=0.05,
    test_type="sum",
    inference_type="iid",
    size_block=None,
    progress_bar=None,
    status_text=None,
    n_power_simulations=40,
    alternative="two-sided",
):
    """
    Evaluates sensitivity of results to different treatment periods and deltas using permutations.

    Args:
        results_by_size (dict): Results organized by sample size.
        deltas (list): List of delta values to evaluate.
        periods (list): List of treatment periods to evaluate.
        n_permutations_per_test (int): Number of permutations per test.
        significance_level (float): Significance level.
        test_type (str): Statistical test type ("sum", "mean_diff", "t_test", "median_diff").
        inference_type (str): Type of conformal inference ("iid" or "block").
        size_block (int): Size of blocks for block shuffling (if applicable).
        progress_bar (callable): Progress bar updater function.
        status_text (callable): Status text updater function.
        n_power_simulations (int): Number of power simulations to run.

    Returns:
        tuple: (sensitivity_results, lift_series)
            - sensitivity_results (dict): Sensitivity results by size and period.
            - lift_series (dict): Adjusted series for each delta and period.
    """
    sensitivity_results = {}
    lift_series = {}

    # Pre-process: extract valid (size, y_real, y_control) entries
    valid_sizes = {}
    for size, result in results_by_size.items():
        if isinstance(result, list):
            if not result:
                logger.warning(f"Skipping size {size} - no groups available")
                continue
            actual_result = result[0]
        else:
            actual_result = result

        if (
            "Actual Target Metric (y)" not in actual_result
            or "Predictions" not in actual_result
            or actual_result["Actual Target Metric (y)"] is None
            or actual_result["Predictions"] is None
        ):
            logger.warning(f"Skipping size {size} due to missing or null values")
            continue

        valid_sizes[size] = (
            np.array(actual_result["Actual Target Metric (y)"]).flatten(),
            np.array(actual_result["Predictions"]).flatten(),
        )

    if not valid_sizes:
        logger.warning("No valid sizes to process in evaluate_sensitivity")
        return {}, {}

    # Build flat task list — all (size, period, delta) combos are fully independent
    tasks = [
        (size, period, delta,
         y_real, y_control,
         n_permutations_per_test, significance_level,
         test_type, inference_type, size_block, n_power_simulations, alternative)
        for size, (y_real, y_control) in valid_sizes.items()
        for period in periods
        for delta in deltas
    ]
    total_steps = len(tasks)
    step = 0

    # Run simulations in parallel — run_simulation is pure Python/numpy (GIL-bound),
    # so ProcessPoolExecutor bypasses the GIL across all (size, period, delta) combos.
    collected = {}
    n_workers = min(os.cpu_count() or 4, total_steps)
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers, initializer=_init_simulation_worker) as executor:
        futures = {executor.submit(_run_simulation_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(futures):
            size, period, delta, res = future.result()
            collected[(size, period, delta)] = res
            step += 1
            if progress_bar:
                try:
                    progress_bar.progress(min(step / total_steps, 1.0))
                except Exception as e:
                    logger.debug(f"Progress update failed: {e}")
            if status_text:
                try:
                    status_text.text(
                        f"Evaluating groups: {int((step / total_steps) * 100)}% complete"
                    )
                except Exception as e:
                    logger.debug(f"Status update failed: {e}")

    # Reconstruct original output structure from collected results
    for size, (y_real, y_control) in valid_sizes.items():
        results_by_period = {}

        for period in periods:
            results = [collected[(size, period, delta)] for delta in deltas]

            statistical_power = [
                (round(res[0], 2), res[1], res[2], res[4]) for res in results
            ]  # (delta, power, power_ci, p_value)
            # MDE only exists when the design is BOTH adequately powered (>= 80%) AND
            # significant (p-value <= significance_level). Otherwise all summary scalars
            # stay None — the same nil the UI reads as "doesn't meet the requirements".
            selected_mde = _select_significant_mde(statistical_power, significance_level)
            if selected_mde is not None:
                mde, mde_power, power_ci, mde_p_value = selected_mde
            else:
                mde = mde_power = power_ci = mde_p_value = None

            # Standardize p-value: if < 0.001, set to 0.001
            if mde_p_value is not None and mde_p_value < 0.001:
                mde_p_value = 0.001

            # Format values safely for logging
            p_value_str = f"{mde_p_value:.4f}" if mde_p_value is not None else "None"
            power_str = f"{mde_power:.4f}" if mde_power is not None else "None"

            logger.info(
                f"Period {period} completed for size {size}. MDE found: {mde} with p-value: {p_value_str}, power: {power_str}"
            )

            for delta, _, ci, adjusted_series, p_value in results:
                lift_series[(size, delta, period)] = adjusted_series

            results_by_period[period] = {
                "Statistical Power": statistical_power,
                "MDE": mde,
                "P-Value": mde_p_value,
                "MDE_CI": power_ci,
                "Power": mde_power,
            }

        sensitivity_results[size] = results_by_period

    logger.info("evaluate_sensitivity completed successfully.")
    return sensitivity_results, lift_series

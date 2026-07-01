import numpy as np

from logger_config import get_logger

from .synthetic_control import _fit_sc_counterfactual
from .power import simulate_power, _auto_block_size, _moving_block_bootstrap

logger = get_logger("inference")


def compute_falsification_metrics(
    y_real,
    y_control=None,
    *,
    donors=None,
    holdout_fraction=0.2,
    n_windows=3,
    skip_recent=1,
    min_train_fraction=0.4,
    significance_level=0.1,
    n_power_simulations=100,
    n_permutations_per_test=500,
    alternative="two-sided",
    inference_type="iid",
    block_size="auto",
):
    """
    Placebo-in-time falsification (ISS-1).

    Runs a null (delta=0) check on hold-out window(s) where the SCM weights were NOT fit,
    returning the placebo bias ``abs_lift_in_zero`` and the false-positive rate.
    Conceptually inspired by GeoLift's lookback diagnostic but NOT a reimplementation
    (GeoLift computes ``|detected - injected|`` at the MDE row; here it is the raw % gap
    at delta=0).

    Two modes:
      * sliding-window (when ``donors`` is given): REFIT the SCM on the data BEFORE each
        placebo window, walking backward, and average over ``n_windows``. ``skip_recent``
        omits the most-recent window(s) so the falsification window is DISJOINT from the
        ranking window (breaks the ranking/gate circularity). Windows whose training span
        falls below ``min_train_fraction`` are discarded.
      * single-window (legacy, no ``donors``): evaluate the last hold-out window of the
        supplied ``(y_real, y_control)`` directly.

    Returns:
        dict: {"abs_lift_in_zero": float (% of counterfactual, direction-agnostic),
               "false_positive_rate": float (power@delta=0),
               "n_windows_used": int}
    """
    y_real = np.asarray(y_real, dtype=float).flatten()
    n = len(y_real)
    holdout = max(2, int(holdout_fraction * n))

    def _window_metrics(y_obs_window, y_cf_window, y_obs_full, y_cf_full):
        denom = float(np.mean(y_cf_window))
        abs_lift = abs(float(np.mean(y_obs_window - y_cf_window)) / denom) * 100 if denom != 0 else 0.0
        _, power_at_zero, _, _, _ = simulate_power(
            y_obs_full, y_cf_full, delta=0.0, period=len(y_obs_window),
            n_permutations_per_test=n_permutations_per_test,
            significance_level=significance_level, inference_type=inference_type,
            block_size=block_size, n_power_simulations=n_power_simulations,
            alternative=alternative,
        )
        return abs_lift, power_at_zero

    abs_lifts, fprs = [], []

    if donors is not None:
        donors = np.asarray(donors, dtype=float)
        min_train = max(2, int(min_train_fraction * n))
        for k in range(skip_recent, skip_recent + n_windows):
            window_end = n - k * holdout
            window_start = window_end - holdout
            if window_start < min_train:
                continue
            try:
                fit = _fit_sc_counterfactual(
                    donors[:window_end], y_real[:window_end], split_index=window_start
                )
            except Exception as e:
                logger.debug(f"falsification window k={k} skipped: {e}")
                continue
            cf_full, yo_full = fit["counterfactual"], fit["y_original"]
            abs_lift, fpr = _window_metrics(
                yo_full[window_start:window_end], cf_full[window_start:window_end],
                yo_full[:window_end], cf_full[:window_end],
            )
            abs_lifts.append(abs_lift)
            fprs.append(fpr)

        if not abs_lifts:
            # Short series: no window disjoint from ranking is available -> reuse the
            # most recent (overlap inevitable) and warn.
            logger.warning(
                "falsification: no disjoint window available; reusing recent window (overlap)"
            )
            window_start = max(2, n - holdout)
            try:
                fit = _fit_sc_counterfactual(donors, y_real, split_index=window_start)
                cf_full, yo_full = fit["counterfactual"], fit["y_original"]
                abs_lift, fpr = _window_metrics(
                    yo_full[window_start:], cf_full[window_start:], yo_full, cf_full
                )
                abs_lifts.append(abs_lift)
                fprs.append(fpr)
            except Exception as e:
                logger.debug(f"falsification fallback skipped: {e}")
    else:
        y_control = np.asarray(y_control, dtype=float).flatten()
        abs_lift, fpr = _window_metrics(
            y_real[-holdout:], y_control[-holdout:], y_real, y_control
        )
        abs_lifts.append(abs_lift)
        fprs.append(fpr)

    if not abs_lifts:
        return {"abs_lift_in_zero": float("inf"), "false_positive_rate": 1.0, "n_windows_used": 0}

    return {
        "abs_lift_in_zero": round(float(np.mean(abs_lifts)), 4),
        "false_positive_rate": round(float(np.mean(fprs)), 4),
        "n_windows_used": len(abs_lifts),
    }


def flag_placebo_bias_vs_mde(simulation_results, sensitivity_results):
    """
    Cross-check the placebo bias against the MDE (ISS-1 / §2.4).

    The FPR is a probability (Type-I error) and the MDE is an effect magnitude — not
    comparable. ``abs_lift_in_zero`` IS comparable to the MDE (both are % lift), so per
    size we compare it to the STRICTEST MDE (smallest, i.e. the longest period). Annotates
    each ``simulation_results[size]`` in place with ``abs_lift_vs_mde_ratio``,
    ``placebo_bias_exceeds_mde``, ``MDE_for_bias_check`` and ``MDE_period_for_bias_check``,
    and warns when the bias is >=50% of the MDE (caution) or >=100% (size unreliable).
    """
    if not simulation_results or not sensitivity_results:
        return simulation_results

    for size, sim in simulation_results.items():
        if not isinstance(sim, dict):  # multi-cell stores a list — skip
            continue
        abs_lift = sim.get("abs_lift_in_zero")
        if abs_lift is None or not np.isfinite(abs_lift):
            continue

        periods = sensitivity_results.get(size, {}) or {}
        mdes = [
            (p, pr.get("MDE"))
            for p, pr in periods.items()
            if isinstance(pr, dict) and pr.get("MDE") is not None
        ]
        if not mdes:
            sim["abs_lift_vs_mde_ratio"] = None
            sim["placebo_bias_exceeds_mde"] = None
            sim["MDE_for_bias_check"] = None
            sim["MDE_period_for_bias_check"] = None
            continue

        period_best, mde_best = min(mdes, key=lambda t: t[1])  # strictest (smallest) MDE
        ratio = abs_lift / (mde_best * 100) if mde_best > 0 else float("inf")
        sim["abs_lift_vs_mde_ratio"] = round(float(ratio), 4)
        sim["placebo_bias_exceeds_mde"] = bool(ratio >= 1.0)
        sim["MDE_for_bias_check"] = mde_best
        sim["MDE_period_for_bias_check"] = period_best

        if ratio >= 1.0:
            logger.warning(
                f"size {size}: placebo bias ({abs_lift:.2f}%) >= strictest MDE "
                f"({mde_best * 100:.2f}%) — a 'detected effect' near the MDE could be control drift"
            )
        elif ratio >= 0.5:
            logger.warning(
                f"size {size}: placebo bias ({abs_lift:.2f}%) is >=50% of the MDE "
                f"({mde_best * 100:.2f}%) — interpret with caution"
            )

    return simulation_results


def conformal_att_interval(
    y,
    counterfactual,
    split_index,
    significance_level=0.10,
    block_size="auto",
    n_bootstrap=2000,
    alternative="two-sided",
):
    """
    Block-conformal confidence interval on the aggregate treatment effect (ATT / lift).

    Replaces the synthetic-noise confidence ribbon with a statistically valid interval
    (CWZ-style conformal under the sharp null, serial-dependence aware). Because the SCM
    weights are fit on the PRE-period only (see ``_fit_sc_counterfactual``), subtracting a
    candidate effect ``g`` from the post window does NOT change the fitted weights, so the
    conformal refit-per-g is a no-op here and the interval collapses to ``ATT ± q``, where
    ``q`` is the ``(1 - alpha)`` quantile of a moving-block bootstrap null of the post-window
    mean built from the effect-free PRE residuals (reusing ``_auto_block_size`` /
    ``_moving_block_bootstrap`` — so it respects autocorrelation).

    Args:
        y (array-like): observed treatment series (full).
        counterfactual (array-like): synthetic-control prediction (full).
        split_index (int): first post-treatment index.
        significance_level (float): alpha (CI level = 1 - alpha).
        block_size (int|"auto"): block length for the null (auto → from pre residuals).
        n_bootstrap (int): moving-block bootstrap replicas for the null.
        alternative (str): "two-sided" | "greater" | "less".

    Returns:
        dict: att, att_total, att_ci (tuple|None), lift, lift_ci_lower, lift_ci_upper,
              p_value, block_size, significant; plus "warning" when the pre-period is too
              short for a block-conformal interval (point estimate returned, CI None).
    """
    y = np.asarray(y, dtype=float).flatten()
    counterfactual = np.asarray(counterfactual, dtype=float).flatten()
    gaps = y - counterfactual
    split_index = int(split_index)

    pre = gaps[:split_index]
    post = gaps[split_index:]
    L = len(post)

    att = float(np.mean(post)) if L > 0 else 0.0
    att_total = float(np.sum(post))
    denom = float(np.mean(counterfactual[split_index:])) if L > 0 else 0.0
    lift = round(att / denom * 100, 4) if denom != 0 else 0.0

    bs = (
        _auto_block_size(pre)
        if not isinstance(block_size, (int, np.integer))
        else max(1, int(block_size))
    )

    # Need a pre-period at least as long as the post window to build a length-L null.
    if L < 1 or len(pre) < 2 or len(pre) < L:
        return {
            "att": round(att, 4),
            "att_total": round(att_total, 4),
            "att_ci": None,
            "lift": lift,
            "lift_ci_lower": None,
            "lift_ci_upper": None,
            "p_value": None,
            "block_size": bs,
            "significant": None,
            "warning": "pre-period too short for a block-conformal interval; returning point estimate",
        }

    # Null of the length-L mean from the EFFECT-FREE pre residuals (moving-block bootstrap).
    # Center first so a non-zero pre-period bias (e.g. an ASCM fit with no time intercept) does
    # not shift/inflate the null — matching conformal_pointwise_bands / conformal_window_margin.
    # Pre-period bias is a separate concern, handled by the falsification gate.
    pre_centered = pre - np.mean(pre)
    null_means = np.array(
        [float(np.mean(_moving_block_bootstrap(pre_centered, bs)[:L])) for _ in range(n_bootstrap)]
    )

    if alternative == "greater":
        q = float(np.quantile(null_means, 1 - significance_level))
        att_ci = (att - q, float("inf"))
        p_value = float(np.mean(null_means >= att))
    elif alternative == "less":
        q = float(np.quantile(null_means, 1 - significance_level))
        att_ci = (float("-inf"), att + q)
        p_value = float(np.mean(null_means <= att))
    else:  # two-sided
        q = float(np.quantile(np.abs(null_means), 1 - significance_level))
        att_ci = (att - q, att + q)
        p_value = float(np.mean(np.abs(null_means) >= abs(att)))

    lo, hi = att_ci
    significant = not (lo <= 0 <= hi)
    lift_ci_lower = round(lo / denom * 100, 4) if denom != 0 and np.isfinite(lo) else None
    lift_ci_upper = round(hi / denom * 100, 4) if denom != 0 and np.isfinite(hi) else None

    return {
        "att": round(att, 4),
        "att_total": round(att_total, 4),
        "att_ci": (round(lo, 4) if np.isfinite(lo) else lo, round(hi, 4) if np.isfinite(hi) else hi),
        "lift": lift,
        "lift_ci_lower": lift_ci_lower,
        "lift_ci_upper": lift_ci_upper,
        "p_value": round(p_value, 4),
        "block_size": bs,
        "significant": significant,
    }


def attach_conformal_design_margins(simulation_results, sensitivity_results, significance_level=0.05):
    """
    Attach the block-conformal window margin to each sensitivity_results[size][period] so the
    DESIGN PDFs / calc services use the conformal band width on the projected incremental
    (the same residual noise floor as the evaluation), instead of a Gaussian approximation.

    Effect-free residuals = Actual - Predictions from the selected cell (design history has no
    treatment). Single-cell only (dict); multi-cell structures fall back to the Gaussian band
    on the Rails side.
    """
    if not simulation_results or not sensitivity_results:
        return sensitivity_results

    for size, sim in simulation_results.items():
        if not isinstance(sim, dict):  # multi-cell stores a list — skip
            continue
        y = sim.get("Actual Target Metric (y)")
        cf = sim.get("Predictions")
        periods = sensitivity_results.get(size)
        if y is None or cf is None or not isinstance(periods, dict):
            continue

        y = np.asarray(y, dtype=float).flatten()
        cf = np.asarray(cf, dtype=float).flatten()
        m = min(len(y), len(cf))
        if m < 2:
            continue
        residuals = y[:m] - cf[:m]

        for period, pdata in periods.items():
            if not isinstance(pdata, dict):
                continue
            try:
                pdata["conformal_margin"] = conformal_window_margin(
                    residuals, int(period), significance_level=significance_level
                )
            except Exception as e:
                logger.debug(f"conformal_margin skipped (size={size}, period={period}): {e}")

    return sensitivity_results


def conformal_window_margin(
    residuals,
    period,
    significance_level=0.05,
    block_size="auto",
    n_bootstrap=2000,
):
    """
    Block-conformal half-width for the total effect over a window of `period` steps.

    Returns ``q_cum(L)`` = the (1-alpha) quantile of |sum of L moving-block-bootstrapped
    residuals| — the same residual noise floor used by the evaluation bands. The DESIGN
    pipeline calls this on the selected cell's fit residuals so the projected-incremental
    band uses the conformal width (block/autocorrelation-aware) instead of a Gaussian
    approximation. ``residuals`` is the effect-free fit residual series (design history has
    no treatment, so all residuals are fit residuals).
    """
    r = np.asarray(residuals, dtype=float).flatten()
    n = len(r)
    L = int(period)
    if n < 2 or L < 1:
        return 0.0

    r = r - np.mean(r)
    bs = (
        _auto_block_size(r)
        if not isinstance(block_size, (int, np.integer))
        else max(1, int(block_size))
    )

    if n >= L:
        sums = np.array(
            [float(np.sum(_moving_block_bootstrap(r, bs)[:L])) for _ in range(n_bootstrap)]
        )
    else:
        # window longer than the history: scale the full-length bootstrap sum by L/n
        scale = L / float(n)
        sums = np.array(
            [float(np.sum(_moving_block_bootstrap(r, bs))) * scale for _ in range(n_bootstrap)]
        )

    return round(float(np.quantile(np.abs(sums), 1 - significance_level)), 2)


def conformal_pointwise_bands(
    y,
    counterfactual,
    split_index,
    significance_level=0.05,
    block_size="auto",
    n_bootstrap=2000,
):
    """
    Per-period conformal confidence bands for the evaluation charts (Parte B4), replacing
    the synthetic-noise ribbon. Uses the block-conformal residual null built from the
    effect-free PRE residuals (weights are fit pre-only → the sharp-null refit is a no-op):

      * per-period half-width ``q`` = (1-alpha) quantile of |pre residual| → a constant band
        on the counterfactual (Panel 1) and the point difference (Panel 2);
      * cumulative half-width ``q_cum(k)`` = (1-alpha) quantile of |sum of k block-bootstrapped
        residuals| → a band that grows with the horizon on the cumulative effect (Panel 3).

    Returns POST-period arrays (lists), matching the legacy chart keys:
      lower_bound/upper_bound      — around the counterfactual,
      lower_bound_pd/upper_bound_pd — around the point difference (daily effect),
      lower_bound_ce/upper_bound_ce — around the cumulative effect.
    Bands degenerate to the point series when the pre-period is too short.
    """
    y = np.asarray(y, dtype=float).flatten()
    cf = np.asarray(counterfactual, dtype=float).flatten()
    split_index = int(split_index)

    pre = (y - cf)[:split_index]
    cf_post = cf[split_index:]
    pd_post = (y - cf)[split_index:]
    cum_post = np.cumsum(pd_post)
    L = len(pd_post)

    def _round(arr):
        return [round(float(v), 2) for v in arr]

    if L < 1 or len(pre) < 2:
        return {
            "lower_bound": _round(cf_post), "upper_bound": _round(cf_post),
            "lower_bound_pd": _round(pd_post), "upper_bound_pd": _round(pd_post),
            "lower_bound_ce": _round(cum_post), "upper_bound_ce": _round(cum_post),
        }

    r = pre - np.mean(pre)
    q1 = float(np.quantile(np.abs(r), 1 - significance_level))
    bs = (
        _auto_block_size(r)
        if not isinstance(block_size, (int, np.integer))
        else max(1, int(block_size))
    )

    if len(r) >= L:
        cum_samples = np.array(
            [np.cumsum(_moving_block_bootstrap(r, bs)[:L]) for _ in range(n_bootstrap)]
        )
        q_cum = np.quantile(np.abs(cum_samples), 1 - significance_level, axis=0)
    else:
        # iid approximation when the pre-period is shorter than the post window
        q_cum = q1 * np.sqrt(np.arange(1, L + 1))

    return {
        "lower_bound": _round(cf_post - q1), "upper_bound": _round(cf_post + q1),
        "lower_bound_pd": _round(pd_post - q1), "upper_bound_pd": _round(pd_post + q1),
        "lower_bound_ce": _round(cum_post - q_cum), "upper_bound_ce": _round(cum_post + q_cum),
    }

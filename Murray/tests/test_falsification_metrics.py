import numpy as np
import pytest

from Murray.main import (
    scaled_l2_imbalance,
    compute_falsification_metrics,
    flag_placebo_bias_vs_mde,
)


def _donors_and_y(drift=None, n=120, holdout=24, seed=0):
    """4 donors; y = their mean (a clean control the simplex can match exactly), with an
    optional +30% drift confined to a chosen placebo window."""
    rng = np.random.default_rng(seed)
    D = np.column_stack([rng.normal(100, 5, n) for _ in range(4)])
    y = D.mean(axis=1).copy()
    if drift == "recent":  # only the most-recent window (the ranking window)
        y[n - holdout:] *= 1.30
    elif drift == "second":  # the first NON-skipped window
        y[n - 2 * holdout:n - holdout] *= 1.30
    return D, y


def test_scaled_l2_perfect_fit_is_zero():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    donors = np.column_stack([np.zeros(4), np.zeros(4)])  # naive mean = 0
    assert scaled_l2_imbalance(y, y_synth=y, donors=donors) == pytest.approx(0.0)


def test_scaled_l2_naive_fit_is_one():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    donors = np.column_stack([np.zeros(4), np.zeros(4)])  # naive mean = 0
    naive = donors.mean(axis=1)
    assert scaled_l2_imbalance(y, y_synth=naive, donors=donors) == pytest.approx(1.0)


def test_scaled_l2_better_than_naive_is_below_one():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    donors = np.column_stack([np.zeros(4), np.zeros(4)])
    y_synth = y * 0.9  # close to y, far better than the zero naive mean
    assert 0.0 < scaled_l2_imbalance(y, y_synth, donors) < 1.0


# ---- ISS-1: sliding-window falsification ----

def test_falsification_returns_expected_keys():
    D, y = _donors_and_y()
    m = compute_falsification_metrics(
        y_real=y, donors=D, n_windows=2, skip_recent=1,
        n_power_simulations=20, n_permutations_per_test=100,
    )
    assert set(m) >= {"abs_lift_in_zero", "false_positive_rate", "n_windows_used"}
    assert m["n_windows_used"] >= 1


def test_falsification_skips_recent_ranking_window():
    """Drift confined to the most-recent window (the ranking window) is NOT counted
    when skip_recent=1; the same drift placed one window earlier IS caught."""
    D_recent, y_recent = _donors_and_y(drift="recent")
    D_second, y_second = _donors_and_y(drift="second")

    m_recent = compute_falsification_metrics(
        y_real=y_recent, donors=D_recent, n_windows=2, skip_recent=1,
        n_power_simulations=20, n_permutations_per_test=100,
    )
    m_second = compute_falsification_metrics(
        y_real=y_second, donors=D_second, n_windows=2, skip_recent=1,
        n_power_simulations=20, n_permutations_per_test=100,
    )

    assert m_recent["abs_lift_in_zero"] < 5.0, (
        f"skipped ranking-window drift must not inflate abs_lift, got {m_recent['abs_lift_in_zero']}"
    )
    assert m_second["abs_lift_in_zero"] > m_recent["abs_lift_in_zero"] + 5.0, (
        "drift inside an evaluated window must raise abs_lift_in_zero"
    )


def test_falsification_clean_control_single_window_mode():
    """Legacy single-window mode (no donors): a clean control has low placebo bias."""
    rng = np.random.default_rng(7)
    y_control = rng.normal(100, 2, 100)
    y_real = y_control + rng.normal(0, 0.5, 100)
    m = compute_falsification_metrics(
        y_real=y_real, y_control=y_control, holdout_fraction=0.2,
        n_power_simulations=20, n_permutations_per_test=100,
    )
    assert m["abs_lift_in_zero"] < 5.0


# ---- ISS-1: abs_lift_in_zero vs MDE cross-check ----

def test_flag_placebo_bias_vs_mde_flags_when_bias_exceeds():
    sim = {5: {"abs_lift_in_zero": 6.0}}
    sens = {5: {28: {"MDE": 0.05}, 14: {"MDE": 0.10}}}  # strictest MDE = 5%
    flag_placebo_bias_vs_mde(sim, sens)
    assert sim[5]["abs_lift_vs_mde_ratio"] == pytest.approx(6.0 / 5.0)
    assert sim[5]["placebo_bias_exceeds_mde"] is True
    assert sim[5]["MDE_for_bias_check"] == 0.05
    assert sim[5]["MDE_period_for_bias_check"] == 28


def test_flag_placebo_bias_vs_mde_no_flag_when_small():
    sim = {5: {"abs_lift_in_zero": 2.0}}
    sens = {5: {28: {"MDE": 0.10}}}  # 10%
    flag_placebo_bias_vs_mde(sim, sens)
    assert sim[5]["placebo_bias_exceeds_mde"] is False


def test_flag_placebo_bias_vs_mde_handles_missing_mde():
    sim = {5: {"abs_lift_in_zero": 2.0}}
    sens = {5: {28: {"MDE": None}}}
    flag_placebo_bias_vs_mde(sim, sens)
    assert sim[5]["abs_lift_vs_mde_ratio"] is None

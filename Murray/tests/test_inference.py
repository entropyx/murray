import numpy as np
import pytest

from Murray.main import (
    _auto_block_size,
    _has_serial_dependence,
    _moving_block_bootstrap,
    _resolve_inference_type,
    simulate_power,
)


def _ar1(n, rho, seed=0):
    """Generate an AR(1) series with autocorrelation rho."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = rho * x[t - 1] + eps[t]
    return x


def test_auto_block_size_white_noise_is_small():
    """White noise has no serial dependence -> block size ~ floor n^(1/3)."""
    rng = np.random.default_rng(1)
    x = rng.standard_normal(200)
    b = _auto_block_size(x)
    floor = int(round(200 ** (1 / 3)))  # ~6
    assert 1 <= b <= floor + 2, f"white-noise block should be near the n^(1/3) floor, got {b}"


def test_auto_block_size_grows_with_autocorrelation():
    """Strong AR(1) (rho=0.9) has a long correlation length -> larger block than white noise."""
    n = 200
    white = _auto_block_size(np.random.default_rng(2).standard_normal(n))
    ar = _auto_block_size(_ar1(n, rho=0.9, seed=3))
    assert ar > white, f"AR(1) block ({ar}) should exceed white-noise block ({white})"
    assert ar >= 7, f"AR(1) 0.9 correlation length should reach the weekly lag, got {ar}"


def test_auto_block_size_is_bounded_and_safe():
    """A constant (degenerate) series must not crash and stays within [1, max_fraction*n]."""
    n = 100
    b = _auto_block_size(np.ones(n), max_fraction=0.25)
    assert 1 <= b <= int(0.25 * n), f"block must stay bounded, got {b}"


def test_auto_block_size_short_series_does_not_exceed_length():
    b = _auto_block_size(np.array([1.0, 2.0, 3.0, 4.0]))
    assert 1 <= b <= 4


# ---- ISS-2: serial-dependence detection + auto scheme resolution ----

def test_has_serial_dependence_white_noise_is_false():
    x = np.random.default_rng(10).standard_normal(200)
    assert _has_serial_dependence(x) is False


def test_has_serial_dependence_ar1_is_true():
    x = _ar1(200, rho=0.9, seed=11)
    assert _has_serial_dependence(x) is True


def test_resolve_inference_type_auto_picks_block_on_autocorrelated():
    x = _ar1(200, rho=0.9, seed=12)
    assert _resolve_inference_type("auto", x) == "block"


def test_resolve_inference_type_auto_picks_iid_on_white_noise():
    x = np.random.default_rng(13).standard_normal(200)
    assert _resolve_inference_type("auto", x) == "iid"


def test_resolve_inference_type_passes_through_explicit():
    x = _ar1(100, rho=0.9, seed=14)
    assert _resolve_inference_type("iid", x) == "iid"
    assert _resolve_inference_type("block", x) == "block"


# ---- ISS-8: moving-block bootstrap replaces the 5%-of-std noise ----

def test_moving_block_bootstrap_preserves_length():
    np.random.seed(0)
    x = np.arange(100, dtype=float)
    b = _moving_block_bootstrap(x, block_size=10)
    assert len(b) == len(x)


def test_moving_block_bootstrap_preserves_autocorrelation():
    """Moving-block resampling keeps within-block (short-range) autocorrelation,
    unlike an iid shuffle which destroys it."""
    np.random.seed(1)
    x = _ar1(300, rho=0.9, seed=20)

    def lag1(s):
        s = s - s.mean()
        return float(np.dot(s[:-1], s[1:]) / np.dot(s, s))

    boots = [lag1(_moving_block_bootstrap(x, block_size=_auto_block_size(x))) for _ in range(20)]
    shuffles = [lag1(np.random.permutation(x)) for _ in range(20)]
    assert np.mean(boots) > 0.3, f"block bootstrap should retain autocorr, got {np.mean(boots):.3f}"
    assert np.mean(boots) > np.mean(shuffles) + 0.2


def test_moving_block_bootstrap_resamples_with_replacement():
    """Output values come from the input pool; ordering is not the identity."""
    np.random.seed(2)
    x = np.arange(50, dtype=float)
    b = _moving_block_bootstrap(x, block_size=5)
    assert set(np.unique(b)).issubset(set(x.tolist()))
    assert not np.array_equal(b, x)


def test_simulate_power_drifting_control_fpr_is_calibrated():
    """A control that drifts up in the recent window must NOT yield power@delta=0 ~ 1.0.
    With the moving-block bootstrap of residuals, FPR collapses toward alpha (the old
    5%-noise loop gave ~1.0 here). Positional drift is left to abs_lift_in_zero."""
    np.random.seed(3)
    n, period = 120, 20
    base = np.random.default_rng(30).normal(100, 2, n)
    y_control = base.copy()
    y_real = base.copy()
    y_real[-period:] = y_real[-period:] * 1.30  # +30% positional drift in the window

    _, power_at_zero, _, _, _ = simulate_power(
        y_real=y_real,
        y_control=y_control,
        delta=0.0,
        period=period,
        n_permutations_per_test=200,
        significance_level=0.1,
        n_power_simulations=40,
    )
    assert power_at_zero <= 0.3, f"FPR should be calibrated near alpha, got power@0={power_at_zero}"


# ---- ISS-4: one-sided alternative ----

def _clean_control(n=120):
    base = np.random.default_rng(40).normal(100, 2, n)
    return base.copy(), base.copy()  # y_real == y_control (clean, no drift)


def test_simulate_power_greater_detects_positive_lift():
    np.random.seed(4)
    y_real, y_control = _clean_control()
    _, power, _, _, _ = simulate_power(
        y_real, y_control, delta=0.3, period=20,
        n_permutations_per_test=200, significance_level=0.1,
        alternative="greater", n_power_simulations=20,
    )
    assert power >= 0.7, f"greater should detect a positive lift, got {power}"


def test_simulate_power_greater_ignores_negative_lift():
    np.random.seed(5)
    y_real, y_control = _clean_control()
    _, power, _, _, _ = simulate_power(
        y_real, y_control, delta=-0.3, period=20,
        n_permutations_per_test=200, significance_level=0.1,
        alternative="greater", n_power_simulations=20,
    )
    assert power <= 0.3, f"greater must ignore a negative-direction deviation, got {power}"


def test_simulate_power_less_detects_negative_lift():
    np.random.seed(6)
    y_real, y_control = _clean_control()
    _, power, _, _, _ = simulate_power(
        y_real, y_control, delta=-0.3, period=20,
        n_permutations_per_test=200, significance_level=0.1,
        alternative="less", n_power_simulations=20,
    )
    assert power >= 0.7, f"less should detect a negative lift, got {power}"


def test_simulate_power_block_with_auto_block_size():
    """block scheme + block_size='auto' must resolve the block length internally, not crash."""
    rng = np.random.default_rng(15)
    y_real = rng.random(100) * 100
    y_control = y_real * 0.95
    delta, power, power_ci, y_lifted, p_value = simulate_power(
        y_real=y_real,
        y_control=y_control,
        delta=0.1,
        period=20,
        n_permutations_per_test=50,
        significance_level=0.05,
        inference_type="block",
        block_size="auto",
        n_power_simulations=5,
    )
    assert isinstance(power, float)
    assert 0 <= p_value <= 1
    assert len(y_lifted) == len(y_real)

import numpy as np
import pytest

from Murray.main import (
    conformal_att_interval,
    conformal_pointwise_bands,
    conformal_window_margin,
    _auto_block_size,
)


def _ar1(n, rho, seed):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = rho * x[t - 1] + eps[t]
    return x


def test_conformal_clean_control_ci_contains_zero():
    rng = np.random.default_rng(0)
    n = 120
    counterfactual = 100 + rng.normal(0, 1, n)
    y = counterfactual + rng.normal(0, 2, n)  # gaps ~ N(0,2), NO post effect
    np.random.seed(0)

    r = conformal_att_interval(y, counterfactual, split_index=90, n_bootstrap=500)

    lo, hi = r["att_ci"]
    assert lo <= 0 <= hi, f"clean control CI should bracket 0, got {r['att_ci']}"
    assert r["significant"] is False


def test_conformal_centers_biased_pre_residuals():
    """The null is built from EFFECT-FREE pre residuals, so a constant pre-period bias must be
    centered out and NOT leak into the CI half-width (matching conformal_pointwise_bands /
    conformal_window_margin, which both center). Without centering, a biased fit inflates the
    interval — a real risk for the ASCM engine, which has no time intercept to absorb the bias.
    """
    n = 120
    counterfactual = np.full(n, 100.0)
    y = counterfactual + 5.0  # constant +5 gap: pure pre-period bias, zero noise

    r = conformal_att_interval(y, counterfactual, split_index=90, n_bootstrap=200)

    lo, hi = r["att_ci"]
    # Centered residuals have zero spread, so the half-width collapses to ~0; the bias does
    # not widen the interval. (Pre-bias is a separate concern, caught by the falsification gate.)
    assert hi - lo < 1e-6, f"pre-period bias leaked into the CI half-width: {r['att_ci']}"


def test_conformal_strong_effect_ci_excludes_zero():
    rng = np.random.default_rng(1)
    n = 120
    counterfactual = 100 + rng.normal(0, 1, n)
    y = counterfactual + rng.normal(0, 1, n)
    y[90:] += 20.0  # +20 on a ~100 counterfactual -> ~20% lift
    np.random.seed(1)

    r = conformal_att_interval(y, counterfactual, split_index=90, n_bootstrap=500)

    assert r["att_ci"][0] > 0, f"strong effect CI should be above 0, got {r['att_ci']}"
    assert r["significant"] is True
    assert 15.0 < r["lift"] < 25.0, f"lift should be ~20%, got {r['lift']}"


def test_conformal_ci_widens_with_noise():
    def width(noise_sd, seed):
        rng = np.random.default_rng(seed)
        n = 120
        cf = 100 + rng.normal(0, 1, n)
        y = cf + rng.normal(0, noise_sd, n)
        y[90:] += 10.0
        np.random.seed(seed)
        r = conformal_att_interval(y, cf, split_index=90, n_bootstrap=500)
        return r["att_ci"][1] - r["att_ci"][0]

    assert width(0.5, 5) < width(4.0, 5)


def test_conformal_block_size_auto_grows_with_autocorrelation():
    def block(make_gaps, seed):
        n = 120
        cf = np.full(n, 100.0)
        y = cf + make_gaps(n, seed)
        np.random.seed(seed)
        r = conformal_att_interval(y, cf, split_index=90, n_bootstrap=100)
        return r["block_size"]

    b_white = block(lambda n, s: np.random.default_rng(s).normal(0, 1, n), 7)
    b_ar = block(lambda n, s: _ar1(n, 0.9, s), 7)
    assert b_white >= 1
    assert b_ar > b_white, f"AR(1) block ({b_ar}) should exceed white-noise block ({b_white})"


def test_conformal_ci_nominal_coverage():
    """The interval must actually cover the true effect at ~the nominal rate (validity,
    not just plausibility). Simulate many datasets with AR(1) residuals and a known
    constant effect; the fraction of CIs that contain the true ATT should sit near 1-alpha."""
    K = 200
    n, split = 120, 90
    g_true = 5.0
    alpha = 0.10
    covered = 0

    for trial in range(K):
        resid = _ar1(n, rho=0.4, seed=trial)        # shared AR(1) over pre+post
        counterfactual = np.full(n, 100.0)
        y = counterfactual + resid
        y[split:] += g_true                          # known per-period effect
        np.random.seed(1000 + trial)                 # seed the bootstrap
        r = conformal_att_interval(
            y, counterfactual, split_index=split,
            significance_level=alpha, n_bootstrap=300,
        )
        lo, hi = r["att_ci"]
        if lo <= g_true <= hi:
            covered += 1

    coverage = covered / K
    assert 0.82 <= coverage <= 0.98, f"empirical coverage {coverage:.3f} far from nominal 0.90"


def test_pointwise_bands_lengths_and_keys():
    rng = np.random.default_rng(0)
    n, split = 100, 70
    cf = 100 + rng.normal(0, 2, n)
    y = cf + rng.normal(0, 1, n)
    np.random.seed(0)
    b = conformal_pointwise_bands(y, cf, split_index=split, significance_level=0.1, n_bootstrap=300)
    L = n - split
    for k in ("lower_bound", "upper_bound", "lower_bound_pd", "upper_bound_pd",
              "lower_bound_ce", "upper_bound_ce"):
        assert k in b and len(b[k]) == L, f"{k} must be length {L}"


def test_pointwise_bands_pd_excludes_zero_under_effect():
    rng = np.random.default_rng(1)
    n, split = 100, 70
    cf = 100 + rng.normal(0, 2, n)
    y = cf + rng.normal(0, 1, n)
    y[split:] += 20.0  # clear effect
    np.random.seed(1)
    b = conformal_pointwise_bands(y, cf, split_index=split, significance_level=0.1, n_bootstrap=300)
    assert all(lo > 0 for lo in b["lower_bound_pd"]), "point-difference band should exclude 0 under a clear effect"


def test_pointwise_bands_clean_control_pd_contains_zero():
    rng = np.random.default_rng(2)
    n, split = 100, 70
    cf = 100 + rng.normal(0, 2, n)
    y = cf + rng.normal(0, 1, n)  # no effect
    np.random.seed(2)
    b = conformal_pointwise_bands(y, cf, split_index=split, significance_level=0.1, n_bootstrap=300)
    contains_zero = [lo <= 0 <= hi for lo, hi in zip(b["lower_bound_pd"], b["upper_bound_pd"])]
    assert sum(contains_zero) >= 0.7 * len(contains_zero), "most daily bands should bracket 0 for a clean control"


def test_pointwise_bands_cumulative_widens():
    rng = np.random.default_rng(3)
    n, split = 120, 60
    cf = 100 + rng.normal(0, 2, n)
    y = cf + rng.normal(0, 1, n)
    np.random.seed(3)
    b = conformal_pointwise_bands(y, cf, split_index=split, significance_level=0.1, n_bootstrap=300)
    half = [(hi - lo) / 2 for lo, hi in zip(b["lower_bound_ce"], b["upper_bound_ce"])]
    assert half[-1] > half[0], "cumulative band half-width should grow with horizon"


def test_pointwise_bands_short_pre_degenerates():
    rng = np.random.default_rng(4)
    n = 40
    cf = 100 + rng.normal(0, 1, n)
    y = cf + rng.normal(0, 1, n)
    np.random.seed(4)
    b = conformal_pointwise_bands(y, cf, split_index=1, n_bootstrap=100)  # pre too short
    # degenerate: bands equal the point series (point difference band collapses to the gap)
    pd_post = (y - cf)[1:]
    assert b["lower_bound_pd"] == [round(float(v), 2) for v in pd_post]


def test_conformal_window_margin_positive_and_grows_with_period():
    rng = np.random.default_rng(0)
    residuals = rng.normal(0, 5, 200)
    np.random.seed(0)
    m10 = conformal_window_margin(residuals, period=10, significance_level=0.1, n_bootstrap=400)
    np.random.seed(0)
    m40 = conformal_window_margin(residuals, period=40, significance_level=0.1, n_bootstrap=400)
    assert m10 > 0
    assert m40 > m10, "the window margin should grow with the period length"


def test_conformal_window_margin_zero_for_empty_or_degenerate():
    assert conformal_window_margin([], period=10) == 0.0
    assert conformal_window_margin([5.0], period=10) == 0.0


def _pysyncon_significance(seed, effect):
    """Run pysyncon's ConformalInference (the reference CWZ implementation) and OUR
    block-conformal on the SAME (treated, synthetic) series; return both significance
    decisions. Tiny problem + capped iterations so it stays ~seconds."""
    import warnings

    warnings.filterwarnings("ignore")
    import pandas as pd
    from pysyncon import Synth
    from pysyncon.inference import ConformalInference

    rng = np.random.default_rng(seed)
    n, split = 24, 20
    t = list(range(n))
    ctrl = {f"c{i}": 100 + np.cumsum(rng.normal(0, 1, n)) + rng.normal(0, 1, n) for i in range(3)}
    Z0 = pd.DataFrame(ctrl, index=t)
    treated = Z0.mean(axis=1).values + rng.normal(0, 1, n)
    treated[split:] += effect
    Z1 = pd.Series(treated, index=t, name="treated")
    pre, post = t[:split], t[split : split + 2]

    fit_args = {"X0": Z0.loc[pre], "X1": Z1.loc[pre], "optim_options": {"maxiter": 50}}
    scm = Synth()
    scm.fit(Z0=Z0.loc[pre], Z1=Z1.loc[pre], **fit_args)
    ci = ConformalInference().confidence_intervals(
        alpha=0.1, scm=scm, Z0=Z0, Z1=Z1, pre_periods=pre, post_periods=post,
        verbose=False, max_iter=12, tol=0.4, scm_fit_args=fit_args,
    )
    pysyncon_sig = float(((ci["lower_ci"] > 0) | (ci["upper_ci"] < 0)).mean()) >= 0.5

    synthetic = scm._synthetic(Z0=Z0).values
    np.random.seed(seed)
    ours = conformal_att_interval(
        Z1.values, synthetic, split_index=split, significance_level=0.1, n_bootstrap=1000
    )
    return pysyncon_sig, ours["significant"]


def test_conformal_agrees_with_pysyncon_oracle():
    """Cross-check against pysyncon's ConformalInference (reference CWZ). Our refit-free
    block-conformal must reach the SAME significance verdict on the same data. Methods
    differ by design (aggregate vs pointwise refit-per-g), so we compare the decision,
    not exact bounds."""
    pytest.importorskip("pysyncon")

    pysyncon_sig, ours_sig = _pysyncon_significance(seed=7, effect=8.0)
    assert pysyncon_sig is True and ours_sig is True, "both should detect the strong effect"

    pysyncon_null, ours_null = _pysyncon_significance(seed=11, effect=0.0)
    assert pysyncon_null is False and ours_null is False, "neither should flag a null effect"


def test_conformal_short_pre_returns_point_with_warning():
    rng = np.random.default_rng(3)
    n = 40
    cf = 100 + rng.normal(0, 1, n)
    y = cf + rng.normal(0, 1, n)
    np.random.seed(3)

    r = conformal_att_interval(y, cf, split_index=2, n_bootstrap=100)

    assert r["att_ci"] is None
    assert "warning" in r
    assert r["att"] is not None  # point estimate still returned

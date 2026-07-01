import numpy as np

from Murray.main import (
    _fit_sc_counterfactual,
    _fit_sc_auto,
    _select_lambda_ascm,
    _ASCM_LAMBDAS,
    select_engine_isolated,
    smape,
)


def _holdout_smape(fit):
    s = fit["split_index"]
    return smape(fit["y_original"][s:], fit["counterfactual"][s:])


def test_select_lambda_ascm_returns_candidate():
    rng = np.random.default_rng(0)
    X = rng.random((80, 4)) * 10
    y = X @ np.array([0.3, 0.3, 0.2, 0.2]) + rng.normal(0, 0.5, 80)
    lam = _select_lambda_ascm(X, y, split_index=64)
    assert lam in _ASCM_LAMBDAS


def test_fit_sc_auto_returns_engine_metadata():
    rng = np.random.default_rng(1)
    X = rng.random((80, 3)) * 10
    y = X @ np.array([0.4, 0.3, 0.3]) + rng.normal(0, 0.5, 80)
    fit = _fit_sc_auto(X, y, split_index=64)
    assert fit["engine"] in ("ascm", "ridge_time")
    assert "ridge_alpha" in fit
    assert "counterfactual" in fit and "split_index" in fit


def test_fit_sc_auto_never_worse_than_ridge():
    """Auto picks the better of ridge-on-time / ASCM(lambda*) by holdout SMAPE, so it can
    never be worse than the current default engine."""
    rng = np.random.default_rng(2)
    X = rng.random((90, 4)) * 10
    y = X @ np.array([0.25, 0.25, 0.25, 0.25]) + rng.normal(0, 0.8, 90)
    split = 72

    ridge = _fit_sc_counterfactual(X, y, split, augmentation=None)
    auto = _fit_sc_auto(X, y, split)
    assert _holdout_smape(auto) <= _holdout_smape(ridge) + 1e-6


def test_fit_sc_auto_picks_ascm_outside_convex_hull():
    """A treated unit above the donor hull is fit better by ASCM → with no anti-noise margin
    the auto-selector picks it. (The default margin requires a larger edge; see
    test_fit_sc_auto_min_improvement_blocks_marginal_flip.)"""
    rng = np.random.default_rng(3)
    X = rng.random((80, 3)) * 10.0
    y = X.max(axis=1) * 1.5 + 5.0  # above every donor
    fit = _fit_sc_auto(X, y, split_index=64, min_improvement=0.0)
    assert fit["engine"] == "ascm"


def test_fit_sc_counterfactual_auto_dispatch():
    rng = np.random.default_rng(4)
    X = rng.random((70, 3)) * 10
    y = X @ np.array([0.3, 0.4, 0.3]) + rng.normal(0, 0.5, 70)
    fit = _fit_sc_counterfactual(X, y, split_index=56, augmentation="auto")
    assert "engine" in fit
    assert len(fit["counterfactual"]) == len(y)


def test_select_engine_isolated_returns_decision():
    """The isolated selector returns the same kind of decision as _fit_sc_auto, as a
    (augmentation, ridge_alpha, engine_label) tuple usable by SyntheticControl."""
    rng = np.random.default_rng(5)
    X = rng.random((80, 3)) * 10
    y = X @ np.array([0.4, 0.3, 0.3]) + rng.normal(0, 0.5, 80)
    aug, alpha, label = select_engine_isolated(X, y, split_index=64)
    assert aug in (None, "ascm")
    assert isinstance(alpha, float) and alpha > 0
    assert label in ("ascm", "ridge_time")


def test_select_engine_isolated_falls_back_on_failure():
    """If the isolated worker cannot return in time (here: timeout=0), the selector must NOT
    raise — it falls back to ridge-on-time so the evaluation still completes. This mirrors the
    real guard against a native SIGSEGV killing the child process."""
    rng = np.random.default_rng(6)
    X = rng.random((80, 3)) * 10
    y = X @ np.array([0.4, 0.3, 0.3]) + rng.normal(0, 0.5, 80)
    aug, alpha, label = select_engine_isolated(X, y, split_index=64, timeout=0)
    assert aug is None
    assert alpha == 1.0
    assert label == "ridge_time(fallback)"


def test_fit_sc_auto_min_improvement_blocks_marginal_flip():
    """ASCM must beat ridge by at least ``min_improvement`` (relative holdout SMAPE) to be
    chosen, so engine flips driven by single-holdout noise are suppressed. A strict margin
    keeps ridge even where ASCM is nominally better; a zero margin recovers the old behavior."""
    rng = np.random.default_rng(3)
    X = rng.random((80, 3)) * 10.0
    y = X.max(axis=1) * 1.5 + 5.0  # ASCM fits this far better than ridge-on-time

    strict = _fit_sc_auto(X, y, split_index=64, min_improvement=0.99)
    assert strict["engine"] == "ridge_time"

    lenient = _fit_sc_auto(X, y, split_index=64, min_improvement=0.0)
    assert lenient["engine"] == "ascm"

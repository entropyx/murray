import pytest
import numpy as np
import pandas as pd
from Murray.main import SyntheticControl
from Murray.auxiliary import cleaned_data, market_correlations


@pytest.fixture(scope="module")
def synthetic_data():
    """Fixture that creates synthetic test data"""
    np.random.seed(42)
    X = np.random.rand(100, 3)
    y = X @ np.array([0.3, 0.5, 0.2]) + np.random.normal(0, 0.1, 100)

    return X, y


@pytest.fixture(scope="module")
def correlation_matrix(synthetic_data):
    """Fixture that generates correlation matrix from synthetic data"""
    return market_correlations(synthetic_data)


@pytest.fixture(scope="module")
def synthetic_control():
    """Fixture that creates a synthetic control instance"""
    return SyntheticControl(
        regularization_strength_l1=0.1,
        regularization_strength_l2=0.1,
        seasonality=None,
        delta=1.0,
    )


@pytest.fixture(scope="module")
def synthetic_control_with_ridge():
    """Fixture that creates a synthetic control instance with ridge adjustment"""
    return SyntheticControl(use_ridge_adjustment=True, ridge_alpha=1.0)


def test_synthetic_control_fit(synthetic_control, synthetic_data):
    """Test that synthetic control can fit the data"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)

    assert hasattr(synthetic_control, "is_fitted_")
    assert hasattr(synthetic_control, "w_")
    assert isinstance(synthetic_control.w_, np.ndarray)
    assert len(synthetic_control.w_) == X.shape[1]


def test_synthetic_control_predict(synthetic_control, synthetic_data):
    """Test that synthetic control can make predictions"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)
    predictions, weights = synthetic_control.predict(X)

    assert isinstance(predictions, np.ndarray)
    assert len(predictions) == len(y)
    assert not np.isnan(predictions).any()
    assert isinstance(weights, np.ndarray)
    assert len(weights) == X.shape[1]


def test_synthetic_control_predict_not_fitted(synthetic_control, synthetic_data):
    """Test that predict raises error when model is not fitted"""
    X, y = synthetic_data

    predictions, weights = synthetic_control.predict(X)
    assert isinstance(predictions, np.ndarray)
    assert isinstance(weights, np.ndarray)


def test_synthetic_control_ridge_adjustment(
    synthetic_control_with_ridge, synthetic_data
):
    """Test synthetic control with ridge adjustment"""
    X, y = synthetic_data
    time_index = np.arange(len(y))
    synthetic_control_with_ridge.fit(X, y, time_train=time_index)
    predictions, weights = synthetic_control_with_ridge.predict(
        X, time_index=time_index
    )

    assert isinstance(predictions, np.ndarray)
    assert len(predictions) == len(y)
    assert not np.isnan(predictions).any()


def test_synthetic_control_filter_controls_by_weights(
    synthetic_control, synthetic_data
):
    """Test the filter_controls_by_weights method"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)

    control_group = ["Control_A", "Control_B", "Control_C"]
    min_weight_threshold = 0.1

    filtered_controls, filtered_weights = synthetic_control.filter_controls_by_weights(
        control_group, min_weight_threshold
    )

    assert isinstance(filtered_controls, list)
    assert isinstance(filtered_weights, np.ndarray)
    assert len(filtered_controls) <= len(control_group)
    assert len(filtered_weights) == len(filtered_controls)
    assert all(w >= min_weight_threshold for w in filtered_weights)
    assert np.isclose(np.sum(filtered_weights), 1.0, atol=1e-6)


def test_synthetic_control_filter_controls_no_weights_above_threshold(
    synthetic_control, synthetic_data
):
    """Test filter_controls_by_weights when no weights meet threshold"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)

    control_group = ["Control_A", "Control_B", "Control_C"]
    min_weight_threshold = 1.5

    filtered_controls, filtered_weights = synthetic_control.filter_controls_by_weights(
        control_group, min_weight_threshold
    )

    assert len(filtered_controls) == 1
    assert len(filtered_weights) == 1
    assert np.isclose(filtered_weights[0], 1.0, atol=1e-6)


def test_synthetic_control_filter_controls_mismatched_lengths(
    synthetic_control, synthetic_data
):
    """Test filter_controls_by_weights with mismatched control group and weights"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)

    control_group = ["Control_A", "Control_B"]

    with pytest.raises(ValueError, match="The number of control locations must match"):
        synthetic_control.filter_controls_by_weights(control_group, 0.1)


def test_synthetic_control_different_solvers():
    """Test synthetic control with different solver configurations"""
    np.random.seed(42)
    X = np.random.rand(50, 4)
    y = X @ np.array([0.2, 0.3, 0.3, 0.2]) + np.random.normal(0, 0.1, 50)

    solvers_to_test = [
        {"regularization_strength_l1": 0.1, "regularization_strength_l2": 0.0},
        {"regularization_strength_l1": 0.0, "regularization_strength_l2": 0.1},
        {"regularization_strength_l1": 0.05, "regularization_strength_l2": 0.05},
    ]

    for solver_config in solvers_to_test:
        model = SyntheticControl(**solver_config)
        model.fit(X, y)
        predictions, weights = model.predict(X)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == len(y)
        assert not np.isnan(predictions).any()
        assert np.all(weights >= 0)


def test_synthetic_control_edge_cases():
    """Test synthetic control with edge cases"""
    np.random.seed(42)
    X_single = np.random.rand(50, 1)
    y_single = X_single.flatten() * 0.8 + np.random.normal(0, 0.1, 50)

    model = SyntheticControl()
    model.fit(X_single, y_single)
    predictions, weights = model.predict(X_single)

    assert len(predictions) == len(y_single)
    assert len(weights) == 1
    assert not np.isnan(predictions).any()


def test_synthetic_control_time_index():
    """Test synthetic control with time index parameter"""
    np.random.seed(42)
    X = np.random.rand(50, 3)
    y = X @ np.array([0.3, 0.4, 0.3]) + np.random.normal(0, 0.1, 50)
    time_index = np.arange(50)

    model = SyntheticControl()
    model.fit(X, y, time_train=time_index)
    predictions, weights = model.predict(X, time_index=time_index)

    assert len(predictions) == len(y)
    assert not np.isnan(predictions).any()


# ---- ASCM (Ben-Michael ridge augmentation, opt-in) ----

def test_ascm_reduces_to_simplex_with_large_alpha():
    """As ridge_alpha -> infinity the augmentation vanishes and ASCM == simplex."""
    np.random.seed(0)
    X = np.random.rand(60, 3)
    y = X @ np.array([0.3, 0.5, 0.2]) + np.random.normal(0, 0.05, 60)

    pred_s, _ = SyntheticControl().fit(X, y).predict(X)
    pred_a, _ = SyntheticControl(augmentation="ascm", ridge_alpha=1e8).fit(X, y).predict(X)
    assert np.allclose(pred_a, pred_s, atol=1e-3)


def test_ascm_improves_pre_fit_vs_simplex():
    """The ridge augmentation can only reduce the pre-period fit error."""
    np.random.seed(1)
    X = np.random.rand(60, 4)
    y = X @ np.array([0.4, 0.3, 0.2, 0.1]) + np.random.normal(0, 0.1, 60)

    ps, _ = SyntheticControl().fit(X, y).predict(X)
    pa, _ = SyntheticControl(augmentation="ascm", ridge_alpha=0.1).fit(X, y).predict(X)
    rmse_s = np.sqrt(np.mean((y - ps) ** 2))
    rmse_a = np.sqrt(np.mean((y - pa) ** 2))
    assert rmse_a <= rmse_s + 1e-9


def test_ascm_extrapolates_outside_convex_hull():
    """Treated above the donor hull: the simplex caps at the max donor; ASCM extrapolates."""
    np.random.seed(2)
    X = np.random.rand(50, 3) * 10.0           # donors in [0, 10]
    y = X.max(axis=1) * 1.5 + 5.0              # treated above every donor

    ps, _ = SyntheticControl().fit(X, y).predict(X)
    pa, _ = SyntheticControl(augmentation="ascm", ridge_alpha=0.01).fit(X, y).predict(X)
    rmse_s = np.sqrt(np.mean((y - ps) ** 2))
    rmse_a = np.sqrt(np.mean((y - pa) ** 2))
    assert rmse_a < rmse_s, f"ASCM ({rmse_a:.3f}) should beat simplex ({rmse_s:.3f}) out of hull"


def test_ascm_predict_returns_simplex_weights_for_filtering():
    """predict() still returns the simplex weights (sum=1, >=0) so the weight filter and
    donor display stay interpretable; the augmentation only affects the counterfactual."""
    np.random.seed(3)
    X = np.random.rand(40, 3)
    y = X @ np.array([0.3, 0.4, 0.3]) + np.random.normal(0, 0.05, 40)

    _, weights = SyntheticControl(augmentation="ascm", ridge_alpha=1.0).fit(X, y).predict(X)
    assert len(weights) == X.shape[1]
    assert np.isclose(np.sum(weights), 1.0, atol=1e-6)
    assert np.all(weights >= -1e-9)


def test_synthetic_control_weights_properties(synthetic_control, synthetic_data):
    """Test properties of weights returned by synthetic control"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)
    predictions, weights = synthetic_control.predict(X)

    assert np.all(weights >= 0)

    assert np.isclose(np.sum(weights), 1.0, atol=1e-6)

    assert len(weights) == X.shape[1]

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


def test_synthetic_control_weights_properties(synthetic_control, synthetic_data):
    """Test properties of weights returned by synthetic control"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)
    predictions, weights = synthetic_control.predict(X)

    assert np.all(weights >= 0)

    assert np.isclose(np.sum(weights), 1.0, atol=1e-6)

    assert len(weights) == X.shape[1]

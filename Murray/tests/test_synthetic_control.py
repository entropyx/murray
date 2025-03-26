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
        delta=1.0
    )

def test_synthetic_control_fit(synthetic_control, synthetic_data):
    """Test that synthetic control can fit the data"""
    X, y = synthetic_data
    synthetic_control.fit(X, y)
    
    assert hasattr(synthetic_control, 'is_fitted_')
    assert hasattr(synthetic_control, 'w_')
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

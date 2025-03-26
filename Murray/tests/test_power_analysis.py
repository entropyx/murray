import pytest
import numpy as np
import pandas as pd
from Murray.main import apply_lift, calculate_conformity, simulate_power, run_simulation, evaluate_sensitivity

@pytest.fixture
def synthetic_series():
    """Fixture to generate a synthetic time series."""
    np.random.seed(42)
    y = np.random.rand(100) * 100  
    return y


def test_apply_lift(synthetic_series):
    y = synthetic_series.copy()
    y_lifted = apply_lift(y, delta=0.1, start_treatment=50, end_treatment=70)

    assert np.all(y_lifted[:50] == y[:50]), "Values before the treatment should not change"
    assert np.all(y_lifted[70:] == y[70:]), "Values after the treatment should not change"
    assert np.all(y_lifted[50:70] == y[50:70] * 1.1), "The lift should be applied in the treatment period"


def test_calculate_conformity(synthetic_series):
    y_real = synthetic_series.copy()
    y_control = synthetic_series.copy() * 0.9  

    conformity = calculate_conformity(y_real, y_control, start_treatment=50, end_treatment=70)

    expected_conformity = np.mean(y_real[50:70]) - np.mean(y_control[50:70])
    assert np.isclose(conformity, expected_conformity), "The calculated conformity should match the expected value"


def test_simulate_power(synthetic_series):
    y_real = synthetic_series.copy()
    y_control = synthetic_series.copy() * 0.95  

    delta, power, y_lifted = simulate_power(
        y_real=y_real,
        y_control=y_control,
        delta=0.1,
        period=20,
        n_permutations=100,
        significance_level=0.05
    )

    assert isinstance(delta, float), "Delta must be a float"
    assert isinstance(power, float), "Statistical power must be a float"
    assert isinstance(y_lifted, np.ndarray), "The adjusted series must be a NumPy array"
    assert len(y_lifted) == len(y_real), "The adjusted series must have the same length as the original"


def test_run_simulation(synthetic_series):
    y_real = synthetic_series.copy()
    y_control = synthetic_series.copy() * 0.98

    delta, power, y_lifted = run_simulation(
        delta=0.2,
        y_real=y_real,
        y_control=y_control,
        period=20,
        n_permutations=100,
        significance_level=0.05
    )

    assert isinstance(delta, float), "Delta must be a float"
    assert isinstance(power, float), "Statistical power must be a float"
    assert isinstance(y_lifted, np.ndarray), "The adjusted series must be a NumPy array"


def test_evaluate_sensitivity():
    """Test the sensitivity evaluation function"""
    results_by_size = {
        50: {"Actual Target Metric (y)": np.random.rand(100) * 100, "Predictions": np.random.rand(100) * 100}
    }
    deltas = [0.05, 0.1, 0.2]
    periods = [10, 20, 30]
    n_permutations = 50

    sensitivity_results, lift_series = evaluate_sensitivity(
        results_by_size=results_by_size,
        deltas=deltas,
        periods=periods,
        n_permutations=n_permutations,
        significance_level=0.05
    )

    assert isinstance(sensitivity_results, dict), "The result must be a dictionary"
    assert isinstance(lift_series, dict), "The lift series must be a dictionary"
    assert all(isinstance(v, dict) for v in sensitivity_results.values()), "Each value in sensitivity_results must be a dictionary"
    assert all(isinstance(v, np.ndarray) for v in lift_series.values()), "Each value in lift_series must be a NumPy array"

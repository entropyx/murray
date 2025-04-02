import pytest
import numpy as np
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app
from Murray.auxiliary import market_correlations, cleaned_data

@pytest.fixture
def sample_data():
    """Fixture that generates a test DataFrame with synthetic data."""
    np.random.seed(42)
    data = pd.DataFrame({
        "time": np.tile(pd.date_range("2023-01-01", periods=100, freq="D"), 10),
        "location": np.repeat([f"Location_{i}" for i in range(10)], 100),
        "Y": np.random.rand(1000) * 100
    })
    return data


def test_run_geo_analysis(sample_data):
    """Checks that the analysis function runs correctly."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.05,
        deltas_range=(0.05, 0.2, 0.05),
        periods_range=(10, 30, 10),
        excluded_locations=["Location_1"],
        n_permutations=100  
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert "simulation_results" in results, "Missing 'simulation_results' in the results"
    assert "sensitivity_results" in results, "Missing 'sensitivity_results' in the results"
    assert "series_lifts" in results, "Missing 'series_lifts' in the results"

    assert isinstance(results["simulation_results"], dict), "simulation_results must be a dictionary"
    assert isinstance(results["sensitivity_results"], dict), "sensitivity_results must be a dictionary"
    assert isinstance(results["series_lifts"], dict), "series_lifts must be a dictionary"

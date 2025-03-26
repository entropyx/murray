import pytest
import numpy as np
import pandas as pd
from Murray.post_analysis import run_geo_evaluation
from Murray.auxiliary import market_correlations, cleaned_data

@pytest.fixture
def sample_data():
    """Fixture that generates a test DataFrame with fictitious data"""
    np.random.seed(42)
    data = pd.DataFrame({
        "time": np.tile(pd.date_range("2023-01-01", periods=100, freq="D"), 10),
        "location": np.repeat([f"Location_{i}" for i in range(10)], 100),
        "Y": np.random.rand(1000) * 100
    })
    return data


def test_run_geo_evaluation(sample_data):
    """Checks that the geographic evaluation function runs correctly"""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        n_permutations=100,  
        inference_type="iid",
        significance_level=0.05
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    expected_keys = [
        "MAPE", "SMAPE", "predictions", "treatment", "p_value", "power",
        "percenge_lift", "control_group", "observed_stat",
        "null_stats", "weights", "period", "spend", "length_treatment"
    ]
    for key in expected_keys:
        assert key in results, f"Missing the key '{key}' in the results"

    assert isinstance(results["MAPE"], float), "MAPE must be a float"
    assert isinstance(results["p_value"], float), "p_value must be a float"
    assert isinstance(results["power"], float), "Power must be a float"
    assert isinstance(results["control_group"], list), "Control group must be a list"
    assert 0 <= results["power"] <= 1, "Power must be between 0 and 1"
    assert 0 <= results["p_value"] <= 1, "p_value must be between 0 and 1"

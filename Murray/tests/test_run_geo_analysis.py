import pytest
import numpy as np
import pandas as pd
from Murray.main import run_geo_analysis_streamlit_app, transform_results_data
from Murray.auxiliary import market_correlations, cleaned_data


@pytest.fixture
def sample_data():
    """Fixture that generates a test DataFrame with synthetic data."""
    np.random.seed(42)
    data = pd.DataFrame(
        {
            "time": np.tile(pd.date_range("2023-01-01", periods=100, freq="D"), 10),
            "location": np.repeat([f"Location_{i}" for i in range(10)], 100),
            "Y": np.random.rand(1000) * 100,
        }
    )
    return data


@pytest.fixture
def sample_data_with_duplicates():
    """Fixture that generates test data with some duplicates."""
    np.random.seed(42)
    base_data = pd.DataFrame(
        {
            "time": np.tile(pd.date_range("2023-01-01", periods=50, freq="D"), 8),
            "location": np.repeat([f"Location_{i}" for i in range(8)], 50),
            "Y": np.random.rand(400) * 100,
        }
    )

    # Add some duplicates
    duplicate_rows = base_data.sample(n=20, random_state=42)
    duplicate_rows["Y"] = duplicate_rows["Y"] * 1.1  # Slightly different values

    combined_data = pd.concat([base_data, duplicate_rows], ignore_index=True)
    return combined_data


def test_run_geo_analysis(sample_data):
    """Checks that the analysis function runs correctly."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.05,
        deltas_range=(0.05, 0.2, 0.05),
        periods_range=(10, 30, 10),
        excluded_locations=["Location_1"],
        n_permutations_per_test=100,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert (
        "simulation_results" in results
    ), "Missing 'simulation_results' in the results"
    assert (
        "sensitivity_results" in results
    ), "Missing 'sensitivity_results' in the results"
    assert "series_lifts" in results, "Missing 'series_lifts' in the results"

    assert isinstance(
        results["simulation_results"], dict
    ), "simulation_results must be a dictionary"
    assert isinstance(
        results["sensitivity_results"], dict
    ), "sensitivity_results must be a dictionary"
    assert isinstance(
        results["series_lifts"], dict
    ), "series_lifts must be a dictionary"


def test_run_geo_analysis_with_duplicates(sample_data_with_duplicates):
    """Test that the analysis handles duplicates correctly."""
    from Murray.auxiliary import handle_duplicates

    cleaned_data = handle_duplicates(sample_data_with_duplicates)

    results = run_geo_analysis_streamlit_app(
        data=cleaned_data,
        maximum_treatment_percentage=0.40,
        significance_level=0.10,
        deltas_range=(0.05, 0.15, 0.05),
        periods_range=(10, 20, 5),
        excluded_locations=[],
        n_permutations_per_test=50,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert (
        "simulation_results" in results
    ), "Missing 'simulation_results' in the results"
    assert len(results["simulation_results"]) > 0, "Should have simulation results"


def test_run_geo_analysis_no_excluded_locations(sample_data):
    """Test analysis with no excluded locations."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.30,
        significance_level=0.05,
        deltas_range=(0.05, 0.10, 0.05),
        periods_range=(10, 15, 5),
        excluded_locations=[],
        n_permutations_per_test=50,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert (
        len(results["simulation_results"]) > 0
    ), "Should have results with no exclusions"


def test_run_geo_analysis_high_treatment_percentage(sample_data):
    """Test analysis with high treatment percentage."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.80,
        significance_level=0.05,
        deltas_range=(0.05, 0.10, 0.05),
        periods_range=(10, 15, 5),
        excluded_locations=[],
        n_permutations_per_test=50,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert "simulation_results" in results


def test_run_geo_analysis_low_significance_level(sample_data):
    """Test analysis with low significance level."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.01,
        deltas_range=(0.05, 0.10, 0.05),
        periods_range=(10, 15, 5),
        excluded_locations=[],
        n_permutations_per_test=50,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert "sensitivity_results" in results


def test_run_geo_analysis_single_delta_period(sample_data):
    """Test analysis with single delta and period values."""
    results = run_geo_analysis_streamlit_app(
        data=sample_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.05,
        deltas_range=(0.10, 0.11, 0.05),
        periods_range=(15, 16, 5),
        excluded_locations=[],
        n_permutations_per_test=30,
        n_power_simulations=10,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert (
        len(results["series_lifts"]) > 0
    ), "Should have series lifts for single values"


def test_transform_results_data():
    """Test the transform_results_data function."""
    mock_results = {
        1: {
            "Best Treatment Group": ["A", "B"],
            "Control Group": ["C", "D"],
            "MAPE": 0.15,
            "SMAPE": 0.20,
            "Actual Target Metric (y)": np.array([1, 2, 3]),
            "Predictions": np.array([1.1, 1.9, 3.1]),
            "Weights": np.array([0.6, 0.4]),
            "Holdout Percentage": 75.0,
        },
        2: {
            "Best Treatment Group": ["E", "F"],
            "Control Group": ["G", "H"],
            "MAPE": 0.12,
            "SMAPE": 0.18,
            "Actual Target Metric (y)": np.array([4, 5, 6]),
            "Predictions": np.array([4.1, 4.8, 6.2]),
            "Weights": np.array([0.7, 0.3]),
            "Holdout Percentage": 65.0,
        },
    }

    transformed = transform_results_data(mock_results)

    assert isinstance(transformed, dict), "Transformed data should be a dictionary"
    assert len(transformed) == 2, "Should have same number of entries"

    for size, data in transformed.items():
        assert "Best Treatment Group" in data
        assert "Control Group" in data
        assert isinstance(data["Best Treatment Group"], str)
        assert isinstance(data["Control Group"], str)
        assert isinstance(data["MAPE"], float)
        assert isinstance(data["SMAPE"], float)
        assert isinstance(data["Holdout Percentage"], float)


def test_run_geo_analysis_insufficient_data():
    """Test analysis with insufficient data."""
    small_data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=10),
            "location": ["Location_A"] * 10,
            "Y": np.random.rand(10) * 100,
        }
    )

    results = run_geo_analysis_streamlit_app(
        data=small_data,
        maximum_treatment_percentage=0.50,
        significance_level=0.05,
        deltas_range=(0.05, 0.10, 0.05),
        periods_range=(5, 10, 5),
        excluded_locations=[],
        n_permutations_per_test=10,
        n_power_simulations=5,
    )

    assert isinstance(results, dict), "Should return dict even with insufficient data"


def test_run_geo_analysis_all_locations_excluded(sample_data):
    """Test analysis when all locations are excluded."""
    all_locations = sample_data["location"].unique().tolist()

    with pytest.raises(
        ValueError, match="treatment size.*exceeds.*available number of columns"
    ):
        run_geo_analysis_streamlit_app(
            data=sample_data,
            maximum_treatment_percentage=0.50,
            significance_level=0.05,
            deltas_range=(0.05, 0.10, 0.05),
            periods_range=(10, 15, 5),
            excluded_locations=all_locations,
            n_permutations_per_test=30,
            n_power_simulations=10,
        )

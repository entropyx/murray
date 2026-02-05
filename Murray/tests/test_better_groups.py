import pytest
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from Murray.main import (
    BetterGroups,
    SyntheticControl,
    select_treatments,
    select_controls,
    is_streamlit_context,
)
from Murray.auxiliary import market_correlations, cleaned_data, handle_duplicates
from logger_config import get_logger
import os

logger = get_logger("tests")


@pytest.fixture(scope="module")
def cleaned_dataframe():
    """Fixture that creates synthetic test data"""
    np.random.seed(42)

    dates = pd.date_range(start="2023-01-01", periods=100)
    regions = ["Region_A", "Region_B", "Region_C", "Region_D", "Region_E"]

    data = []
    for region in regions:
        base_value = np.random.randint(50, 100)
        for date in dates:
            value = base_value + np.sin(date.day / 15) * 10 + np.random.normal(0, 2)
            data.append(
                {"date": date, "region": region, "add_to_carts": max(0, int(value))}
            )

    df = pd.DataFrame(data)
    return cleaned_data(df, "add_to_carts", "region", "date")


@pytest.fixture(scope="module")
def cleaned_dataframe_with_duplicates():
    """Fixture that creates synthetic test data with duplicates"""
    np.random.seed(42)

    dates = pd.date_range(start="2023-01-01", periods=50)
    regions = ["Region_A", "Region_B", "Region_C", "Region_D", "Region_E"]

    data = []
    for region in regions:
        base_value = np.random.randint(50, 100)
        for date in dates:
            value = base_value + np.sin(date.day / 15) * 10 + np.random.normal(0, 2)
            data.append(
                {"date": date, "region": region, "add_to_carts": max(0, int(value))}
            )
            if np.random.random() < 0.1:
                data.append(
                    {
                        "date": date,
                        "region": region,
                        "add_to_carts": max(0, int(value + np.random.normal(0, 5))),
                    }
                )

    df = pd.DataFrame(data)
    return cleaned_data(df, "add_to_carts", "region", "date")


@pytest.fixture(scope="module")
def correlation_matrix(cleaned_dataframe):
    """Fixture that generates the correlation matrix from synthetic data"""
    return market_correlations(cleaned_dataframe)


@pytest.fixture(scope="module")
def similarity_matrix(correlation_matrix):
    """Fixture to generate a similarity matrix"""
    return correlation_matrix.copy()


@pytest.fixture
def test_data(cleaned_dataframe):
    """Fixture to generate test data"""
    return cleaned_dataframe.copy()


def test_is_streamlit_context():
    """Test streamlit context detection function"""
    original_port = os.environ.get("STREAMLIT_SERVER_PORT")
    original_address = os.environ.get("STREAMLIT_SERVER_ADDRESS")

    if "STREAMLIT_SERVER_PORT" in os.environ:
        del os.environ["STREAMLIT_SERVER_PORT"]
    if "STREAMLIT_SERVER_ADDRESS" in os.environ:
        del os.environ["STREAMLIT_SERVER_ADDRESS"]

    assert (
        not is_streamlit_context()
    ), "Should return False when not in Streamlit context"

    os.environ["STREAMLIT_SERVER_PORT"] = "8501"
    assert (
        is_streamlit_context()
    ), "Should return True when STREAMLIT_SERVER_PORT is set"

    if original_port is not None:
        os.environ["STREAMLIT_SERVER_PORT"] = original_port
    elif "STREAMLIT_SERVER_PORT" in os.environ:
        del os.environ["STREAMLIT_SERVER_PORT"]

    if original_address is not None:
        os.environ["STREAMLIT_SERVER_ADDRESS"] = original_address
    elif "STREAMLIT_SERVER_ADDRESS" in os.environ:
        del os.environ["STREAMLIT_SERVER_ADDRESS"]


def test_better_groups_with_duplicates(
    similarity_matrix, correlation_matrix, cleaned_dataframe_with_duplicates
):
    """Test BetterGroups with data containing duplicates"""
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=cleaned_dataframe_with_duplicates,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert len(results) > 0, "There must be at least one evaluated treatment group"
    for size, result in results.items():
        assert "Best Treatment Group" in result, "Missing treatment group"
        assert "Control Group" in result, "Missing control group"
        assert "MAPE" in result, "Missing MAPE metric"
        assert "SMAPE" in result, "Missing SMAPE metric"
        assert "Holdout Percentage" in result, "Missing holdout percentage"


def test_better_groups_valid(similarity_matrix, correlation_matrix, test_data):
    """Test BetterGroups with valid data"""
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert len(results) > 0, "There must be at least one evaluated treatment group"
    for size, result in results.items():
        assert "Best Treatment Group" in result, "Missing treatment group"
        assert "Control Group" in result, "Missing control group"
        assert "MAPE" in result, "Missing MAPE metric"
        assert "SMAPE" in result, "Missing SMAPE metric"
        assert "Holdout Percentage" in result, "Missing holdout percentage"
        assert "observed_conformity" in result, "Missing observed conformity"
        assert result["MAPE"] >= 0, "MAPE must be a positive number"
        assert (
            0 <= result["Holdout Percentage"] <= 100
        ), "Holdout must be between 0 and 100"


def test_better_groups_empty_data(similarity_matrix, correlation_matrix):
    """Test BetterGroups with empty data"""
    empty_data = pd.DataFrame(columns=["time", "location", "Y"])

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=empty_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert results is None, "Empty data should return None"


def test_better_groups_zero_total_y(similarity_matrix, correlation_matrix, test_data):
    """Test BetterGroups with zero total Y values"""
    test_data_zero = test_data.copy()
    test_data_zero["Y"] = 0

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data_zero,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert results is None, "Zero total Y should return None"


def test_better_groups_no_valid_treatments(
    similarity_matrix, correlation_matrix, test_data
):
    """Test BetterGroups with no valid treatment locations"""
    test_data_limited = test_data[test_data["location"].isin(["X", "Y"])]
    logger.debug(f"test data: {test_data_limited}")
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data_limited,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert results is None, "If there are no valid locations, the result must be None"


def test_better_groups_scaled_data(similarity_matrix, correlation_matrix, test_data):
    """Test BetterGroups with scaled data"""
    scaler = MinMaxScaler()
    test_data["Y"] = scaler.fit_transform(test_data["Y"].values.reshape(-1, 1))

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert all(
        isinstance(result["MAPE"], (float, int)) for result in results.values()
    ), "MAPE must be a number"


def test_better_groups_with_excluded_locations(
    similarity_matrix, correlation_matrix, test_data
):
    """Test BetterGroups with excluded locations"""
    excluded = ["region_a", "region_b"]

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=excluded,
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    if results is not None:
        for size, result in results.items():
            treatment_group = result["Best Treatment Group"]
            assert not any(
                loc in excluded for loc in treatment_group
            ), f"Excluded location found in treatment group: {treatment_group}"


def test_better_groups_no_control(
    monkeypatch, similarity_matrix, correlation_matrix, test_data
):
    """Test BetterGroups when no control group can be found"""

    def fake_select_controls(correlation_matrix, treatment_group, min_correlation, excluded_control_locations=None):
        return []

    monkeypatch.setattr("Murray.main.select_controls", fake_select_controls)

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    if results is not None:
        for result in results.values():
            assert isinstance(result["MAPE"], (int, float)), "MAPE should be a number"
            assert "Control Group" in result, "Should have control group field"


def test_better_groups_functionality():
    """Test that BetterGroups function works correctly with various parameters"""
    import numpy as np
    import pandas as pd
    from Murray.auxiliary import market_correlations, cleaned_data

    np.random.seed(42)
    dates = pd.date_range(start="2023-01-01", periods=50)
    regions = ["region_a", "region_b", "region_c"]

    data = []
    for region in regions:
        base_value = np.random.randint(50, 100)
        for date in dates:
            value = base_value + np.sin(date.day / 15) * 10 + np.random.normal(0, 2)
            data.append(
                {"date": date, "region": region, "add_to_carts": max(0, int(value))}
            )

    df = pd.DataFrame(data)
    test_data = cleaned_data(df, "add_to_carts", "region", "date")
    correlation_matrix = market_correlations(test_data)
    similarity_matrix = correlation_matrix.copy()

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
    )

    if results is not None:
        assert isinstance(results, dict), "Should return a dictionary"
        assert len(results) > 0, "Should have some results"

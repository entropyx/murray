import pytest
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from Murray.main import BetterGroups, SyntheticControl, select_treatments, select_controls
from Murray.auxiliary import market_correlations, cleaned_data

@pytest.fixture(scope="module")
def cleaned_dataframe():
    """Fixture that loads and cleans the real data"""
    dataset_path = r"Murray\data\data1.csv" 
    col_target = "add_to_carts"
    col_locations = "region"
    col_dates = "date"

    df = pd.read_csv(dataset_path)
    df_cleaned = cleaned_data(df, col_target, col_locations, col_dates)
    return df_cleaned

@pytest.fixture(scope="module")
def correlation_matrix(cleaned_dataframe):
    """Fixture that generates the correlation matrix from the cleaned data"""
    return market_correlations(cleaned_dataframe)

@pytest.fixture(scope="module")
def similarity_matrix(correlation_matrix):
    """Fixture to generate a similarity matrix"""
    return correlation_matrix.copy()

@pytest.fixture
def test_data(cleaned_dataframe):
    """Fixture to generate test data"""
    return cleaned_dataframe.copy()


def test_better_groups_valid(similarity_matrix, correlation_matrix, test_data):
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert len(results) > 0, "There must be at least one evaluated treatment group"
    for size, result in results.items():
        assert "Best Treatment Group" in result, "Missing treatment group"
        assert "Control Group" in result, "Missing control group"
        assert "MAPE" in result, "Missing MAPE metric"
        assert "SMAPE" in result, "Missing SMAPE metric"
        assert "Holdout Percentage" in result, "Missing holdout percentage"
        assert result["MAPE"] >= 0, "MAPE must be a positive number"
        assert 0 <= result["Holdout Percentage"] <= 100, "Holdout must be between 0 and 100"


def test_better_groups_no_valid_treatments(similarity_matrix, correlation_matrix, test_data):
    test_data = test_data[test_data["location"].isin(["X", "Y"])]  
    print(f"test data: {test_data}")
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50
    )

    assert results is None, "If there are no valid locations, the result must be None"


def test_better_groups_scaled_data(similarity_matrix, correlation_matrix, test_data):
    scaler = MinMaxScaler()
    test_data["Y"] = scaler.fit_transform(test_data["Y"].values.reshape(-1, 1))  

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50
    )

    assert isinstance(results, dict), "The result must be a dictionary"
    assert all(isinstance(result["MAPE"], (float, int)) for result in results.values()), "MAPE must be a number"


def test_better_groups_no_control(monkeypatch, similarity_matrix, correlation_matrix, test_data):
    
    def fake_select_controls(correlation_matrix, treatment_group, min_correlation):
        return []  
    
    monkeypatch.setattr("Murray.main.select_controls", fake_select_controls)

    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50
    )

    for result in results.values():
        assert result["MAPE"] == float('inf'), "If there are no controls, MAPE must be infinite"

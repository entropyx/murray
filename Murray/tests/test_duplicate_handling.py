import pytest
import pandas as pd
import numpy as np
from Murray.auxiliary import handle_duplicates, market_correlations


def test_handle_duplicates_no_duplicates():
    """Test that handle_duplicates works correctly when there are no duplicates"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=5),
            "location": ["A", "B", "C", "D", "E"],
            "Y": [1, 2, 3, 4, 5],
        }
    )

    result = handle_duplicates(data)
    assert len(result) == len(data)
    assert result.equals(data)


def test_handle_duplicates_with_duplicates():
    """Test that handle_duplicates correctly aggregates duplicates"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=3).repeat(2),
            "location": ["A", "A", "B", "B", "C", "C"],
            "Y": [1, 2, 3, 4, 5, 6],
        }
    )

    result = handle_duplicates(data)
    assert len(result) == 3
    assert result["Y"].iloc[0] == 1.5
    assert result["Y"].iloc[1] == 3.5
    assert result["Y"].iloc[2] == 5.5


def test_handle_duplicates_empty_dataframe():
    """Test handle_duplicates with empty DataFrame"""
    empty_data = pd.DataFrame(columns=["time", "location", "Y"])

    result = handle_duplicates(empty_data)
    assert len(result) == 0
    assert list(result.columns) == ["time", "location", "Y"]


def test_handle_duplicates_missing_columns():
    """Test handle_duplicates raises error for missing columns"""
    data = pd.DataFrame(
        {"time": pd.date_range("2023-01-01", periods=3), "Y": [1, 2, 3]}
    )

    with pytest.raises(ValueError, match="Missing columns for duplicate check"):
        handle_duplicates(data, subset=["time", "location"])


def test_handle_duplicates_sum_aggregation():
    """Test handle_duplicates with sum aggregation method"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "Y": [1, 2, 3, 4],
        }
    )

    result = handle_duplicates(data, agg_method="sum")
    assert len(result) == 2
    assert result["Y"].iloc[0] == 3
    assert result["Y"].iloc[1] == 7


def test_handle_duplicates_first_aggregation():
    """Test handle_duplicates with first aggregation method"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "Y": [1, 2, 3, 4],
        }
    )

    result = handle_duplicates(data, agg_method="first")
    assert len(result) == 2
    assert result["Y"].iloc[0] == 1
    assert result["Y"].iloc[1] == 3


def test_handle_duplicates_last_aggregation():
    """Test handle_duplicates with last aggregation method"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "Y": [1, 2, 3, 4],
        }
    )

    result = handle_duplicates(data, agg_method="last")
    assert len(result) == 2
    assert result["Y"].iloc[0] == 2
    assert result["Y"].iloc[1] == 4


def test_handle_duplicates_custom_subset():
    """Test handle_duplicates with custom subset columns"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "category": ["X", "Y", "X", "Y"],
            "Y": [1, 2, 3, 4],
        }
    )

    result = handle_duplicates(data, subset=["time", "location"])
    assert len(result) == 2


def test_handle_duplicates_functionality_with_duplicates():
    """Test that handle_duplicates works correctly when duplicates are present"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "Y": [1, 2, 3, 4],
        }
    )

    result = handle_duplicates(data)

    assert len(result) == 2
    assert not result.duplicated(subset=["time", "location"]).any()


def test_handle_duplicates_functionality_no_duplicates():
    """Test that handle_duplicates works correctly when no duplicates are present"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=3),
            "location": ["A", "B", "C"],
            "Y": [1, 2, 3],
        }
    )

    result = handle_duplicates(data)

    assert len(result) == len(data)
    assert result.equals(data)


def test_market_correlations_with_duplicates():
    """Test that market_correlations handles duplicates correctly"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=3).repeat(2),
            "location": ["A", "A", "B", "B", "C", "C"],
            "Y": [1, 2, 3, 4, 5, 6],
        }
    )

    cleaned_data = handle_duplicates(data)

    result = market_correlations(cleaned_data)
    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == result.shape[1]
    assert result.shape[0] == 3


def test_handle_duplicates_preserves_data_types():
    """Test that handle_duplicates preserves data types"""
    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=2).repeat(2),
            "location": ["A", "A", "B", "B"],
            "Y": [1.5, 2.5, 3.5, 4.5],
        }
    )

    result = handle_duplicates(data)
    assert result["time"].dtype == data["time"].dtype
    assert result["location"].dtype == data["location"].dtype
    assert result["Y"].dtype == data["Y"].dtype


def test_handle_duplicates_large_dataset():
    """Test handle_duplicates performance with larger dataset"""
    np.random.seed(42)
    n_rows = 10000

    data = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=100).repeat(n_rows // 100),
            "location": np.random.choice(["A", "B", "C", "D", "E"], n_rows),
            "Y": np.random.randint(1, 100, n_rows),
        }
    )

    result = handle_duplicates(data)

    assert len(result) <= len(data)
    assert list(result.columns) == list(data.columns)
    assert not result.duplicated(subset=["time", "location"]).any()

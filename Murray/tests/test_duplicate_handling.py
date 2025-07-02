import pytest
import pandas as pd
import numpy as np
from Murray.auxiliary import handle_duplicates, market_correlations

def test_handle_duplicates_no_duplicates():
    """Test that handle_duplicates works correctly when there are no duplicates"""
    data = pd.DataFrame({
        'time': pd.date_range('2023-01-01', periods=5),
        'location': ['A', 'B', 'C', 'D', 'E'],
        'Y': [1, 2, 3, 4, 5]
    })
    
    result = handle_duplicates(data)
    assert len(result) == len(data)
    assert result.equals(data)

def test_handle_duplicates_with_duplicates():
    """Test that handle_duplicates correctly aggregates duplicates"""
    data = pd.DataFrame({
        'time': pd.date_range('2023-01-01', periods=3).repeat(2),
        'location': ['A', 'A', 'B', 'B', 'C', 'C'],
        'Y': [1, 2, 3, 4, 5, 6]
    })
    
    result = handle_duplicates(data)
    assert len(result) == 3  # Should have 3 unique combinations
    assert result['Y'].iloc[0] == 1.5  # Mean of 1 and 2
    assert result['Y'].iloc[1] == 3.5  # Mean of 3 and 4
    assert result['Y'].iloc[2] == 5.5  # Mean of 5 and 6

def test_market_correlations_with_duplicates():
    """Test that market_correlations handles duplicates correctly"""
    data = pd.DataFrame({
        'time': pd.date_range('2023-01-01', periods=3).repeat(2),
        'location': ['A', 'A', 'B', 'B', 'C', 'C'],
        'Y': [1, 2, 3, 4, 5, 6]
    })
    
    # This should not raise an error
    result = market_correlations(data)
    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == result.shape[1]  # Square matrix
    assert result.shape[0] == 3  # 3 unique locations 
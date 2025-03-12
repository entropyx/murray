import pytest
import numpy as np
import pandas as pd
from Murray.main import select_treatments, select_controls
from Murray.auxiliary import market_correlations, cleaned_data

@pytest.fixture(scope="module")
def cleaned_dataframe():
    """Fixture that creates synthetic test data"""
    np.random.seed(42)  
    
    dates = pd.date_range(start='2023-01-01', periods=100)
    regions = ['Region_A', 'Region_B', 'Region_C', 'Region_D', 'Region_E']
    
    data = []
    for region in regions:
        base_value = np.random.randint(50, 100)
        for date in dates:
            value = base_value + np.sin(date.day/15) * 10 + np.random.normal(0, 2)
            data.append({
                'date': date,
                'region': region,
                'add_to_carts': max(0, int(value))
            })
    
    df = pd.DataFrame(data)
    return cleaned_data(df, "add_to_carts", "region", "date")

@pytest.fixture(scope="module")
def correlation_matrix(cleaned_dataframe):
    """Fixture that generates the correlation matrix"""
    return market_correlations(cleaned_dataframe)

def test_select_treatments_valid(cleaned_dataframe, correlation_matrix):
    """Test to verify that treatments are correctly selected with a randomly excluded location"""
    excluded_location = np.random.choice(cleaned_dataframe["location"].unique()) 
    treatments = select_treatments(correlation_matrix, treatment_size=2, excluded_locations=[excluded_location])

    assert isinstance(treatments, list), "The result must be a list"
    assert all(isinstance(group, list) for group in treatments), "Each combination must be a list"
    assert all(len(group) == 2 for group in treatments), "Each combination must have 2 treatments"
    assert excluded_location not in [loc for group in treatments for loc in group], "The excluded location must not appear in the treatments"

def test_select_treatments_invalid_location(correlation_matrix):
    """Should raise a KeyError if an excluded location is not in the matrix"""
    with pytest.raises(KeyError, match="not present in the similarity matrix"):
        select_treatments(correlation_matrix, treatment_size=2, excluded_locations=["X", "Y"])

def test_select_treatments_treatment_size_too_large(correlation_matrix):
    """Should raise ValueError if treatment_size is greater than the number of available columns"""
    with pytest.raises(ValueError, match="The treatment size .* exceeds the available number of columns"):
        select_treatments(correlation_matrix, treatment_size=100, excluded_locations=[])

def test_select_treatments_treatment_size_equals_columns(correlation_matrix):
    """Should return only one combination when treatment_size is equal to the available columns"""
    num_columns = correlation_matrix.shape[1]  
    treatments = select_treatments(correlation_matrix, treatment_size=num_columns, excluded_locations=[])
    
    assert len(treatments) == 1, "There must be only one possible combination"
    assert set(treatments[0]) == set(correlation_matrix.columns), "It must contain all possible locations"


def test_select_controls_valid(cleaned_dataframe, correlation_matrix):
    """Test to verify that controls are correctly selected based on treatments"""
    excluded_location = np.random.choice(cleaned_dataframe["location"].unique())  
    treatments = select_treatments(correlation_matrix, treatment_size=2, excluded_locations=[excluded_location])
    
    for treatment_group in treatments:
        controls = select_controls(correlation_matrix, treatment_group)
        assert isinstance(controls, list), "The result must be a list"
        assert len(controls) > 0, "There must be at least one control available"
        assert all(loc not in treatment_group for loc in controls), "Controls must not be in the treatment group"

def test_select_controls_invalid_treatments(correlation_matrix):
    """Should handle nonexistent treatments without failing"""
    fake_treatment_group = ["X", "Y", "Z"]  
    controls = select_controls(correlation_matrix, fake_treatment_group)
    assert controls == [], "If the treatment does not exist, the output must be an empty list"

def test_select_controls_fallback(correlation_matrix,cleaned_dataframe):
    """Should select the `fallback_n` most correlated if no locations meet the min_correlation"""
    treatment_group = np.random.choice(cleaned_dataframe["location"].unique())  
    treatment_group = [treatment_group]
    controls = select_controls(correlation_matrix, treatment_group, min_correlation=0.99, fallback_n=3)
    
    assert len(controls) == 3, "It should select 3 fallback controls"

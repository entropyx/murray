import os
import pandas as pd
import pytest
from Murray.auxiliary import market_correlations,cleaned_data


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


tests = [
    (os.path.join(DATA_DIR, "data1.csv"), "add_to_carts", "region", "date"),
    (os.path.join(DATA_DIR, "data2.csv"), "sessions", "location", "day"),
]

@pytest.fixture
def cleaned_data_fixture(dataset_path, col_target, col_locations, col_dates):
    df = pd.read_csv(dataset_path)
    return cleaned_data(df, col_target, col_locations, col_dates)


@pytest.mark.parametrize("dataset_path, col_target, col_locations, col_dates", tests)
def test_market_correlations(cleaned_data_fixture):
    
    correlation_matrix = market_correlations(cleaned_data_fixture)
    assert isinstance(correlation_matrix, pd.DataFrame), "market_correlations should return a DataFrame"

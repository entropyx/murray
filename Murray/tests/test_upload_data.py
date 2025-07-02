import os
import pandas as pd
import pytest
import Murray as mp
from Murray.auxiliary import cleaned_data


DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


tests = [
    (os.path.join(DATA_DIR, "data1.csv"), "add_to_carts", "region", "date"),
    (os.path.join(DATA_DIR, "data2.csv"), "sessions", "location", "day"),
]



@pytest.mark.parametrize("dataset_path, col_target, col_locations, col_dates", tests)
def test_cleaned_data(dataset_path, col_target, col_locations, col_dates):
    
    assert os.path.exists(dataset_path), f"File {dataset_path} not found"
    df = pd.read_csv(dataset_path)
    df_cleaned = mp.cleaned_data(df, col_target, col_locations, col_dates)

    assert isinstance(df_cleaned, pd.DataFrame), "Output is not a DataFrame"
    assert df_cleaned.isnull().sum().sum() == 0, "Cleaned data contains NaN values"


def test_cleaned_data_basic():
    data = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=10),
        'location': ['A'] * 5 + ['B'] * 5,
        'value': range(10)
    })
    
    result = cleaned_data(data, 'value', 'location', 'date')
    
    assert isinstance(result, pd.DataFrame)
    assert 'time' in result.columns
    assert 'location' in result.columns
    assert 'Y' in result.columns
    assert len(result) == 20
    assert set(result['location'].unique()) == {'a', 'b'}
    expected_dates = pd.date_range('2023-01-01', periods=10)
    assert len(result['time'].unique()) == 10


def test_cleaned_data_column_renaming():
    data = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=5),
        'region': ['X', 'Y', 'X', 'Y', 'X'],
        'metric': [1, 2, 3, 4, 5]
    })
    
    result = cleaned_data(data, 'metric', 'region', 'timestamp')
    
    assert 'time' in result.columns
    assert 'location' in result.columns
    assert 'Y' in result.columns
    assert len(result) == 10
    expected_dates = pd.date_range('2023-01-01', periods=5)
    assert len(result['time'].unique()) == 5
    assert set(result['location'].unique()) == {'x', 'y'}


def test_cleaned_data_fills_missing_combinations():
    data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02', '2023-01-01'],
        'location': ['A', 'A', 'B'],
        'value': [10, 20, 15]
    })
    
    result = cleaned_data(data, 'value', 'location', 'date')
    
    assert len(result) == 4
    missing_combo = result[(result['time'] == '2023-01-02') & (result['location'] == 'b')]
    assert len(missing_combo) == 1
    assert missing_combo['Y'].iloc[0] == 0


def test_cleaned_data_handles_duplicates():
    data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-01', '2023-01-02'],
        'location': ['A', 'A', 'A'],
        'value': [10, 20, 30]
    })
    
    result = cleaned_data(data, 'value', 'location', 'date')
    
    assert len(result) == 2
    jan_01_value = result[result['time'] == '2023-01-01']['Y'].iloc[0]
    assert jan_01_value == 15.0



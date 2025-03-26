import os
import pandas as pd
import pytest
import Murray as mp


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



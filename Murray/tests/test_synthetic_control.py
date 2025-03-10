import pytest
import numpy as np
import pandas as pd
from sklearn.utils.validation import check_is_fitted
from Murray.main import SyntheticControl, select_controls, select_treatments
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
def select_treatment(correlation_matrix):
    return select_treatments(correlation_matrix, 6, excluded_locations=[])

@pytest.fixture(scope="module")
def select_control(correlation_matrix, select_treatment):
    return select_controls(correlation_matrix, select_treatment[0], 0.8)


@pytest.fixture
def synthetic_data(cleaned_dataframe, select_control, select_treatment):
    df = cleaned_dataframe
    df_pivot = df.pivot(index="time", columns="location", values="Y")

    X = df_pivot[select_control].values
    y = df_pivot[select_treatment[0]].sum(axis=1).values

    return X, y


def test_synthetic_control_fit(synthetic_data):
    X, y = synthetic_data
    model = SyntheticControl()
    model.fit(X, y)

    assert hasattr(model, "w_"), "The model must have optimized weights after fitting"
    assert model.w_ is not None, "Weights must not be None"
    assert np.isclose(np.sum(model.w_), 1, atol=1e-3), f"The sum of the weights must be 1 (model constraint)"


def test_synthetic_control_fit_mismatched_sizes():
    X = np.random.rand(10, 5)
    y = np.random.rand(8, 1)

    model = SyntheticControl()
    with pytest.raises(ValueError, match="The number of rows in X must match the size of y"):
        model.fit(X, y)


def test_synthetic_control_predict_without_fit():
    X = np.random.rand(10, 5)
    model = SyntheticControl()

    with pytest.raises(AttributeError, match="SyntheticControl instance is not fitted yet"):
        check_is_fitted(model)  
        model.predict(X)


def test_synthetic_control_predict(synthetic_data):
    X, y = synthetic_data
    model = SyntheticControl()
    model.fit(X, y)
    y_pred, weights = model.predict(X)

    assert isinstance(y_pred, np.ndarray), "Predictions must be a NumPy array"
    assert isinstance(weights, np.ndarray), "Weights must be a NumPy array"
    assert y_pred.shape == (X.shape[0],), "Predictions must have the same size as y"

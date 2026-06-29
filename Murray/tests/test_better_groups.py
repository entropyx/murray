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


def test_better_groups_single_cell_two_stage_gate_fields(
    similarity_matrix, correlation_matrix, test_data
):
    """ISS-1: single-cell selection is two-stage (rank by holdout SMAPE, then falsify),
    and each size carries the falsification/gate fields."""
    results = BetterGroups(
        similarity_matrix=similarity_matrix,
        excluded_locations=[],
        data=test_data,
        correlation_matrix=correlation_matrix,
        maximum_treatment_percentage=0.50,
        n_power_simulations_falsification=10,
        n_permutations_falsification=50,
    )

    assert isinstance(results, dict) and len(results) > 0
    for size, result in results.items():
        for key in (
            "Scaled L2 Imbalance",
            "abs_lift_in_zero",
            "false_positive_rate",
            "fpr_gate_passed",
            "abs_lift_gate_passed",
            "gate_passed",
        ):
            assert key in result, f"missing two-stage field {key} for size {size}"
        assert isinstance(result["gate_passed"], bool)


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

    def fake_select_controls(correlation_matrix, treatment_group, *args, **kwargs):
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


def test_evaluate_group_respects_excluded_control_locations(cleaned_dataframe):
    """`evaluate_group` (single-cell worker path) must thread excluded_control_locations into
    select_controls so excluded locations never appear in the returned Control Group.
    Regression: the single-cell BetterGroups branch called evaluate_group without this kwarg."""
    from Murray.main import evaluate_group
    correlation_matrix = market_correlations(cleaned_dataframe)
    df_pivot = cleaned_dataframe.pivot(index="time", columns="location", values="Y")
    total_Y = cleaned_dataframe["Y"].sum()
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]
    to_exclude = all_locations[1]

    result = evaluate_group(
        treatment_group=treatment_group,
        data=cleaned_dataframe,
        total_Y=total_Y,
        correlation_matrix=correlation_matrix,
        min_holdout=0,
        df_pivot=df_pivot,
        excluded_control_locations=[to_exclude],
    )

    assert result is not None, "Expected evaluate_group to return a result tuple"
    control_group = result[1]
    assert to_exclude not in control_group, (
        f"excluded_control_locations leaked into Control Group: {control_group}"
    )


def test_evaluate_group_returns_donor_matrix_and_scaled_l2(cleaned_dataframe):
    """ISS-1: evaluate_group returns a 10-tuple with scaled_l2 at [8] (diagnostic /
    tie-break) and the raw donor level matrix at [9] (for sliding-window refit)."""
    from Murray.main import evaluate_group

    correlation_matrix = market_correlations(cleaned_dataframe)
    df_pivot = cleaned_dataframe.pivot(index="time", columns="location", values="Y")
    total_Y = cleaned_dataframe["Y"].sum()
    treatment_group = [list(correlation_matrix.columns)[0]]

    result = evaluate_group(
        treatment_group=treatment_group,
        data=cleaned_dataframe,
        total_Y=total_Y,
        correlation_matrix=correlation_matrix,
        min_holdout=0,
        df_pivot=df_pivot,
    )

    assert len(result) == 10, "evaluate_group must return a 10-tuple"
    scaled_l2, donor_matrix = result[8], result[9]
    assert isinstance(scaled_l2, float), "result[8] must be the scaled_l2 imbalance (float)"
    assert donor_matrix.ndim == 2, "result[9] must be the 2-D donor level matrix"
    assert donor_matrix.shape[0] == len(df_pivot), "donor matrix has one row per period"


# ---- ISS-7: rolling-origin CV for the ranking SMAPE ----

def test_rolling_origin_smapes_returns_n_folds():
    from Murray.main import _rolling_origin_smapes

    rng = np.random.default_rng(0)
    X = rng.random((100, 3)) * 10
    y = X.sum(axis=1) + rng.normal(0, 0.5, 100)
    s = _rolling_origin_smapes(X, y, n_folds=2)
    assert len(s) == 2 and all(v >= 0 for v in s)


def test_rolling_origin_smapes_empty_for_short_series():
    from Murray.main import _rolling_origin_smapes

    # too short to place an origin past the minimum training window -> no folds
    assert _rolling_origin_smapes(np.ones((3, 2)), np.ones(3), n_folds=2) == []


def test_evaluate_group_cv_smape_robust_to_recent_shock():
    """A shock confined to the recent window inflates the single 80/20 holdout SMAPE;
    averaging earlier forward-chaining folds (cv_folds>0) yields a lower, more robust
    ranking SMAPE."""
    from Murray.main import evaluate_group

    rng = np.random.default_rng(1)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    base = rng.normal(100, 3, n)
    series = {"T": base.copy()}
    for name in ["A", "B", "C", "D"]:
        series[name] = base + rng.normal(0, 1, n)
    series["T"][-8:] *= 1.5  # recent shock, inside the holdout window

    rows = [
        {"time": d, "location": name, "Y": float(v)}
        for name, s in series.items()
        for d, v in zip(dates, s)
    ]
    data = pd.DataFrame(rows)
    df_pivot = data.pivot(index="time", columns="location", values="Y")
    correlation_matrix = market_correlations(data)
    total_Y = data["Y"].sum()

    common = dict(
        treatment_group=["T"], data=data, total_Y=total_Y,
        correlation_matrix=correlation_matrix, min_holdout=0, df_pivot=df_pivot,
        treatment_period=20,
    )
    r_single = evaluate_group(**common, cv_folds=0)
    r_cv = evaluate_group(**common, cv_folds=2)
    assert r_cv[3] < r_single[3], (
        f"CV SMAPE ({r_cv[3]}) should be below the shock-inflated single split ({r_single[3]})"
    )

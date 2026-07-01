import pytest
import numpy as np
import pandas as pd
from Murray.main import select_treatments, select_controls, select_controls_exclusive
from Murray.auxiliary import market_correlations, cleaned_data


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
def correlation_matrix(cleaned_dataframe):
    """Fixture that generates the correlation matrix"""
    return market_correlations(cleaned_dataframe)


def test_select_treatments_valid(cleaned_dataframe, correlation_matrix):
    """Test to verify that treatments are correctly selected with a randomly excluded location"""
    excluded_location = np.random.choice(cleaned_dataframe["location"].unique())
    treatments = select_treatments(
        correlation_matrix, treatment_size=2, excluded_locations=[excluded_location]
    )

    assert isinstance(treatments, list), "The result must be a list"
    assert all(
        isinstance(group, list) for group in treatments
    ), "Each combination must be a list"
    assert all(
        len(group) == 2 for group in treatments
    ), "Each combination must have 2 treatments"
    assert excluded_location not in [
        loc for group in treatments for loc in group
    ], "The excluded location must not appear in the treatments"


def test_select_treatments_invalid_location(correlation_matrix):
    """Should raise a KeyError if an excluded location is not in the matrix"""
    with pytest.raises(KeyError, match="not present in the similarity matrix"):
        select_treatments(
            correlation_matrix, treatment_size=2, excluded_locations=["X", "Y"]
        )


def test_select_treatments_treatment_size_too_large(correlation_matrix):
    """Should raise ValueError if treatment_size is greater than the number of available columns"""
    with pytest.raises(
        ValueError,
        match="The treatment size .* exceeds the available number of columns",
    ):
        select_treatments(correlation_matrix, treatment_size=100, excluded_locations=[])


def test_select_treatments_treatment_size_equals_columns(correlation_matrix):
    """Should return only one combination when treatment_size is equal to the available columns"""
    num_columns = correlation_matrix.shape[1]
    treatments = select_treatments(
        correlation_matrix, treatment_size=num_columns, excluded_locations=[]
    )

    assert len(treatments) == 1, "There must be only one possible combination"
    assert set(treatments[0]) == set(
        correlation_matrix.columns
    ), "It must contain all possible locations"


def test_select_controls_valid(cleaned_dataframe, correlation_matrix):
    """Test to verify that controls are correctly selected based on treatments"""
    excluded_location = np.random.choice(cleaned_dataframe["location"].unique())
    treatments = select_treatments(
        correlation_matrix, treatment_size=2, excluded_locations=[excluded_location]
    )

    for treatment_group in treatments:
        controls = select_controls(correlation_matrix, treatment_group)
        assert isinstance(controls, list), "The result must be a list"
        assert len(controls) > 0, "There must be at least one control available"
        assert all(
            loc not in treatment_group for loc in controls
        ), "Controls must not be in the treatment group"


def test_select_controls_invalid_treatments(correlation_matrix):
    """Should handle nonexistent treatments without failing"""
    fake_treatment_group = ["X", "Y", "Z"]
    controls = select_controls(correlation_matrix, fake_treatment_group)
    assert (
        controls == []
    ), "If the treatment does not exist, the output must be an empty list"


# ---- ISS-6: all eligible donors by default; top_k is an optional cap ----

def test_select_controls_returns_all_eligible_by_default(correlation_matrix):
    """top_k=None (default) -> every eligible donor is returned; the simplex selects."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]

    controls = select_controls(correlation_matrix, treatment_group)

    expected = set(all_locations) - set(treatment_group)
    assert set(controls) == expected, "default must return ALL eligible donors"


def test_select_controls_caps_with_top_k(correlation_matrix):
    """An explicit top_k caps the shortlist."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]

    controls = select_controls(correlation_matrix, treatment_group, top_k=2)

    assert len(controls) == 2, "top_k must cap the number of donors"
    assert treatment_group[0] not in controls


def test_select_controls_drops_nan_scored_donors():
    """Donors with a NaN correlation to the treatment are degenerate and dropped."""
    cm = pd.DataFrame(
        {
            "A": [1.0, 0.9, np.nan],
            "B": [0.9, 1.0, 0.5],
            "C": [np.nan, 0.5, 1.0],
        },
        index=["A", "B", "C"],
    )
    controls = select_controls(cm, ["A"])
    assert controls == ["B"], "NaN-scored donor C must be dropped"


def test_select_controls_respects_excluded_control_locations(correlation_matrix):
    """`select_controls` (single-cell path) must filter out excluded_control_locations."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]
    to_exclude_from_control = all_locations[1]

    controls = select_controls(
        correlation_matrix,
        treatment_group,
        excluded_control_locations=[to_exclude_from_control],
    )

    assert to_exclude_from_control not in controls
    assert treatment_group[0] not in controls


def test_select_controls_exclusive_returns_all_eligible_by_default(correlation_matrix):
    """top_k=None -> all eligible donors, minus treatment/used/excluded."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]

    controls = select_controls_exclusive(
        correlation_matrix, treatment_group, excluded_locations=[]
    )

    assert set(controls) == set(all_locations) - set(treatment_group)


def test_select_controls_exclusive_respects_excluded_control_locations(correlation_matrix):
    """`excluded_control_locations` removes locations from the control group only."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]
    to_exclude_from_control = all_locations[1]

    controls = select_controls_exclusive(
        correlation_matrix,
        treatment_group,
        excluded_locations=[],
        excluded_control_locations=[to_exclude_from_control],
    )

    assert to_exclude_from_control not in controls
    assert treatment_group[0] not in controls


def test_select_controls_exclusive_defaults_to_empty_excluded_control_locations(correlation_matrix):
    """Omitting `excluded_control_locations` == passing None (no extra exclusions)."""
    all_locations = list(correlation_matrix.columns)
    treatment_group = [all_locations[0]]

    controls_without = select_controls_exclusive(
        correlation_matrix, treatment_group, excluded_locations=[]
    )
    controls_with_none = select_controls_exclusive(
        correlation_matrix,
        treatment_group,
        excluded_locations=[],
        excluded_control_locations=None,
    )

    assert set(controls_without) == set(controls_with_none)

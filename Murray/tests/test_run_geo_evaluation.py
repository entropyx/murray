import pytest
import numpy as np
import pandas as pd
from Murray.post_analysis import run_geo_evaluation, get_evaluation_chart_data
from Murray.auxiliary import market_correlations, cleaned_data


@pytest.fixture
def sample_data():
    """Fixture that generates a test DataFrame with fictitious data"""
    np.random.seed(42)
    data = pd.DataFrame(
        {
            "time": np.tile(pd.date_range("2023-01-01", periods=100, freq="D"), 10),
            "location": np.repeat([f"Location_{i}" for i in range(10)], 100),
            "Y": np.random.rand(1000) * 100,
        }
    )
    return data


def test_run_geo_evaluation(sample_data):
    """Checks that the geographic evaluation function runs correctly"""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",  # March 1st, 2023 (day 60 in the dataset)
        end_treatment="2023-03-10",    # March 10th, 2023 (day 69 in the dataset)
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        n_permutations=100,
        inference_type="iid",
        significance_level=0.05,
    )

    assert isinstance(results, dict), "The result must be a dictionary"

    # Check for essential keys (some keys might vary based on implementation)
    essential_keys = [
        "MAPE",
        "SMAPE",
        "counterfactual",
        "treatment",
        "p_value",
        "power",
        "control_group",
        "spend",
    ]
    for key in essential_keys:
        assert key in results, f"Missing the key '{key}' in the results"

    assert isinstance(results["MAPE"], (float, np.floating)), "MAPE must be a float"
    assert isinstance(results["p_value"], (float, np.floating)), "p_value must be a float"
    assert isinstance(results["power"], (float, np.floating)), "Power must be a float"
    assert isinstance(results["control_group"], list), "Control group must be a list"
    assert 0 <= results["power"] <= 1, "Power must be between 0 and 1"
    assert 0 <= results["p_value"] <= 1, "p_value must be between 0 and 1"


def test_engine_selection_scores_only_pre_treatment_period(sample_data, monkeypatch):
    """Regression: the ridge-vs-ASCM engine selection must be scored on the PRE-treatment
    period only — never the intervention window. X_train_data spans [0:end_position_treatment]
    (pre + the 10 treatment days here), so handing the selector the treatment-start split would
    judge engines by how well they track the *treated* (effect-laden) outcome, leaking the
    intervention into model selection and biasing the lift. We capture the (X, split) given to
    the selector and assert it stays inside the pre-period.

    Fixture: treatment starts at index 59 (2023-03-01) and ends index 68, so
    end_position_treatment = 69. Pre-period is the 59 rows [0:59]; the buggy call passed 69 rows
    with split 59.
    """
    import Murray.post_analysis as pa

    captured = {}

    def fake_select(X, y, split, **kwargs):
        captured["n"] = len(X)
        captured["split"] = split
        return None, 1.0, "ridge_time"

    monkeypatch.setattr(pa, "select_engine_isolated", fake_select)

    run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        n_permutations=50,
        inference_type="iid",
        significance_level=0.05,
    )

    assert captured["n"] == 59, (
        f"selector saw {captured['n']} rows; it must see only the 59 pre-treatment rows, "
        f"not the 10 intervention days"
    )
    assert 1 <= captured["split"] < 59, (
        f"validation split {captured['split']} must hold out a window WITHIN the pre-period"
    )


def test_run_geo_evaluation_excludes_control_locations(sample_data):
    """`excluded_control_locations` must remove those locations from the final control_group."""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        excluded_control_locations=["Location_2", "Location_3"],
        n_permutations=100,
        inference_type="iid",
        significance_level=0.05,
    )

    assert "Location_2" not in results["control_group"]
    assert "Location_3" not in results["control_group"]
    # Treatment group should not be affected by the control exclusion list
    assert "Location_0" not in results["control_group"]
    assert "Location_1" not in results["control_group"]


def test_run_geo_evaluation_raises_when_all_controls_excluded(sample_data):
    """If the user excludes every non-treatment location, there is no valid control group
    and `run_geo_evaluation` must raise a clear ValueError (not a downstream pivot/index crash).

    Why: when control_group is empty, `df_pivot[control_group]` returns a zero-column DataFrame
    and the synthetic control model fails with an opaque error. The explicit guard tells the
    user exactly what went wrong."""
    all_locations = [f"Location_{i}" for i in range(10)]
    treatment = ["Location_0", "Location_1"]
    exclude_all_non_treatment = [loc for loc in all_locations if loc not in treatment]

    with pytest.raises(ValueError, match="No control locations available"):
        run_geo_evaluation(
            data_input=sample_data,
            start_treatment="2023-03-01",
            end_treatment="2023-03-10",
            treatment_group=treatment,
            spend=50000,
            excluded_control_locations=exclude_all_non_treatment,
            n_permutations=100,
            inference_type="iid",
            significance_level=0.05,
        )


def test_run_geo_evaluation_exclusion_overlap_with_treatment_is_noop(sample_data):
    """Excluding a location that is already in the treatment group must not break the run
    (treatment is always excluded from control by design; the overlap is redundant)."""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        # Location_0 is treatment AND in exclusion list — redundant but legal
        excluded_control_locations=["Location_0", "Location_3"],
        n_permutations=100,
        inference_type="iid",
        significance_level=0.05,
    )

    assert "Location_0" not in results["control_group"]
    assert "Location_3" not in results["control_group"]
    assert len(results["control_group"]) > 0, "Control group must still be populated"


def test_get_evaluation_chart_data_returns_conformal_lift_ci():
    """Parte B4: the evaluation chart data must carry a statistically valid conformal CI on
    the lift (not just the synthetic-noise ribbon). With a clear injected effect the CI
    excludes 0."""
    rng = np.random.default_rng(0)
    n = 100
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    factor = 100 + np.cumsum(rng.normal(0, 1, n))  # shared trend
    locs = [f"Location_{i}" for i in range(10)]
    series = {loc: factor + rng.normal(0, 2, n) for loc in locs}

    start_date = pd.Timestamp("2023-03-12")
    start_idx = list(dates).index(start_date)
    series["Location_0"][start_idx:] += 30.0  # clear post-treatment lift on the treated unit

    data = pd.DataFrame(
        [{"time": d, "location": loc, "Y": float(v)}
         for loc in locs for d, v in zip(dates, series[loc])]
    )

    np.random.seed(0)
    res = get_evaluation_chart_data(
        data,
        start_treatment=str(start_date.date()),
        end_treatment=str(dates[-1].date()),
        treatment_group=["Location_0"],
        significance_level=0.10,
    )

    for key in ("lift", "lift_ci_lower", "lift_ci_upper", "att_ci", "conformal_p_value",
                "conformal_significant"):
        assert key in res, f"missing conformal field {key}"

    assert res["lift_ci_lower"] > 0, f"effect CI should exclude 0, got {res['att_ci']}"
    assert res["conformal_significant"] is True

    # Task 5: the conformal fields must survive the webhook serialization path.
    import json
    from shared.serialization import convert_ndarrays

    json.dumps(convert_ndarrays(res))  # raises if any field is not JSON-safe


def test_run_geo_evaluation_exclusion_unknown_location_is_noop(sample_data):
    """Unknown locations in the exclusion list (typos, stale data) must not crash the run;
    they are simply ignored because they don't exist in the correlation matrix."""
    results = run_geo_evaluation(
        data_input=sample_data,
        start_treatment="2023-03-01",
        end_treatment="2023-03-10",
        treatment_group=["Location_0", "Location_1"],
        spend=50000,
        excluded_control_locations=["Location_Does_Not_Exist", "", "   "],
        n_permutations=100,
        inference_type="iid",
        significance_level=0.05,
    )

    assert len(results["control_group"]) > 0

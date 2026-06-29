import os
import numpy as np
import pandas as pd
import pytest
from Murray.auxiliary import (
    market_correlations,
    cleaned_data,
    _infer_seasonal_period,
)


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
    assert isinstance(
        correlation_matrix, pd.DataFrame
    ), "market_correlations should return a DataFrame"


# ---- ISS-5: seasonal differencing ----

def test_infer_seasonal_period_daily_is_weekly():
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    assert _infer_seasonal_period(idx) == 7


def test_infer_seasonal_period_weekly_or_short_is_none():
    weekly = pd.date_range("2024-01-01", periods=30, freq="W")
    assert _infer_seasonal_period(weekly) is None
    short = pd.date_range("2024-01-01", periods=2, freq="D")
    assert _infer_seasonal_period(short) is None


def _two_locations_sharing_only_weekly_cycle(n_weeks=12, seed=0):
    """Two daily series that share ONLY a weekly cycle; their daily innovations are
    independent. Levels correlate (shared cycle); seasonal diffs do not."""
    rng = np.random.default_rng(seed)
    n = n_weeks * 7
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    weekly = np.tile([10.0, 12.0, 15.0, 22.0, 18.0, 35.0, 28.0], n_weeks)
    a = 100.0 + weekly + rng.normal(0, 1.0, n)
    b = 500.0 + weekly + rng.normal(0, 1.0, n)
    frames = []
    for name, series in (("A", a), ("B", b)):
        frames.append(pd.DataFrame({"time": idx, "location": name, "Y": series}))
    return pd.concat(frames, ignore_index=True)


def test_market_correlations_removes_shared_weekly_seasonality():
    data = _two_locations_sharing_only_weekly_cycle()

    # New behavior: Spearman on seasonal (lag-7) differences -> shared cycle removed,
    # only independent innovations remain -> low correlation.
    seasonal_corr = market_correlations(data).loc["A", "B"]
    assert abs(seasonal_corr) < 0.3, f"seasonal diff should de-correlate, got {seasonal_corr}"

    # Reference: Pearson on levels is inflated by the shared weekly cycle.
    levels = data.pivot(index="time", columns="location", values="Y")
    levels_corr = levels.corr(method="pearson").loc["A", "B"]
    assert levels_corr > 0.5, f"levels should look correlated, got {levels_corr}"

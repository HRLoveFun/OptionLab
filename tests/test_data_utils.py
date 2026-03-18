"""Tests for utils/data_utils.py — recent extreme change calculation."""
import datetime as dt
import numpy as np
import pandas as pd
import pytest

from utils.data_utils import calculate_recent_extreme_change


class TestCalculateRecentExtremeChange:
    def test_uptrend(self):
        # Series going up: latest > prev → trend is "up", should find rolling min
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        series = pd.Series([100, 90, 95, 100, 110], index=idx)
        pct, extreme, date = calculate_recent_extreme_change(series)
        assert pct > 0  # positive change from low

    def test_downtrend(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="D")
        series = pd.Series([100, 110, 105, 100, 90], index=idx)
        pct, extreme, date = calculate_recent_extreme_change(series)
        assert pct < 0  # negative change from high

    def test_insufficient_data(self):
        series = pd.Series([100])
        pct, extreme, date = calculate_recent_extreme_change(series)
        assert np.isnan(pct)

    def test_empty_series(self):
        series = pd.Series([], dtype=float)
        pct, extreme, date = calculate_recent_extreme_change(series)
        assert np.isnan(pct)

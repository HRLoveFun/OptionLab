"""Tests for data_pipeline/cleaning.py — anomaly flags and business-day alignment."""
import datetime as dt
import numpy as np
import pandas as pd
import pytest

from data_pipeline.cleaning import _flag_anomalies, _get_business_days


class TestGetBusinessDays:
    def test_excludes_weekends(self):
        # Mon Jan 1 2024 to Sun Jan 7 2024 → 5 weekdays
        idx = _get_business_days(dt.date(2024, 1, 1), dt.date(2024, 1, 7))
        assert len(idx) == 5
        assert all(d.weekday() < 5 for d in idx)

    def test_single_day(self):
        # A Monday
        idx = _get_business_days(dt.date(2024, 1, 1), dt.date(2024, 1, 1))
        assert len(idx) == 1

    def test_weekend_start(self):
        # Saturday to Monday → only Monday
        idx = _get_business_days(dt.date(2024, 1, 6), dt.date(2024, 1, 8))
        assert len(idx) == 1


class TestFlagAnomalies:
    def _make_df(self, closes, volumes=None, n=50):
        """Build a minimal DataFrame with synthetic data."""
        if closes is None:
            np.random.seed(42)
            closes = 100 + np.cumsum(np.random.randn(n) * 0.5)
        n = len(closes)
        if volumes is None:
            volumes = [1_000_000] * n
        return pd.DataFrame({
            "open": closes,
            "high": np.array(closes) + 1,
            "low": np.array(closes) - 1,
            "close": closes,
            "volume": volumes,
        })

    def test_no_anomalies_in_smooth_data(self):
        df = self._make_df(None, n=100)
        flagged = _flag_anomalies(df)
        # Smooth random walk should have zero or very few flags
        assert flagged["price_jump_flag"].sum() <= 2
        assert flagged["vol_anom_flag"].sum() <= 2

    def test_ohlc_consistent(self):
        df = self._make_df([100, 101, 102])
        flagged = _flag_anomalies(df)
        # high > open and high > close, low < open and low < close → consistent
        assert flagged["ohlc_inconsistent"].sum() == 0

    def test_ohlc_inconsistent_detected(self):
        # Low is above close → inconsistent
        df = pd.DataFrame({
            "open": [100, 100],
            "high": [105, 105],
            "low": [103, 103],   # low > close
            "close": [101, 101],
            "volume": [1e6, 1e6],
        })
        flagged = _flag_anomalies(df)
        assert flagged["ohlc_inconsistent"].sum() > 0

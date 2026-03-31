"""Tests for data_pipeline.processing — feature computation correctness."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from data_pipeline.db import init_db, upsert_many
from data_pipeline.processing import _features, _agg_ohlcv, process_frequencies


# ── Helpers ───────────────────────────────────────────────────────

def _make_daily(n: int = 30, base_close: float = 100.0) -> pd.DataFrame:
    """Generate a simple OHLCV DataFrame with n business days."""
    dates = pd.bdate_range(end=dt.date.today(), periods=n)
    rng = np.random.default_rng(42)
    closes = base_close + np.cumsum(rng.normal(0, 1, n))
    df = pd.DataFrame(
        {
            "open": closes - rng.uniform(0, 1, n),
            "high": closes + rng.uniform(0.5, 2, n),
            "low": closes - rng.uniform(0.5, 2, n),
            "close": closes,
            "adj_close": closes,
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
        },
        index=dates,
    )
    return df


def _seed_clean_prices(ticker: str, df: pd.DataFrame) -> None:
    """Insert rows into clean_prices table for testing."""
    init_db()
    rows = []
    for d, r in df.iterrows():
        rows.append((
            ticker,
            d.date().isoformat(),
            float(r["open"]),
            float(r["high"]),
            float(r["low"]),
            float(r["close"]),
            float(r["adj_close"]),
            float(r["volume"]),
            1,  # is_trading_day
            0,  # missing_any
            0,  # price_jump_flag
            0,  # vol_anom_flag
            0,  # ohlc_inconsistent
        ))
    upsert_many(
        "clean_prices",
        ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume",
         "is_trading_day", "missing_any", "price_jump_flag", "vol_anom_flag", "ohlc_inconsistent"],
        rows,
    )


# ── _features() unit tests ───────────────────────────────────────

class TestFeatures:
    def test_output_columns(self):
        df = _make_daily(20)
        out = _features(df)
        expected_cols = {
            "log_return", "amplitude", "log_hl_spread",
            "parkinson_var", "gk_var",
            "log_vol_delta", "vol_zscore",
            "ma_5", "ma_10", "ma_20", "ma_60", "ma_120", "ma_250",
            "mom_10", "mom_20", "mom_60",
            "osc_high", "osc_low", "osc",
            "last_close",
        }
        assert expected_cols.issubset(set(out.columns))

    def test_log_return_values(self):
        df = _make_daily(10)
        out = _features(df)
        # log_return should be log(close_t / close_{t-1})
        expected = np.log(df["close"].iloc[1]) - np.log(df["close"].iloc[0])
        assert abs(out["log_return"].iloc[1] - expected) < 1e-10

    def test_ma_5_correctness(self):
        df = _make_daily(10)
        out = _features(df)
        # MA-5 at index 4 (5th row) should be mean of first 5 closes
        expected_ma5 = df["close"].iloc[:5].mean()
        assert abs(out["ma_5"].iloc[4] - expected_ma5) < 1e-10

    def test_momentum_values(self):
        df = _make_daily(15)
        out = _features(df)
        # mom_10 at index 10 should be close[10]/close[0] - 1
        expected = df["close"].iloc[10] / df["close"].iloc[0] - 1.0
        assert abs(out["mom_10"].iloc[10] - expected) < 1e-10

    def test_oscillation_metrics(self):
        df = _make_daily(5)
        out = _features(df)
        # osc = osc_high - osc_low
        valid = out.dropna(subset=["osc_high", "osc_low", "osc"])
        if not valid.empty:
            np.testing.assert_allclose(
                valid["osc"].values,
                (valid["osc_high"] - valid["osc_low"]).values,
                atol=1e-10,
            )

    def test_parkinson_var_non_negative(self):
        df = _make_daily(20)
        out = _features(df)
        valid = out["parkinson_var"].dropna()
        assert (valid >= 0).all()

    def test_vol_zscore_baseline(self):
        df = _make_daily(25)
        out = _features(df)
        # vol_zscore should be volume / rolling(20).mean()
        valid = out["vol_zscore"].dropna()
        assert (valid > 0).all()


# ── _agg_ohlcv() tests ──────────────────────────────────────────

class TestAggOHLCV:
    def test_weekly_aggregation(self):
        df = _make_daily(20)
        weekly = _agg_ohlcv(df, "W-FRI")
        # Should have fewer rows than daily
        assert len(weekly) < len(df)
        assert set(weekly.columns) == {"open", "high", "low", "close", "adj_close", "volume"}

    def test_monthly_aggregation(self):
        df = _make_daily(60)
        monthly = _agg_ohlcv(df, "ME")
        assert len(monthly) <= 4  # ~2-3 months of data
        assert "close" in monthly.columns


# ── process_frequencies() integration tests ──────────────────────

class TestProcessFrequencies:
    def test_basic_pipeline(self):
        """Process 30 days of synthetic data through all frequencies."""
        df = _make_daily(30)
        _seed_clean_prices("TEST", df)
        start = df.index[0].date()
        end = df.index[-1].date()
        result = process_frequencies("TEST", start, end)
        assert result.ok
        assert result.rows > 0

    def test_empty_data_returns_zero_rows(self):
        """No cleaned data → 0 rows, still ok."""
        init_db()
        result = process_frequencies("NODATA", dt.date(2020, 1, 1), dt.date(2020, 1, 31))
        assert result.ok
        assert result.rows == 0
        assert len(result.warnings) > 0

    def test_all_frequencies_present(self):
        """Check D, W, ME rows are produced."""
        from data_pipeline.db import fetch_df

        df = _make_daily(30)
        _seed_clean_prices("FREQ", df)
        start = df.index[0].date()
        end = df.index[-1].date()
        process_frequencies("FREQ", start, end)

        for freq in ("D", "W", "ME"):
            out = fetch_df(
                "SELECT * FROM processed_prices WHERE ticker=? AND frequency=?",
                ("FREQ", freq),
            )
            assert not out.empty, f"No rows for frequency {freq}"

    def test_feature_columns_in_db(self):
        """Verify key feature columns are stored."""
        from data_pipeline.db import fetch_df

        df = _make_daily(30)
        _seed_clean_prices("COLS", df)
        start = df.index[0].date()
        end = df.index[-1].date()
        process_frequencies("COLS", start, end)

        out = fetch_df(
            "SELECT * FROM processed_prices WHERE ticker=? AND frequency='D'",
            ("COLS",),
        )
        for col in ("log_return", "ma_5", "ma_20", "mom_10", "osc"):
            assert col in out.columns, f"Missing column: {col}"

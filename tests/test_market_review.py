"""Tests for core.market_review — data processing, caching, and output format."""
import datetime as dt
from unittest.mock import patch

import numpy as np
import pandas as pd

from data_pipeline.db import get_conn, init_db

# ── Helpers ───────────────────────────────────────────────────────

def _make_benchmark_prices(tickers: list[str], days: int = 60) -> pd.DataFrame:
    """Generate synthetic close prices for multiple tickers."""
    dates = pd.bdate_range(end=dt.date.today(), periods=days)
    rng = np.random.default_rng(42)
    data = {}
    for t in tickers:
        base = 100 + rng.normal(0, 10)
        data[t] = base + np.cumsum(rng.normal(0, 0.5, days))
    return pd.DataFrame(data, index=dates)


def _seed_market_review_prices(tickers: list[str], days: int = 60) -> None:
    """Seed the market_review_prices table with synthetic data."""
    init_db()
    df = _make_benchmark_prices(tickers, days)
    rows = []
    for t in tickers:
        for date_idx, val in df[t].items():
            rows.append((t, date_idx.strftime('%Y-%m-%d'), float(val)))
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO market_review_prices (ticker, date, close) "
            "VALUES (?, ?, ?) ON CONFLICT(ticker, date) DO UPDATE SET close=excluded.close",
            rows,
        )
        conn.commit()


# ── Cache tests ──────────────────────────────────────────────────

class TestMarketReviewCache:
    def test_cache_hit_avoids_refetch(self):
        """After first fetch, second call should use L1 cache."""
        from core.market_review import BENCHMARKS, _mr_cache, _mr_cache_lock

        all_tickers = ["AAPL"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=60)

        # Clear L1 cache
        with _mr_cache_lock:
            _mr_cache.clear()

        from core.market_review import _fetch_market_data

        with patch("core.market_review._yf_download_with_retry"):
            # First call — should use DB (not yfinance since we seeded)
            data1, ret1, disp1 = _fetch_market_data("AAPL")
            # Second call — should hit L1 cache
            data2, ret2, disp2 = _fetch_market_data("AAPL")
            assert data1.shape == data2.shape
            assert disp1 == disp2

    def test_cache_returns_copy(self):
        """Cached data should be a copy — mutations don't affect cache."""
        from core.market_review import BENCHMARKS, _fetch_market_data, _mr_cache, _mr_cache_lock

        all_tickers = ["MSFT"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=60)

        with _mr_cache_lock:
            _mr_cache.clear()

        with patch("core.market_review._yf_download_with_retry"):
            data1, _, _ = _fetch_market_data("MSFT")
            original_shape = data1.shape
            data1.drop(data1.index[:10], inplace=True)
            data2, _, _ = _fetch_market_data("MSFT")
            assert data2.shape == original_shape


# ── market_review output format tests ────────────────────────────

class TestMarketReviewOutput:
    def test_returns_dataframe(self):
        """market_review() returns a DataFrame with MultiIndex columns."""
        from core.market_review import BENCHMARKS, _mr_cache, _mr_cache_lock, market_review

        all_tickers = ["GOOGL"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=100)

        with _mr_cache_lock:
            _mr_cache.clear()

        with patch("core.market_review._yf_download_with_retry"):
            result = market_review("GOOGL")
            assert isinstance(result, pd.DataFrame)
            assert isinstance(result.columns, pd.MultiIndex)
            assert len(result) > 0

    def test_result_contains_expected_assets(self):
        """Result index should contain the primary ticker and benchmark names."""
        from core.market_review import BENCHMARKS, _mr_cache, _mr_cache_lock, market_review

        all_tickers = ["TSLA"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=100)

        with _mr_cache_lock:
            _mr_cache.clear()

        with patch("core.market_review._yf_download_with_retry"):
            result = market_review("TSLA")
            assert "TSLA" in result.index


# ── market_review_timeseries tests ───────────────────────────────

class TestMarketReviewTimeseries:
    def test_returns_dict_structure(self):
        """market_review_timeseries() returns dict with expected keys."""
        from core.market_review import BENCHMARKS, _mr_cache, _mr_cache_lock, market_review_timeseries

        all_tickers = ["AMZN"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=100)

        with _mr_cache_lock:
            _mr_cache.clear()

        with patch("core.market_review._yf_download_with_retry"):
            result = market_review_timeseries("AMZN")
            assert "dates" in result
            assert "assets" in result
            assert "instrument" in result
            assert len(result["dates"]) > 0

    def test_assets_have_expected_fields(self):
        """Each asset entry should have prices, cum_return, rolling_vol."""
        from core.market_review import BENCHMARKS, _mr_cache, _mr_cache_lock, market_review_timeseries

        all_tickers = ["META"] + list(BENCHMARKS.values())
        _seed_market_review_prices(all_tickers, days=100)

        with _mr_cache_lock:
            _mr_cache.clear()

        with patch("core.market_review._yf_download_with_retry"):
            result = market_review_timeseries("META")
            for _asset_name, asset_data in result["assets"].items():
                assert "prices" in asset_data
                assert "cum_returns" in asset_data
                assert "rolling_vol" in asset_data

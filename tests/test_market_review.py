"""Tests for services.market_review — L1 cache + output format.

Batch B10 folded the benchmark close panel into the provider seam: the ladder
no longer owns a ``market_review_prices`` table, it calls
``DataService.get_close_panel`` (which reads ``clean_bars``). These tests stub
that call and focus on the L1 cache behaviour and the shape of what
``core.market_review`` produces from a panel.
"""

import datetime as dt
from unittest.mock import patch

import numpy as np
import pandas as pd

# ── Helpers ───────────────────────────────────────────────────────


def _make_close_panel(tickers: list[str], days: int = 120) -> pd.DataFrame:
    """A synthetic wide close-price panel, date-indexed, one column per ticker —
    the shape ``DataService.get_close_panel`` returns."""
    dates = pd.bdate_range(end=dt.date.today(), periods=days)
    rng = np.random.default_rng(42)
    data = {}
    for t in tickers:
        base = 100 + rng.normal(0, 10)
        data[t] = base + np.cumsum(rng.normal(0, 0.5, days))
    return pd.DataFrame(data, index=dates)


def _patch_panel(primary: str):
    """Patch ``DataService.get_close_panel`` to return a panel covering
    *primary* + every benchmark."""
    from services.market_review import BENCHMARKS

    panel = _make_close_panel([primary] + list(BENCHMARKS.values()))
    return patch(
        "services.market_review.fetch.DataService.get_close_panel",
        return_value=panel,
    )


# ── Cache tests ──────────────────────────────────────────────────


class TestMarketReviewCache:
    def test_cache_hit_avoids_refetch(self, clear_mr_cache):
        """After first fetch, the second call uses the L1 cache and never
        re-enters the read layer."""
        from services.market_review import _fetch_market_data

        clear_mr_cache()
        with _patch_panel("AAPL") as mocked:
            data1, _ret1, disp1 = _fetch_market_data("AAPL")
            data2, _ret2, disp2 = _fetch_market_data("AAPL")

        assert data1.shape == data2.shape
        assert disp1 == disp2
        assert mocked.call_count == 1, "second call must be served from the L1 cache"

    def test_cache_returns_copy(self, clear_mr_cache):
        """Cached data is a copy — mutating a result must not corrupt the cache."""
        from services.market_review import _fetch_market_data

        clear_mr_cache()
        with _patch_panel("MSFT"):
            data1, _, _ = _fetch_market_data("MSFT")
            original_shape = data1.shape
            data1.drop(data1.index[:10], inplace=True)
            data2, _, _ = _fetch_market_data("MSFT")

        assert data2.shape == original_shape


# ── market_review output format tests ────────────────────────────


class TestMarketReviewOutput:
    def test_returns_dataframe(self, clear_mr_cache):
        from services.market_review import market_review

        clear_mr_cache()
        with _patch_panel("GOOGL"):
            result = market_review("GOOGL")

        assert isinstance(result, pd.DataFrame)
        assert isinstance(result.columns, pd.MultiIndex)
        assert len(result) > 0

    def test_result_contains_primary_ticker(self, clear_mr_cache):
        from services.market_review import market_review

        clear_mr_cache()
        with _patch_panel("TSLA"):
            result = market_review("TSLA")

        assert "TSLA" in result.index


# ── market_review_timeseries tests ───────────────────────────────


class TestMarketReviewTimeseries:
    def test_returns_dict_structure(self, clear_mr_cache):
        from services.market_review import market_review_timeseries

        clear_mr_cache()
        with _patch_panel("AMZN"):
            result = market_review_timeseries("AMZN")

        assert "dates" in result
        assert "assets" in result
        assert "instrument" in result
        assert len(result["dates"]) > 0

    def test_assets_have_expected_fields(self, clear_mr_cache):
        from services.market_review import market_review_timeseries

        clear_mr_cache()
        with _patch_panel("META"):
            result = market_review_timeseries("META")

        for _asset_name, asset_data in result["assets"].items():
            assert "prices" in asset_data
            assert "cum_returns" in asset_data
            assert "rolling_vol" in asset_data

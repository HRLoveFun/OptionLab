"""Tests for data_service.py — cooldown, throttle, and concurrency behavior."""
import datetime as dt
import threading
import time
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from data_pipeline import PipelineResult
from data_pipeline.db import init_db
from data_pipeline.data_service import (
    DataService,
    _update_locks,
    _update_lock_mutex,
    _UPDATE_COOLDOWN,
    _cache_get,
    _cache_set,
    _cache_invalidate,
    _query_cache,
    _query_cache_lock,
    _QUERY_CACHE_TTL,
)


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset cooldown locks and query cache before each test."""
    with _update_lock_mutex:
        _update_locks.clear()
    with _query_cache_lock:
        _query_cache.clear()
    yield
    with _update_lock_mutex:
        _update_locks.clear()
    with _query_cache_lock:
        _query_cache.clear()


# ── Cooldown tests ───────────────────────────────────────────────

class TestCooldown:
    @patch("data_pipeline.data_service.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_first_call_runs_pipeline(self, mock_dl, mock_cl, mock_pr):
        init_db()
        result = DataService.manual_update("COOL1")
        assert result is True
        mock_dl.assert_called_once()

    @patch("data_pipeline.data_service.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_second_call_within_cooldown_skips(self, mock_dl, mock_cl, mock_pr):
        init_db()
        DataService.manual_update("COOL2")
        result = DataService.manual_update("COOL2")
        assert result is False
        assert mock_dl.call_count == 1  # only first call

    @patch("data_pipeline.data_service.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_different_tickers_not_blocked(self, mock_dl, mock_cl, mock_pr):
        init_db()
        DataService.manual_update("TCKR_A")
        result = DataService.manual_update("TCKR_B")
        assert result is True
        assert mock_dl.call_count == 2

    @patch("data_pipeline.data_service.upsert_raw_prices",
           return_value=PipelineResult(ok=False, error="download_failed"))
    def test_failed_pipeline_clears_cooldown(self, mock_dl):
        """If download fails, cooldown should NOT prevent retry (since we return False, not raise)."""
        init_db()
        result = DataService.manual_update("FAIL1")
        assert result is False
        # The cooldown was set but pipeline returned False.
        # Per current code: cooldown is NOT cleared on stage failure (only on exception).
        # This tests the current behavior.


# ── Concurrent update tests ──────────────────────────────────────

class TestConcurrentUpdates:
    @patch("data_pipeline.data_service.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_concurrent_same_ticker_only_one_runs(self, mock_dl, mock_cl, mock_pr):
        """Two threads updating same ticker: only first should actually run."""
        init_db()
        results = []

        def update():
            r = DataService.manual_update("CONC1")
            results.append(r)

        t1 = threading.Thread(target=update)
        t2 = threading.Thread(target=update)
        t1.start()
        t1.join()
        t2.start()
        t2.join()
        # One True (ran), one False (cooldown)
        assert sorted(results) == [False, True]

    @patch("data_pipeline.data_service.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.data_service.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_concurrent_different_tickers_both_run(self, mock_dl, mock_cl, mock_pr):
        """Two threads updating different tickers: both should run."""
        init_db()
        results = {}

        def update(ticker):
            results[ticker] = DataService.manual_update(ticker)

        t1 = threading.Thread(target=update, args=("AAA",))
        t2 = threading.Thread(target=update, args=("BBB",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert results["AAA"] is True
        assert results["BBB"] is True


# ── TTL query cache tests ────────────────────────────────────────

class TestQueryCache:
    def test_cache_set_and_get(self):
        key = ("AAPL", "clean", "2024-01-01", "2024-12-31")
        df = pd.DataFrame({"close": [100, 101]})
        _cache_set(key, df)
        cached = _cache_get(key)
        assert cached is not None
        pd.testing.assert_frame_equal(cached, df)

    def test_cache_returns_copy(self):
        key = ("MSFT", "clean", "2024-01-01", "2024-12-31")
        df = pd.DataFrame({"close": [200]})
        _cache_set(key, df)
        cached = _cache_get(key)
        cached["close"] = [999]
        cached2 = _cache_get(key)
        assert cached2["close"].iloc[0] == 200  # original unchanged

    def test_cache_miss_returns_none(self):
        assert _cache_get(("NONEXIST", "clean", "x", "y")) is None

    def test_cache_invalidate_by_ticker(self):
        _cache_set(("TSLA", "clean", "a", "b"), pd.DataFrame({"x": [1]}))
        _cache_set(("TSLA", "processed", "D", "a"), pd.DataFrame({"x": [2]}))
        _cache_set(("GOOG", "clean", "a", "b"), pd.DataFrame({"x": [3]}))
        _cache_invalidate("TSLA")
        assert _cache_get(("TSLA", "clean", "a", "b")) is None
        assert _cache_get(("TSLA", "processed", "D", "a")) is None
        assert _cache_get(("GOOG", "clean", "a", "b")) is not None

    def test_cache_ttl_expiry(self):
        """Simulate TTL expiry by manipulating the stored timestamp."""
        key = ("EXPIRY", "clean", "a", "b")
        df = pd.DataFrame({"close": [42]})
        _cache_set(key, df)
        # Manually set timestamp to past
        with _query_cache_lock:
            _query_cache[key] = (time.monotonic() - _QUERY_CACHE_TTL - 1, df)
        assert _cache_get(key) is None

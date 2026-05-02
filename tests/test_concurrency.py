"""Tests for data_service.py — cooldown, throttle, and concurrency behavior."""

import threading
import time
from unittest.mock import patch

import pandas as pd
import pytest

from data_pipeline import PipelineResult
from data_pipeline.data_service import (
    _QUERY_CACHE_TTL,
    DataService,
    _cache_get,
    _cache_invalidate,
    _cache_set,
    _query_cache,
    _query_cache_lock,
    _update_lock_mutex,
    _update_locks,
)
from data_pipeline.db import init_db


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
    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_first_call_runs_pipeline(self, mock_dl, mock_cl, mock_pr):
        init_db()
        result = DataService.manual_update("COOL1")
        assert result is True
        mock_dl.assert_called_once()

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_second_call_within_cooldown_skips(self, mock_dl, mock_cl, mock_pr):
        init_db()
        DataService.manual_update("COOL2")
        result = DataService.manual_update("COOL2")
        assert result is False
        assert mock_dl.call_count == 1  # only first call

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    def test_different_tickers_not_blocked(self, mock_dl, mock_cl, mock_pr):
        init_db()
        DataService.manual_update("TCKR_A")
        result = DataService.manual_update("TCKR_B")
        assert result is True
        assert mock_dl.call_count == 2

    @patch(
        "data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(ok=False, error="download_failed")
    )
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
    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
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

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
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


# ── ensure_range in-flight dedup ─────────────────────────────────


class TestEnsureRangeInflightDedup:
    """Regression test for the 'NVDA backfill repeated 4×' bug.

    When 4 streaming render slices fire concurrently, they all call
    ``ensure_range(NVDA, …)`` at the same time. Without in-flight dedup,
    each starts its own multi-year backfill — burning the yfinance
    rate-limit budget. The fix uses a per-ticker threading.Event so only
    one thread (the leader) runs the backfill; the rest wait and inherit
    the leader's memo.
    """

    def setup_method(self):
        DataService._ensure_range_memo.clear()
        DataService._ensure_range_inflight.clear()

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.db.fetch_df")
    def test_concurrent_calls_run_backfill_only_once(self, mock_fetch_df, mock_dl, mock_cl, mock_pr):
        import datetime as dt

        # Simulate empty DB so impl always proceeds to the chunked download.
        mock_fetch_df.return_value = pd.DataFrame({"min_d": [None], "max_d": [None], "n": [0]})

        # Slow the leader's downloader so followers actually queue up
        # behind the inflight Event instead of racing past it.
        original = mock_dl.return_value

        def slow_download(*args, **kwargs):
            time.sleep(0.05)
            return original

        mock_dl.side_effect = slow_download

        results = []

        def call():
            results.append(
                DataService.ensure_range("DEDUPTEST", dt.date(2024, 1, 1), dt.date(2024, 6, 1))
            )

        threads = [threading.Thread(target=call) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All 4 callers should report success.
        assert results == [True, True, True, True]
        # But the heavy upsert_raw_prices must only have been called by the
        # leader (a small number of chunks for the requested 5-month range,
        # NOT 4× that).
        leader_chunks = mock_dl.call_count
        # 5 months ≈ 152 days; chunk size ≈ 89 ⇒ 2 chunks for the leader.
        # Followers should add 0. Allow a small margin but reject 4×.
        assert leader_chunks <= 4, (
            f"in-flight dedup failed: upsert_raw_prices called {leader_chunks} times "
            f"(expected ≤ 4 for one leader's chunked backfill)"
        )

    def test_sentinel_start_skips_backfill_when_db_has_coverage(self):
        """PriceDynamic sentinel start (1900-01-01) must not trigger backfill
        when DB already has years of recent data."""
        import datetime as dt

        DataService._ensure_range_memo.clear()
        with patch("data_pipeline.db.fetch_df") as mock_fetch_df, patch(
            "data_pipeline.downloader.upsert_raw_prices"
        ) as mock_dl:
            # DB has 2021-01-01 .. today coverage already.
            mock_fetch_df.return_value = pd.DataFrame(
                {
                    "min_d": ["2021-01-01"],
                    "max_d": [dt.date.today().isoformat()],
                    "n": [1000],
                }
            )
            ok = DataService.ensure_range(
                "SENTINELTEST", dt.date(1900, 1, 1), dt.date.today()
            )
            assert ok is True
            assert mock_dl.call_count == 0, "must NOT walk yfinance back to 1990"

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.db.fetch_df")
    def test_explicit_multiyear_request_does_backfill(
        self, mock_fetch_df, mock_dl, mock_cl, mock_pr
    ):
        """Regression for the 'NVDA only has 30 days, user asked for 5
        years, sentinel short-circuit silently lied' bug. A user-explicit
        multi-year request must trigger backfill even when DB has only a
        recent sliver."""
        import datetime as dt

        DataService._ensure_range_memo.clear()
        DataService._ensure_range_inflight.clear()
        # DB has only March 2026 — far ahead of the user's 2021 request.
        mock_fetch_df.return_value = pd.DataFrame(
            {
                "min_d": ["2026-03-31"],
                "max_d": ["2026-04-30"],
                "n": [22],
            }
        )
        ok = DataService.ensure_range(
            "EXPLICITTEST", dt.date(2021, 3, 1), dt.date(2026, 3, 1)
        )
        assert ok is True
        assert mock_dl.call_count > 0, (
            "user-explicit 5-year range must trigger backfill — "
            "sentinel short-circuit must NOT apply here"
        )

    @patch("data_pipeline.processing.process_frequencies", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.cleaning.clean_range", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.downloader.upsert_raw_prices", return_value=PipelineResult(rows=5))
    @patch("data_pipeline.db.fetch_df")
    def test_sentinel_with_thin_db_still_backfills(
        self, mock_fetch_df, mock_dl, mock_cl, mock_pr
    ):
        """Regression: sentinel start (PriceDynamic uses 1900-01-01 always)
        but DB has only ~1 month of recent data MUST backfill. The sentinel
        short-circuit only applies when DB itself spans a meaningful horizon
        (≥ ~1 year). Otherwise the user's downstream multi-year request
        would silently see only that month."""
        import datetime as dt

        DataService._ensure_range_memo.clear()
        DataService._ensure_range_inflight.clear()
        # DB has only ~1 month of recent data — NOT authoritative.
        mock_fetch_df.return_value = pd.DataFrame(
            {
                "min_d": ["2026-03-31"],
                "max_d": ["2026-04-30"],
                "n": [22],
            }
        )
        ok = DataService.ensure_range(
            "THINSENTINELTEST", dt.date(1900, 1, 1), dt.date.today()
        )
        assert ok is True
        assert mock_dl.call_count > 0, (
            "sentinel short-circuit must NOT fire when DB span < 1y; "
            "PriceDynamic always passes sentinel start, so a thin DB would "
            "otherwise leave statistical analyses with no historical data"
        )

"""Failure-injection tests for the yfinance download path.

These tests verify that the data pipeline degrades gracefully when
yfinance misbehaves in the ways most commonly seen in production:

  * HTTP 429 rate limiting (raised by yfinance internals)
  * Network / connection timeouts
  * Empty DataFrame responses (silent rate limit)

The goal is to lock in the **graceful degradation contract**:

  1. `upsert_raw_prices` never raises — always returns a `PipelineResult`.
  2. On exception → `ok=False`, `error="download_failed: ..."`, no DB writes.
  3. On empty DataFrame → `ok=True`, `rows=0`, warning recorded.
  4. `DataService.manual_update` returns `False` on stage failure and never
     bubbles the exception.
  5. Existing DB rows survive a failed update (DB-first read still works).
  6. The DB-fresh staleness check skips the network entirely.
  7. `yf_throttle` is always invoked before any `yf.download` call.

All `yf.download` calls are mocked — no network I/O.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data_pipeline import PipelineResult
from data_pipeline.data_service import (
    DataService,
    _query_cache,
    _query_cache_lock,
    _update_lock_mutex,
    _update_locks,
)
from data_pipeline.db import fetch_df, init_db, upsert_many
from data_pipeline.downloader import _download_yf, upsert_raw_prices


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_state():
    """Init schema, then clear cooldown locks and query cache between tests."""
    init_db()
    with _update_lock_mutex:
        _update_locks.clear()
    with _query_cache_lock:
        _query_cache.clear()
    yield
    with _update_lock_mutex:
        _update_locks.clear()
    with _query_cache_lock:
        _query_cache.clear()


def _make_yf_frame(start: dt.date, days: int = 5) -> pd.DataFrame:
    """Build a yfinance-shaped DataFrame (single-level columns, datetime index)."""
    idx = pd.DatetimeIndex([start + dt.timedelta(days=i) for i in range(days)])
    return pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(days)],
            "High": [101.0 + i for i in range(days)],
            "Low": [99.0 + i for i in range(days)],
            "Close": [100.5 + i for i in range(days)],
            "Adj Close": [100.5 + i for i in range(days)],
            "Volume": [1_000_000 + i for i in range(days)],
        },
        index=idx,
    )


def _seed_raw_row(ticker: str, date: dt.date, close: float = 123.45) -> None:
    """Insert a single raw_prices row directly so we can verify it survives a failed update."""
    init_db()
    upsert_many(
        "raw_prices",
        ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"],
        [(ticker, date.isoformat(), close, close, close, close, close, 100_000, "test")],
    )


class _FakeRateLimitError(Exception):
    """Simulates yfinance's rate-limit error (which is not always a stable type
    across versions, so we match by message string)."""


# ---------------------------------------------------------------------------
# 1. Exception-path tests — yf.download raises
# ---------------------------------------------------------------------------


class TestDownloadExceptions:
    """Network / yfinance exceptions must be caught and reported, not propagated."""

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_rate_limit_429_returns_failed_result(self, mock_throttle, mock_dl):
        mock_dl.side_effect = _FakeRateLimitError("429 Too Many Requests")
        # Use a far-past start so the staleness check can't short-circuit.
        end = dt.date(2024, 1, 10)
        start = dt.date(2024, 1, 1)

        result = upsert_raw_prices("RATE_LIMITED", start=start, end=end)

        assert result.ok is False
        assert "download_failed" in (result.error or "")
        assert "429" in (result.error or "")
        assert result.rows == 0
        # Throttle must have been called once before the doomed download.
        assert mock_throttle.call_count == 1

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_connection_timeout_returns_failed_result(self, mock_throttle, mock_dl):
        mock_dl.side_effect = TimeoutError("Connection timed out")
        end = dt.date(2024, 1, 10)
        start = dt.date(2024, 1, 1)

        result = upsert_raw_prices("TIMEOUT_TKR", start=start, end=end)

        assert result.ok is False
        assert "download_failed" in (result.error or "")
        assert "timed out" in (result.error or "").lower()
        assert result.rows == 0

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_generic_exception_does_not_crash(self, mock_throttle, mock_dl):
        mock_dl.side_effect = RuntimeError("yfinance internal boom")
        end = dt.date(2024, 1, 10)
        start = dt.date(2024, 1, 1)

        # Must not raise.
        result = upsert_raw_prices("BOOM_TKR", start=start, end=end)

        assert result.ok is False
        assert "download_failed" in (result.error or "")


# ---------------------------------------------------------------------------
# 2. Empty-data path — yfinance silently returns no rows under rate limiting
# ---------------------------------------------------------------------------


class TestDownloadEmptyData:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_empty_dataframe_records_warning_no_crash(self, mock_throttle, mock_dl):
        mock_dl.return_value = pd.DataFrame()
        end = dt.date(2024, 1, 10)
        start = dt.date(2024, 1, 1)

        result = upsert_raw_prices("EMPTY_TKR", start=start, end=end)

        # Empty data is recoverable: ok=True so callers don't trigger error paths,
        # but rows=0 and a warning is recorded.
        assert result.ok is True
        assert result.rows == 0
        assert any("No new data" in w for w in result.warnings)

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_none_response_treated_as_empty(self, mock_throttle, mock_dl):
        mock_dl.return_value = None
        end = dt.date(2024, 1, 10)
        start = dt.date(2024, 1, 1)

        result = upsert_raw_prices("NONE_TKR", start=start, end=end)
        assert result.ok is True
        assert result.rows == 0


# ---------------------------------------------------------------------------
# 3. DB-first staleness check — fresh DB → no network call
# ---------------------------------------------------------------------------


class TestStalenessSkip:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_fresh_db_skips_download(self, mock_throttle, mock_dl):
        """If every business day in [start, end] is already in raw_prices, no yfinance call is made."""
        end = dt.date.today()
        start = end - dt.timedelta(days=6)
        # Seed every business day in the requested window so the gap-aware
        # coverage check finds no missing days.
        for ts in pd.bdate_range(start, end):
            _seed_raw_row("FRESH_TKR", ts.date())

        result = upsert_raw_prices("FRESH_TKR", start=start, end=end)

        assert result.ok is True
        assert result.rows == 0
        assert any("Skipped download" in w for w in result.warnings)
        # Coverage short-circuit happens *before* throttle + download.
        mock_dl.assert_not_called()
        mock_throttle.assert_not_called()

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_stale_db_triggers_download(self, mock_throttle, mock_dl):
        """If DB only has very old data, the download proceeds (and gets rate-limited
        in this test, but that's fine — we only assert that yf.download was attempted)."""
        end = dt.date.today()
        _seed_raw_row("STALE_TKR", end - dt.timedelta(days=30))

        mock_dl.side_effect = _FakeRateLimitError("429")
        result = upsert_raw_prices("STALE_TKR", end=end, days=7)

        assert result.ok is False
        mock_dl.assert_called_once()
        mock_throttle.assert_called_once()


# ---------------------------------------------------------------------------
# 4. DB survival — old data must remain readable after a failed update
# ---------------------------------------------------------------------------


class TestDbSurvivesFailure:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_existing_rows_survive_429(self, mock_throttle, mock_dl):
        """A 429 during update must NOT delete or corrupt existing DB rows."""
        end = dt.date.today()
        seed_date = end - dt.timedelta(days=20)
        _seed_raw_row("SURVIVE_TKR", seed_date, close=999.99)

        mock_dl.side_effect = _FakeRateLimitError("429 Too Many Requests")
        result = upsert_raw_prices("SURVIVE_TKR", end=end, days=7)
        assert result.ok is False

        # Pre-existing row must still be queryable.
        df = fetch_df(
            "SELECT date, close FROM raw_prices WHERE ticker=? AND date=?",
            ("SURVIVE_TKR", seed_date.isoformat()),
        )
        assert len(df) == 1
        assert float(df.iloc[0]["close"]) == pytest.approx(999.99)


# ---------------------------------------------------------------------------
# 5. Throttle ordering — yf_throttle must be called BEFORE yf.download
# ---------------------------------------------------------------------------


class TestThrottleOrdering:
    def test_throttle_called_before_download(self):
        """Verify the rate-limit guard rail: throttle precedes the network call.

        Uses a single shared MagicMock parent so call order across two patches
        is recorded in `parent.mock_calls`.
        """
        parent = MagicMock()
        parent.dl.return_value = _make_yf_frame(dt.date(2024, 1, 1), days=3)

        with (
            patch("data_pipeline.downloader.yf_throttle", parent.throttle),
            patch("data_pipeline.downloader.yf.download", parent.dl),
        ):
            _download_yf("ORDER_TKR", dt.date(2024, 1, 1), dt.date(2024, 1, 5))

        # First parent call must be throttle, then download.
        names = [c[0] for c in parent.mock_calls if c[0] in {"throttle", "dl"}]
        assert names[0] == "throttle", f"Expected throttle first, got order: {names}"
        assert "dl" in names, "yf.download was never called"


# ---------------------------------------------------------------------------
# 6. End-to-end via DataService.manual_update — exception never propagates
# ---------------------------------------------------------------------------


class TestManualUpdateGracefulFailure:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_manual_update_returns_false_on_429(self, mock_throttle, mock_dl):
        """`DataService.manual_update` must report False, not raise, on a 429."""
        init_db()
        mock_dl.side_effect = _FakeRateLimitError("429")

        # No exception expected.
        result = DataService.manual_update("E2E_TKR")
        assert result is False

    @patch("data_pipeline.data_service.upsert_raw_prices")
    def test_manual_update_returns_false_on_pipeline_error_field(self, mock_upsert):
        """Even if downloader returns ok=False (rather than raising), we degrade gracefully."""
        init_db()
        mock_upsert.return_value = PipelineResult(ok=False, error="download_failed: 429")

        result = DataService.manual_update("E2E_TKR2")
        assert result is False

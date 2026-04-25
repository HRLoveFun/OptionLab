"""Tests for the gap-aware downloader logic in `data_pipeline/downloader.py`.

These lock in the behavior fix for the NVDA-style outage: when historical
business days are missing from `raw_prices` (e.g. after a yfinance rate-limit
window), `upsert_raw_prices` must trigger a download covering the gap rather
than short-circuiting on `MAX(date)` alone.
"""

from __future__ import annotations

import datetime as dt
from unittest.mock import patch

import pandas as pd
import pytest

from data_pipeline.data_service import (
    DataService,
    _query_cache,
    _query_cache_lock,
    _update_lock_mutex,
    _update_locks,
)
from data_pipeline.db import init_db, upsert_many
from data_pipeline.downloader import find_missing_business_days, upsert_raw_prices


@pytest.fixture(autouse=True)
def _reset_state():
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


def _seed_rows(ticker: str, dates: list[dt.date]) -> None:
    rows = [
        (ticker, d.isoformat(), 100.0, 101.0, 99.0, 100.5, 100.5, 1_000_000, "test")
        for d in dates
    ]
    upsert_many(
        "raw_prices",
        ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"],
        rows,
    )


def _make_yf_frame(dates: list[dt.date]) -> pd.DataFrame:
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    return pd.DataFrame(
        {
            "Open": [100.0] * len(dates),
            "High": [101.0] * len(dates),
            "Low": [99.0] * len(dates),
            "Close": [100.5] * len(dates),
            "Adj Close": [100.5] * len(dates),
            "Volume": [1_000_000] * len(dates),
        },
        index=idx,
    )


# ---------------------------------------------------------------------------
# find_missing_business_days
# ---------------------------------------------------------------------------


class TestFindMissingBusinessDays:
    def test_no_db_rows_returns_full_window(self):
        start = dt.date(2024, 1, 1)  # Mon
        end = dt.date(2024, 1, 5)  # Fri
        missing = find_missing_business_days("EMPTY_TKR", start, end)
        assert missing == [
            dt.date(2024, 1, 1),
            dt.date(2024, 1, 2),
            dt.date(2024, 1, 3),
            dt.date(2024, 1, 4),
            dt.date(2024, 1, 5),
        ]

    def test_full_coverage_returns_empty_list(self):
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 1, 5)
        _seed_rows("FULL_TKR", list(pd.bdate_range(start, end).date))
        assert find_missing_business_days("FULL_TKR", start, end) == []

    def test_interior_gap_detected(self):
        """The original bug: rows on the edges, hole in the middle."""
        # Seed 1/1 and 1/5 only; 1/2, 1/3, 1/4 are missing business days.
        _seed_rows("GAP_TKR", [dt.date(2024, 1, 1), dt.date(2024, 1, 5)])
        missing = find_missing_business_days("GAP_TKR", dt.date(2024, 1, 1), dt.date(2024, 1, 5))
        assert missing == [dt.date(2024, 1, 2), dt.date(2024, 1, 3), dt.date(2024, 1, 4)]

    def test_weekends_are_not_missing(self):
        """Sat/Sun must never appear in the missing list."""
        # Seed Mon–Fri; Sat/Sun deliberately not seeded.
        _seed_rows("WK_TKR", list(pd.bdate_range(dt.date(2024, 1, 1), dt.date(2024, 1, 5)).date))
        missing = find_missing_business_days("WK_TKR", dt.date(2024, 1, 1), dt.date(2024, 1, 7))
        assert missing == []  # Sat 1/6 and Sun 1/7 are not business days


# ---------------------------------------------------------------------------
# upsert_raw_prices: gap-aware skip / download decisions
# ---------------------------------------------------------------------------


class TestUpsertRawPricesGapAware:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_interior_gap_triggers_download(self, mock_throttle, mock_dl):
        """The NVDA regression: existing rows on edges + interior hole → must download."""
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 1, 12)
        # Seed only first 2 and last 2 business days; leave a gap in the middle.
        _seed_rows("NVDA_REGRESSION", [dt.date(2024, 1, 1), dt.date(2024, 1, 2),
                                        dt.date(2024, 1, 11), dt.date(2024, 1, 12)])

        # Mock yfinance to return rows for the gap so the upsert succeeds.
        gap_dates = [d.date() for d in pd.bdate_range(dt.date(2024, 1, 3), dt.date(2024, 1, 10))]
        mock_dl.return_value = _make_yf_frame(gap_dates)

        result = upsert_raw_prices("NVDA_REGRESSION", start=start, end=end)

        assert result.ok is True
        # Download MUST have been attempted — the old MAX(date) check would have skipped this.
        mock_dl.assert_called_once()
        mock_throttle.assert_called_once()
        # No remaining business-day gap after upsert.
        assert find_missing_business_days("NVDA_REGRESSION", start, end) == []

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_full_coverage_skips_download(self, mock_throttle, mock_dl):
        start = dt.date(2024, 1, 1)
        end = dt.date(2024, 1, 5)
        _seed_rows("FULL_TKR", list(pd.bdate_range(start, end).date))

        result = upsert_raw_prices("FULL_TKR", start=start, end=end)

        assert result.ok is True
        assert result.rows == 0
        mock_dl.assert_not_called()
        mock_throttle.assert_not_called()

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_download_start_expanded_to_earliest_gap_within_request(self, mock_throttle, mock_dl):
        """When the requested window contains an earlier gap, the actual download
        `start` is widened to that gap (so we don't waste a round-trip on the tail)."""
        start = dt.date(2024, 1, 8)  # Mon
        end = dt.date(2024, 1, 12)  # Fri
        # Seed only the last two days; first 3 business days are the gap.
        _seed_rows("EXPAND_TKR", [dt.date(2024, 1, 11), dt.date(2024, 1, 12)])

        gap_dates = [dt.date(2024, 1, 8), dt.date(2024, 1, 9), dt.date(2024, 1, 10)]
        mock_dl.return_value = _make_yf_frame(gap_dates)

        upsert_raw_prices("EXPAND_TKR", start=start, end=end)

        called_start = mock_dl.call_args.kwargs.get("start")
        assert called_start is not None
        assert called_start <= dt.date(2024, 1, 8)


# ---------------------------------------------------------------------------
# DataService.manual_update: gap-scan window
# ---------------------------------------------------------------------------


class TestManualUpdateGapScan:
    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_old_gap_within_scan_window_triggers_download(self, mock_throttle, mock_dl):
        """`manual_update(days=7)` must still back-fill a gap older than 7 days
        when it falls within `GAP_SCAN_DAYS`."""
        end = dt.date.today()
        old_gap = end - dt.timedelta(days=15)  # within default GAP_SCAN_DAYS=30

        # Seed every business day in [end-30, end] except `old_gap`.
        scan_start = end - dt.timedelta(days=30)
        all_days = [d.date() for d in pd.bdate_range(scan_start, end)]
        _seed_rows("OLD_GAP_TKR", [d for d in all_days if d != old_gap])

        # Provide a fake response so upsert succeeds.
        mock_dl.return_value = _make_yf_frame([old_gap])

        ran = DataService.manual_update("OLD_GAP_TKR", days=7)
        assert ran is True
        # Download must have been called with start ≤ old_gap.
        called_start = mock_dl.call_args.kwargs.get("start")
        assert called_start <= old_gap

    @patch("data_pipeline.downloader.yf.download")
    @patch("data_pipeline.downloader.yf_throttle")
    def test_no_gaps_no_download(self, mock_throttle, mock_dl):
        """When the gap-scan window is fully covered, `manual_update` skips the network."""
        end = dt.date.today()
        scan_start = end - dt.timedelta(days=30)
        all_days = [d.date() for d in pd.bdate_range(scan_start, end)]
        _seed_rows("NO_GAP_TKR", all_days)

        ran = DataService.manual_update("NO_GAP_TKR", days=7)
        # Pipeline still runs (clean + process), but downloader skips the network.
        assert ran is True
        mock_dl.assert_not_called()

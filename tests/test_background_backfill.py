"""Background wide-range backfill (``get_cleaned_daily``).

The first-ever wide-range request used to run the whole chunked download on
the request thread (tens of seconds to minutes). Now the heavy backfill runs
in a daemon thread, the request waits only a short grace period, and partial
reads are never memoised.
"""

from __future__ import annotations

import datetime as dt
import time

import pandas as pd
import pytest

import data_pipeline.read._query as _q
from data_pipeline import PipelineResult
from data_pipeline._state import _cache_get, _cache_invalidate
from data_pipeline.orchestrate import backfill as _bf
from data_pipeline.orchestrate.readiness import join_backfills, kick_backfill
from data_pipeline.store.db import init_db

TICKER = "BGTEST1"


@pytest.fixture(autouse=True)
def _fast_grace(monkeypatch):
    monkeypatch.setattr(_q, "_BACKFILL_WAIT_SECONDS", 0.5)


def _slow_downloader(delay: float):
    calls = {"n": 0}

    def _dl(ticker, start, end):  # noqa: ARG001
        calls["n"] += 1
        time.sleep(delay)
        return PipelineResult(rows=10)

    return _dl, calls


class TestBackgroundBackfill:
    def test_wide_range_request_returns_without_full_backfill(self, monkeypatch):
        """Empty DB + slow downloader: the request must return quickly with
        whatever exists (nothing), while the backfill continues in background."""
        init_db()
        _dl, calls = _slow_downloader(delay=1.0)
        monkeypatch.setattr("data_pipeline.ingest.ohlcv.upsert_raw_prices", _dl)
        monkeypatch.setattr("data_pipeline.transform.cleaning.clean_range", lambda *a, **k: PipelineResult(rows=1))
        monkeypatch.setattr(
            "data_pipeline.transform.processing.process_frequencies", lambda *a, **k: PipelineResult(rows=1)
        )

        start = dt.date(2021, 1, 1)
        end = dt.date.today()
        t0 = time.monotonic()
        df = _q.get_cleaned_daily(TICKER, start, end)
        elapsed = time.monotonic() - t0

        assert elapsed < 5.0, f"request blocked {elapsed:.1f}s on background backfill"
        assert df.empty, "no data seeded yet — partial read must be empty, not fabricated"
        # The backfill is still running in the background…
        assert calls["n"] >= 1, "background backfill was not kicked"
        join_backfills(timeout=10)
        assert calls["n"] >= 2, "chunked backfill did not continue after the request returned"

    def test_partial_read_is_not_cached(self, monkeypatch):
        init_db()
        _dl, _calls = _slow_downloader(delay=1.0)
        monkeypatch.setattr("data_pipeline.ingest.ohlcv.upsert_raw_prices", _dl)
        monkeypatch.setattr("data_pipeline.transform.cleaning.clean_range", lambda *a, **k: PipelineResult(rows=1))
        monkeypatch.setattr(
            "data_pipeline.transform.processing.process_frequencies", lambda *a, **k: PipelineResult(rows=1)
        )

        start = dt.date(2021, 1, 1)
        end = dt.date.today()
        _q.get_cleaned_daily(TICKER, start, end)

        key = (TICKER, "clean", str(start), str(end))
        assert _cache_get(key) is None, "partial read must not be memoised"
        join_backfills(timeout=10)

    def test_completed_backfill_becomes_visible_and_cached(self, monkeypatch):
        """After the background backfill finishes, the next request returns the
        (mocked) cleaned data and this time it IS memoised."""
        init_db()

        def _fast_dl(ticker, start, end):  # noqa: ARG001
            return PipelineResult(rows=10)

        monkeypatch.setattr("data_pipeline.ingest.ohlcv.upsert_raw_prices", _fast_dl)
        monkeypatch.setattr("data_pipeline.transform.cleaning.clean_range", lambda *a, **k: PipelineResult(rows=1))
        monkeypatch.setattr(
            "data_pipeline.transform.processing.process_frequencies", lambda *a, **k: PipelineResult(rows=1)
        )
        monkeypatch.setattr(
            "data_pipeline.read._query.fetch_df",
            lambda sql, params: pd.DataFrame(
                {
                    "date": ["2026-01-05"],
                    "close": [100.0],
                    "open": [100.0],
                    "high": [100.0],
                    "low": [100.0],
                    "adj_close": [100.0],
                    "volume": [1_000_000],
                }
            ).set_index("date"),
        )

        start = dt.date(2026, 1, 1)
        end = dt.date(2026, 2, 1)
        df = _q.get_cleaned_daily(TICKER, start, end)
        join_backfills(timeout=10)
        assert not df.empty

        _cache_invalidate(TICKER)  # mimic ensure_range's post-success invalidation
        df2 = _q.get_cleaned_daily(TICKER, start, end)
        key = (TICKER, "clean", str(start), str(end))
        assert _cache_get(key) is not None, "complete read must be memoised"
        assert not df2.empty

    def test_needs_backfill_probe(self):
        init_db()
        start = dt.date(2021, 1, 1)
        end = dt.date.today()
        # Empty DB → backfill needed.
        assert _bf.needs_backfill(TICKER + "-PROBE", start, end) is True

    def test_kick_dedupes_concurrent_kicks(self, monkeypatch):
        init_db()
        _dl, calls = _slow_downloader(delay=0.3)
        monkeypatch.setattr("data_pipeline.ingest.ohlcv.upsert_raw_prices", _dl)
        monkeypatch.setattr("data_pipeline.transform.cleaning.clean_range", lambda *a, **k: PipelineResult(rows=1))
        monkeypatch.setattr(
            "data_pipeline.transform.processing.process_frequencies", lambda *a, **k: PipelineResult(rows=1)
        )

        start, end = dt.date(2021, 1, 1), dt.date.today()
        for _ in range(5):
            kick_backfill(TICKER + "-DEDUP", start, end)
        join_backfills(timeout=10)
        # ensure_range's own in-flight dedup collapses the kicked threads —
        # a single leader runs the chunked pipeline, not five. Chunks for a
        # 5.6-year range ≈ days/89, allow one boundary chunk.
        expected_chunks = (end - start).days // 89 + 2
        assert calls["n"] <= expected_chunks, (
            f"kicks were not deduped: {calls['n']} downloads > {expected_chunks} (single leader)"
        )

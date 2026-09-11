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


class TestFeatureBarsHeal:
    """Plan §10 F4: clean_bars present but feature_bars stale must self-heal
    (a reprocess, no download)."""

    @staticmethod
    def _seed_clean(ticker, start, end):
        from data_pipeline.store.db import upsert_many

        days = pd.bdate_range(start, end)
        rows = [
            (ticker, d.date().isoformat(), 100.0, 101.0, 99.0, 100.5, 100.5, 1_000_000, 1, 0, 0, 0, 0) for d in days
        ]
        upsert_many(
            "clean_bars",
            [
                "ticker",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "is_trading_day",
                "missing_any",
                "price_jump_flag",
                "vol_anom_flag",
                "ohlc_inconsistent",
            ],
            rows,
        )

    def test_needs_backfill_true_when_only_clean_exists(self):
        init_db()
        start, end = dt.date(2024, 1, 1), dt.date(2024, 6, 30)
        self._seed_clean("FEATHEAL1", start, end)
        assert _bf.needs_backfill("FEATHEAL1", start, end) is True

    def test_ensure_range_reprocesses_without_downloading(self, monkeypatch):
        from data_pipeline.store.db import fetch_df

        init_db()
        start, end = dt.date(2024, 1, 1), dt.date(2024, 6, 30)
        self._seed_clean("FEATHEAL2", start, end)

        downloads = {"n": 0}
        monkeypatch.setattr(
            "data_pipeline.ingest.ohlcv.upsert_raw_prices",
            lambda *a, **k: downloads.__setitem__("n", downloads["n"] + 1) or PipelineResult(rows=0),
        )

        _cache_invalidate("FEATHEAL2")
        assert _bf.ensure_range("FEATHEAL2", start, end) is True
        assert downloads["n"] == 0, "clean already covers the span — no download"

        feat = fetch_df("SELECT frequency, COUNT(*) AS n FROM feature_bars WHERE ticker='FEATHEAL2' GROUP BY frequency")
        assert not feat.empty, "feature_bars must be populated after the heal"
        assert _bf.needs_backfill("FEATHEAL2", start, end) is False


class TestGetClosePanel:
    """``get_close_panel`` — the ADR 0011 L5 replacement for the old
    ``market_review_prices`` ladder (batch B10)."""

    @pytest.fixture(autouse=True)
    def _no_incremental_update(self, monkeypatch):
        # The per-symbol freshness poke is not under test here and would hit
        # the network; every case exercises only the coverage/read path.
        monkeypatch.setattr("data_pipeline.orchestrate.update.manual_update", lambda *a, **k: False)

    @staticmethod
    def _seed_clean(ticker, start, end, base=100.0):
        from data_pipeline.store.db import upsert_many

        days = pd.bdate_range(start, end)
        rows = [
            (
                ticker,
                d.date().isoformat(),
                base,
                base + 1,
                base - 1,
                base + i * 0.1,
                base + i * 0.1,
                1_000_000,
                1,
                0,
                0,
                0,
                0,
            )
            for i, d in enumerate(days)
        ]
        upsert_many(
            "clean_bars",
            [
                "ticker",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "is_trading_day",
                "missing_any",
                "price_jump_flag",
                "vol_anom_flag",
                "ohlc_inconsistent",
            ],
            rows,
        )

    def test_reads_close_series_per_symbol_from_clean_bars(self, monkeypatch):
        init_db()
        start, end = dt.date(2024, 1, 1), dt.date(2024, 6, 28)
        self._seed_clean("PANELA", start, end, base=50.0)
        self._seed_clean("PANELB", start, end, base=200.0)
        # coverage already satisfied — the panel must not kick a backfill
        monkeypatch.setattr(_bf, "needs_backfill", lambda *a, **k: False)
        kicks = {"n": 0}
        monkeypatch.setattr(_q, "_kick_backfill", lambda *a, **k: kicks.__setitem__("n", kicks["n"] + 1))

        panel = _q.get_close_panel(["PANELA", "PANELB"], start, end)

        assert list(panel.columns) == ["PANELA", "PANELB"]
        assert not panel.empty
        assert kicks["n"] == 0
        assert panel["PANELA"].iloc[0] == 50.0
        assert panel["PANELB"].iloc[0] == 200.0

    def test_missing_symbols_are_kicked_once_and_awaited_together(self, monkeypatch):
        init_db()
        start, end = dt.date(2024, 1, 1), dt.date(2024, 6, 28)
        monkeypatch.setattr(_bf, "needs_backfill", lambda *a, **k: True)
        kicked: list[str] = []
        monkeypatch.setattr(_q, "_kick_backfill", lambda t, s, e: kicked.append(t))

        t0 = time.monotonic()
        panel = _q.get_close_panel(["MISS1", "MISS2", "MISS3"], start, end)
        elapsed = time.monotonic() - t0

        assert kicked == ["MISS1", "MISS2", "MISS3"], "one kick per symbol"
        # _fast_grace sets the wait to 0.5s; the wait is shared, not per-symbol
        assert elapsed < 1.2, f"grace window was not shared across symbols ({elapsed:.2f}s)"
        assert panel.empty

    def test_one_unavailable_symbol_does_not_sink_the_panel(self, monkeypatch):
        init_db()
        start, end = dt.date(2024, 1, 1), dt.date(2024, 6, 28)
        self._seed_clean("GOODSYM", start, end, base=75.0)
        monkeypatch.setattr(_bf, "needs_backfill", lambda t, *a, **k: t != "GOODSYM")
        monkeypatch.setattr(_q, "_kick_backfill", lambda *a, **k: None)

        panel = _q.get_close_panel(["GOODSYM", "NODATA"], start, end)

        assert list(panel.columns) == ["GOODSYM"]
        assert not panel.empty

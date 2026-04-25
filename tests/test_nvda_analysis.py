"""Test simulating frontend NVDA form submission and validating statistical analysis.

Covers:
- Full POST flow: form data → parse_tickers → MarketAnalyzer → charts
- features_df correctness with realistic data
- Graceful handling of NaN-only DB rows (yfinance failure scenario)
- Graceful handling of empty DB + failed download
"""

import datetime as dt
import re

import numpy as np
import pandas as pd
import pytest

from data_pipeline.db import get_conn, init_db


_JOB_ID_RE = re.compile(r'STREAMING_JOB_ID\s*=\s*"([^"]+)"')


def _extract_job_id(html: str) -> str:
    """Pull the streaming job id out of a rendered skeleton HTML page."""
    m = _JOB_ID_RE.search(html)
    return m.group(1) if m else ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_clean_prices(ticker: str, n_rows: int = 30, *, nan_only: bool = False):
    """Insert synthetic price rows into clean_prices.

    Wipes any previous rows for `ticker` first so the seeded distribution is
    deterministic regardless of test ordering, and invalidates the in-memory
    query cache so a stale DataFrame doesn't leak between tests.
    """
    init_db()
    # Drop the cross-test query cache that DataService maintains (TTL 60s).
    from data_pipeline.data_service import _cache_invalidate
    _cache_invalidate(ticker)
    dates = pd.bdate_range(end=dt.date.today(), periods=n_rows)
    np.random.seed(42)
    close = 120.0 + np.cumsum(np.random.randn(n_rows) * 0.5)
    with get_conn() as conn:
        conn.execute("DELETE FROM clean_prices WHERE ticker = ?", (ticker,))
        for i, d in enumerate(dates):
            date_str = d.strftime("%Y-%m-%d")
            if nan_only:
                conn.execute(
                    "INSERT OR REPLACE INTO clean_prices (ticker, date, is_trading_day, missing_any) VALUES (?,?,?,?)",
                    (ticker, date_str, 0, 1),
                )
            else:
                c = float(close[i])
                conn.execute(
                    "INSERT OR REPLACE INTO clean_prices "
                    "(ticker, date, open, high, low, close, adj_close, volume) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (ticker, date_str, c - 0.5, c + 1.0, c - 1.0, c, c, 1_000_000),
                )
        conn.commit()


@pytest.fixture()
def _patch_downloads(monkeypatch):
    """Disable real yfinance downloads and DataService.manual_update."""
    from core.price_dynamic import PriceDynamic
    from data_pipeline.data_service import DataService

    monkeypatch.setattr(DataService, "manual_update", staticmethod(lambda *a, **kw: None))
    monkeypatch.setattr(PriceDynamic, "_download_data", lambda self: None)


# ---------------------------------------------------------------------------
# Unit-level: PriceDynamic + MarketAnalyzer
# ---------------------------------------------------------------------------


class TestFeaturesDF:
    """Verify features_df is correct across data availability scenarios."""

    def test_good_data_produces_nonempty_features(self, _patch_downloads):
        """With 30 rows of price data, features_df should have ~29 rows."""
        _seed_clean_prices("NVDA", 30)
        from core.market_analyzer import MarketAnalyzer

        analyzer = MarketAnalyzer("NVDA", dt.date(2026, 1, 1), "D")
        assert analyzer.is_data_valid()
        assert analyzer.features_df.shape[0] >= 20
        assert set(analyzer.features_df.columns) == {"Oscillation", "Osc_high", "Osc_low", "Returns", "Difference"}

    def test_nan_only_filler_rows_produce_empty_features(self, _patch_downloads):
        """NaN-only filler rows from clean_range should not fool is_valid."""
        _seed_clean_prices("NVDA", 5, nan_only=True)
        from core.market_analyzer import MarketAnalyzer

        analyzer = MarketAnalyzer("NVDA", dt.date(2026, 1, 1), "D")
        assert not analyzer.is_data_valid()
        assert analyzer.features_df.empty

    def test_empty_db_no_download(self, _patch_downloads):
        """Empty DB + failed download → proper error, no crash."""
        init_db()
        from core.market_analyzer import MarketAnalyzer

        analyzer = MarketAnalyzer("NVDA", dt.date(2026, 1, 1), "D")
        assert not analyzer.is_data_valid()
        assert analyzer.features_df.empty

    def test_mixed_real_and_nan_rows(self, _patch_downloads):
        """Mix of real and NaN rows — only real rows used for features."""
        init_db()
        dates = pd.bdate_range(end=dt.date.today(), periods=10)
        np.random.seed(42)
        close = 120.0 + np.cumsum(np.random.randn(10) * 0.5)
        with get_conn() as conn:
            for i, d in enumerate(dates):
                date_str = d.strftime("%Y-%m-%d")
                if i < 7:  # 7 real rows
                    c = float(close[i])
                    conn.execute(
                        "INSERT OR REPLACE INTO clean_prices "
                        "(ticker, date, open, high, low, close, adj_close, volume) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        ("NVDA", date_str, c - 0.5, c + 1.0, c - 1.0, c, c, 1_000_000),
                    )
                else:  # 3 NaN filler rows
                    conn.execute(
                        "INSERT OR REPLACE INTO clean_prices "
                        "(ticker, date, is_trading_day, missing_any) VALUES (?,?,?,?)",
                        ("NVDA", date_str, 0, 1),
                    )
            conn.commit()

        from core.market_analyzer import MarketAnalyzer

        analyzer = MarketAnalyzer("NVDA", dt.date(2026, 1, 1), "D")
        assert analyzer.is_data_valid()
        # 7 real rows → shift(1) eats 1 → 6 feature rows
        assert analyzer.features_df.shape[0] == 6

    def test_single_row_produces_empty_features(self, _patch_downloads):
        """Only 1 row of data → shift(1) creates NaN → no valid features."""
        _seed_clean_prices("NVDA", 1)
        from core.market_analyzer import MarketAnalyzer

        analyzer = MarketAnalyzer("NVDA", dt.date(2026, 1, 1), "D")
        # 1 row is valid data, but after shift(1) → 0 feature rows
        assert analyzer.features_df.shape[0] == 0

    def test_futu_format_ticker_normalized(self, _patch_downloads):
        """PriceDynamic normalizes US.NVDA → NVDA for DB lookup."""
        _seed_clean_prices("NVDA", 10)
        from core.price_dynamic import PriceDynamic

        pd_obj = PriceDynamic("US.NVDA", dt.date(2026, 1, 1), "D")
        assert pd_obj.ticker == "NVDA"
        assert pd_obj.is_valid()


# ---------------------------------------------------------------------------
# Integration: Flask POST simulating frontend "Run" click
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(_patch_downloads):
    """Create Flask test client with isolated DB."""
    import app as flask_app
    from data_pipeline import data_service as _ds
    from data_pipeline import job_cache as _jc

    # Reset module-level caches so prior tests don't leak data into this one.
    _jc._reset()
    with _ds._query_cache_lock:
        _ds._query_cache.clear()

    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c
    _jc._reset()
    with _ds._query_cache_lock:
        _ds._query_cache.clear()


class TestFlaskAnalysisPost:
    """Simulate entering NVDA and clicking Run."""

    def test_nvda_post_returns_charts(self, client):
        """POST returns a skeleton; GET /render/statistical produces charts."""
        _seed_clean_prices("NVDA", 60)

        resp = client.post(
            "/",
            data={
                "ticker": "NVDA",
                "frequency": "D",
                "start_time": "202501",
                "end_time": "",
                "risk_threshold": "90",
                "rolling_window": "120",
                "side_bias": "Neutral",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        # POST now returns a skeleton with HTMX render hooks.
        assert "/render/statistical" in html
        job_id = _extract_job_id(html)
        assert job_id
        # Drive the streaming render to validate the chart payload.
        sub = client.get(f"/render/statistical?job={job_id}&ticker=NVDA")
        assert sub.status_code == 200
        sub_html = sub.data.decode("utf-8")
        assert "data:image/png;base64," in sub_html
        assert "features_df shape: (0," not in sub_html

    def test_nvda_post_futu_format_works(self, client):
        """POST with US.NVDA (futu format) should also work end-to-end."""
        _seed_clean_prices("NVDA", 60)

        resp = client.post(
            "/",
            data={
                "ticker": "US.NVDA",
                "frequency": "D",
                "start_time": "202501",
                "end_time": "",
                "risk_threshold": "90",
                "rolling_window": "120",
                "side_bias": "Neutral",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "/render/statistical" in html
        job_id = _extract_job_id(html)
        assert job_id
        # Ticker is normalised in the slice, so request the normalised form.
        sub = client.get(f"/render/statistical?job={job_id}&ticker=NVDA")
        assert sub.status_code == 200
        assert "data:image/png;base64," in sub.data.decode("utf-8")

    def test_failed_download_shows_error(self, client):
        """Empty DB + no download should surface a meaningful error in the
        streaming render fragment, not blank charts."""
        init_db()
        resp = client.post(
            "/",
            data={
                "ticker": "NVDA",
                "frequency": "D",
                "start_time": "202501",
                "end_time": "",
                "risk_threshold": "90",
                "rolling_window": "120",
                "side_bias": "Neutral",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        job_id = _extract_job_id(html)
        assert job_id
        sub = client.get(f"/render/statistical?job={job_id}&ticker=NVDA")
        sub_html = sub.data.decode("utf-8")
        # The streaming fragment surfaces the failure either as an explicit
        # error banner or as the "insufficient data" empty-state.
        assert (
            "Failed to download data" in sub_html
            or "insufficient data" in sub_html.lower()
            or "error" in sub_html.lower()
        )

    def test_nan_only_db_shows_error(self, client):
        """DB with NaN-only rows should produce an error fragment from
        /render/statistical, not blank charts."""
        _seed_clean_prices("NVDA", 5, nan_only=True)
        resp = client.post(
            "/",
            data={
                "ticker": "NVDA",
                "frequency": "D",
                "start_time": "202501",
                "end_time": "",
                "risk_threshold": "90",
                "rolling_window": "120",
                "side_bias": "Neutral",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        job_id = _extract_job_id(html)
        assert job_id
        sub = client.get(f"/render/statistical?job={job_id}&ticker=NVDA")
        sub_html = sub.data.decode("utf-8")
        assert (
            "Failed to download data" in sub_html
            or "insufficient data" in sub_html.lower()
            or "error" in sub_html.lower()
        )

    def test_analysis_service_direct(self, _patch_downloads):
        """Direct AnalysisService call with good data produces charts."""
        _seed_clean_prices("NVDA", 60)
        from services.analysis_service import AnalysisService

        form_data = {
            "ticker": "NVDA",
            "parsed_tickers": ["NVDA"],
            "frequency": "D",
            "parsed_start_time": dt.date(2025, 1, 1),
            "parsed_end_time": None,
            "risk_threshold": 90,
            "rolling_window": 120,
            "side_bias": "Neutral",
            "target_bias": "Neutral",
        }
        result = AnalysisService.generate_complete_analysis(form_data)
        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        # At least one chart should be non-None
        chart_keys = [
            "feat_ret_scatter_top_url",
            "high_low_scatter_url",
            "return_osc_high_low_url",
            "volatility_dynamic_url",
        ]
        charts_present = [k for k in chart_keys if result.get(k)]
        assert len(charts_present) >= 1, f"Expected at least 1 chart, got {charts_present}"

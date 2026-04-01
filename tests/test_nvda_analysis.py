"""Test simulating frontend NVDA form submission and validating statistical analysis.

Covers:
- Full POST flow: form data → parse_tickers → MarketAnalyzer → charts
- features_df correctness with realistic data
- Graceful handling of NaN-only DB rows (yfinance failure scenario)
- Graceful handling of empty DB + failed download
"""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from data_pipeline.db import get_conn, init_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_clean_prices(ticker: str, n_rows: int = 30, *, nan_only: bool = False):
    """Insert synthetic price rows into clean_prices."""
    init_db()
    dates = pd.bdate_range(end=dt.date.today(), periods=n_rows)
    np.random.seed(42)
    close = 120.0 + np.cumsum(np.random.randn(n_rows) * 0.5)
    with get_conn() as conn:
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

    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


class TestFlaskAnalysisPost:
    """Simulate entering NVDA and clicking Run."""

    def test_nvda_post_returns_charts(self, client):
        """POST with NVDA ticker should produce statistical analysis charts."""
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
        # Should contain at least one base64-encoded chart image
        assert "data:image/png;base64," in html, "Expected base64 chart image in response HTML"
        # Should NOT contain the empty features_df error
        assert "features_df shape: (0," not in html

    def test_nvda_post_futu_format_works(self, client):
        """POST with US.NVDA (futu format) should also work."""
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
        assert "data:image/png;base64," in html

    def test_failed_download_shows_error(self, client):
        """Empty DB + no download should show meaningful error, not blank charts."""
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
        # Should show an error message about failed download
        assert "Failed to download data" in html or "error" in html.lower()

    def test_nan_only_db_shows_error(self, client):
        """DB with NaN-only rows should show error, not blank charts."""
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
        assert "Failed to download data" in html

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

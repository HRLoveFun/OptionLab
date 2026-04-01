"""Diagnostic test: fetch last-year daily data for NVDA via yfinance.

Run standalone:
    python -m pytest tests/test_yf_download.py -v -s

The test checks network connectivity first, then attempts the download.
If the proxy (YF_PROXY) is configured but unreachable, it is bypassed.
If Yahoo is rate-limiting, the test is skipped rather than failing.
"""

import datetime as dt
import logging
import os
import socket

import pandas as pd
import pytest
import yfinance as yf

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _proxy_reachable(url: str, timeout: float = 2.0) -> bool:
    """TCP probe for the proxy endpoint."""
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        with socket.create_connection((p.hostname, p.port or 1080), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def _ensure_clean_proxy_env():
    """If YF_PROXY is set but the proxy is down, remove HTTP(S)_PROXY so
    curl_cffi falls back to a direct connection instead of hanging."""
    proxy = os.environ.get("YF_PROXY")
    if proxy and not _proxy_reachable(proxy):
        logger.warning("YF_PROXY=%s unreachable — clearing proxy env vars", proxy)
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ.pop(k, None)


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "rate" in msg or "too many" in msg or "429" in msg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_proxy():
    """Ensure proxy env is sane before every test in this module."""
    from dotenv import load_dotenv
    load_dotenv()
    from utils.utils import init_yf_proxy
    init_yf_proxy()
    _ensure_clean_proxy_env()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestYFinanceDownload:
    """Download NVDA daily data for the last year."""

    TICKER = "NVDA"
    PERIOD_DAYS = 365

    def test_download_nvda_last_year(self):
        """Fetch ~1 year of NVDA daily bars via yf.download."""
        end = dt.date.today()
        start = end - dt.timedelta(days=self.PERIOD_DAYS)

        try:
            df = yf.download(
                self.TICKER,
                start=start,
                end=end + dt.timedelta(days=1),
                interval="1d",
                progress=False,
                auto_adjust=False,
            )
        except Exception as exc:
            if _is_rate_limited(exc):
                pytest.skip(f"Yahoo rate-limited: {exc}")
            raise

        if df is None or df.empty:
            pytest.skip("yfinance returned empty data — likely rate-limited or blocked")

        # Flatten MultiIndex columns that yfinance sometimes returns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # ── Assertions ────────────────────────────────────────────
        required = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
        assert required.issubset(set(df.columns)), f"Missing columns: {required - set(df.columns)}"

        # At least 200 trading days in a year
        assert len(df) >= 200, f"Only {len(df)} rows — expected ≥200 trading days"

        # Date range sanity
        first = df.index[0].date() if hasattr(df.index[0], "date") else df.index[0]
        last = df.index[-1].date() if hasattr(df.index[-1], "date") else df.index[-1]
        assert first >= start - dt.timedelta(days=5), f"First date {first} is too far before {start}"
        assert last <= end + dt.timedelta(days=1), f"Last date {last} is after {end}"

        # No all-NaN rows
        ohlc = df[["Open", "High", "Low", "Close"]]
        all_nan_rows = ohlc.isna().all(axis=1).sum()
        assert all_nan_rows == 0, f"{all_nan_rows} rows are entirely NaN"

        logger.info("Downloaded %d rows for %s from %s to %s", len(df), self.TICKER, first, last)

    def test_download_handles_rate_limit_gracefully(self):
        """Verify that a rate-limit error doesn't crash — returns empty or raises identifiable error."""
        try:
            df = yf.download(
                self.TICKER,
                period="5d",
                progress=False,
                auto_adjust=False,
            )
            # If we got data, the test passes (no rate limit right now)
            if df is not None and not df.empty:
                assert len(df) > 0
                return
            # Empty is also acceptable (rate limited but no exception)
        except Exception as exc:
            assert _is_rate_limited(exc), f"Unexpected non-rate-limit error: {exc}"
            return

        # If we reach here, download returned empty — acceptable under rate limiting

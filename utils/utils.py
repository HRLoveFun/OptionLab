"""Unified utility module for market analysis application"""

import datetime as dt
import logging
import os
import threading as _threading

import pandas as pd

DEFAULT_RISK_THRESHOLD = 90
DEFAULT_ROLLING_WINDOW = 120
DEFAULT_FREQUENCY = "ME"
DEFAULT_TICKER = "^SPX"
DEFAULT_SIDE_BIAS = "Neutral"
DEFAULT_PERIODS = [12, 36, 60, "ALL"]

FREQUENCY_DISPLAY = {"D": "Daily", "W": "Weekly", "ME": "Monthly", "QE": "Quarterly"}


def parse_month_str(value: str) -> dt.date | None:
    """Parse a YYYYMM or YYYY-MM string into a date (first of month)."""
    if not value:
        return None
    for fmt in ("%Y%m", "%Y-%m"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def exclusive_month_end(month_date: dt.date | None) -> dt.date | None:
    """Return the first day of the next month for horizon end handling."""
    if month_date is None:
        return None
    year = month_date.year + (1 if month_date.month == 12 else 0)
    month = 1 if month_date.month == 12 else month_date.month + 1
    return dt.date(year, month, 1)


class DateHelper:
    @staticmethod
    def parse_date_string(date_str, format_str="%Y%m"):
        try:
            return dt.datetime.strptime(date_str, format_str).date()
        except ValueError:
            return None


# ── yfinance proxy ────────────────────────────────────────────────
# yfinance uses curl_cffi internally, which respects standard
# HTTP_PROXY / HTTPS_PROXY env vars.  We map the simpler YF_PROXY
# variable into both so the user only has to set one value.


def _probe_proxy(proxy_url: str, timeout: float = 2.0) -> bool:
    """Return True if the proxy is reachable (TCP connect)."""
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(proxy_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 1080
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def init_yf_proxy() -> None:
    """Propagate ``YF_PROXY`` to ``HTTP_PROXY``/``HTTPS_PROXY``.

    Call once at startup (e.g. in ``app.py``).  Common values::

        export YF_PROXY=http://127.0.0.1:7890      # Clash / V2Ray
        export YF_PROXY=socks5h://127.0.0.1:1080    # SOCKS5

    The proxy is only activated if it is actually reachable; otherwise
    the app falls back to a direct connection.
    """
    proxy = os.environ.get("YF_PROXY")
    if proxy:
        if _probe_proxy(proxy):
            os.environ.setdefault("HTTP_PROXY", proxy)
            os.environ.setdefault("HTTPS_PROXY", proxy)
            logging.getLogger(__name__).info("YF_PROXY active: %s", proxy)
        else:
            logging.getLogger(__name__).warning(
                "YF_PROXY=%s is not reachable — falling back to direct connection", proxy
            )


# ── yfinance global rate throttle ──────────────────────────────────
# Token-bucket limiter: refills at YF_RATE_PER_SEC tokens/second up to a
# burst capacity of YF_BUCKET_SIZE. Each `yf_throttle()` consumes one token,
# blocking only when the bucket is empty. This replaces the older fixed
# 1.5s gap so a small burst (e.g. 5 parallel requests) completes quickly
# while sustained traffic still respects Yahoo's per-IP limits.

_yf_throttle_lock = _threading.Lock()
_YF_RATE_PER_SEC = float(os.environ.get("YF_RATE_PER_SEC", "5.0"))
_YF_BUCKET_SIZE = float(os.environ.get("YF_BUCKET_SIZE", "5.0"))
_yf_tokens: float = _YF_BUCKET_SIZE
_yf_last_refill: float = 0.0


def yf_throttle() -> None:
    """Block until a token is available, then consume one.

    Tokens regenerate at ``YF_RATE_PER_SEC`` (default 5/s) up to a burst
    capacity of ``YF_BUCKET_SIZE`` (default 5). Call this immediately
    before every ``yf.download()`` / ``yf.Ticker()`` invocation.
    """
    import time as _time

    global _yf_tokens, _yf_last_refill
    while True:
        with _yf_throttle_lock:
            now = _time.monotonic()
            if _yf_last_refill == 0.0:
                _yf_last_refill = now
            elapsed = now - _yf_last_refill
            if elapsed > 0:
                _yf_tokens = min(_YF_BUCKET_SIZE, _yf_tokens + elapsed * _YF_RATE_PER_SEC)
                _yf_last_refill = now
            if _yf_tokens >= 1.0:
                _yf_tokens -= 1.0
                return
            # Compute exact wait outside the lock so other waiters can also
            # observe the refilled bucket once their slot frees up.
            deficit = 1.0 - _yf_tokens
            wait = deficit / _YF_RATE_PER_SEC if _YF_RATE_PER_SEC > 0 else 0.2
        _time.sleep(max(0.001, wait))


def _yf_throttle_reset() -> None:
    """Test helper: reset the bucket to full. Not part of the public API."""
    global _yf_tokens, _yf_last_refill
    with _yf_throttle_lock:
        _yf_tokens = _YF_BUCKET_SIZE
        _yf_last_refill = 0.0


class DataFormatter:
    @staticmethod
    def format_percentage(value, decimal_places=2):
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}%}"

    @staticmethod
    def format_currency(value, decimal_places=2):
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}f}"

    @staticmethod
    def format_number(value, decimal_places=2):
        if pd.isna(value) or not isinstance(value, (int, float)):
            return "N/A"
        return f"{value:.{decimal_places}f}"

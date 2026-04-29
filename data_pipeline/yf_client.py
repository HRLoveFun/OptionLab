"""
Unified yfinance access layer.

Context:
- All direct yfinance calls (`yf.Ticker`, `yf.download`, `option_chain`,
  `fast_info`) for live snapshot data go through this module. OHLCV historical
  bulk downloads remain in ``downloader.py`` (which has DB-aware gap detection).
- Yahoo Finance has no SLA: rate limits, transient 5xx, and silently empty
  payloads are routine. See docs/constraints.md §2 and ADR 0002 / 0005.

Design rules:
- CONSTRAINT: every public function MUST call ``yf_throttle()`` before each
  yfinance call. See docs/decisions/0005-token-bucket-throttle.md.
- WHY (no caching here): caching is the caller's concern (e.g.
  ``app._option_chain_cache``, ``data_service`` 60s freshness window).
- WHY (never raise on transient failure): callers receive ``None`` / empty
  dict and decide how to surface the error. Raising here would cascade into
  unhandled 500s from many different routes.
- INVARIANT: returns plain Python types (float / dict / DataFrame), never
  yfinance-specific objects — keeps the rest of the pipeline mockable.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import yfinance as yf

from utils.utils import yf_throttle

logger = logging.getLogger(__name__)


def _log_dq(source: str, error_class: str, message: str, *, ticker: str | None = None) -> None:
    """Best-effort write to ``data_quality_log``. Never raises."""
    try:
        from data_pipeline.quality_log import log_failure

        log_failure(source, error_class, message, ticker=ticker)
    except Exception:  # noqa: BLE001
        pass

# Standard option-chain numeric columns we always coerce.
_OPT_NUMERIC_COLS = (
    "strike",
    "bid",
    "ask",
    "lastPrice",
    "impliedVolatility",
    "openInterest",
    "volume",
)


# ---------------------------------------------------------------------------
# Spot price
# ---------------------------------------------------------------------------
def fetch_spot(ticker: str) -> float | None:
    """Return the current spot price for ``ticker`` or ``None`` on failure.

    Tries ``fast_info.last_price`` then ``regularMarketPrice`` then a tiny
    history fallback (1d) so we always have *something* for tickers whose
    fast_info is flaky.
    """
    try:
        yf_throttle()
        tk = yf.Ticker(ticker)
        fi = tk.fast_info
        price = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
        if price is not None:
            return float(price)
    except Exception as exc:  # noqa: BLE001 — yfinance raises a wide variety
        logger.debug("fetch_spot fast_info failed for %s: %s", ticker, exc)

    try:
        yf_throttle()
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_spot history fallback failed for %s: %s", ticker, exc)
        _log_dq("yf_client.fetch_spot", "spot_unavailable", str(exc), ticker=ticker)
    return None


def fetch_spots_bulk(tickers: list[str]) -> dict[str, float]:
    """Return ``{ticker: spot}`` for every ticker that resolved successfully.

    Sequential (one yfinance call per ticker) — the global token bucket in
    ``yf_throttle`` already paces us. Failures are logged and omitted from
    the result; callers must handle missing keys.
    """
    out: dict[str, float] = {}
    for t in tickers:
        spot = fetch_spot(t)
        if spot is not None:
            out[t] = spot
    return out


# ---------------------------------------------------------------------------
# Option chain
# ---------------------------------------------------------------------------
def fetch_option_chain(ticker: str) -> dict[str, Any]:
    """Fetch a full option-chain snapshot.

    Returns
    -------
    dict
        Shape::

            {
                "ticker": str,
                "spot": float | None,
                "expiries": list[str],          # YYYY-MM-DD strings
                "chain": {
                    expiry_str: {
                        "calls": pd.DataFrame,
                        "puts":  pd.DataFrame,
                    }
                }
            }

        Numeric columns on the DataFrames are coerced via ``pd.to_numeric``.
        ``openInterest`` / ``volume`` NaNs are filled with 0.

        On total failure (no expiries returned), ``expiries`` and ``chain``
        are empty but ``spot`` may still be populated.
    """
    spot = fetch_spot(ticker)
    expiries: list[str] = []
    chain: dict[str, dict[str, pd.DataFrame]] = {}

    try:
        yf_throttle()
        tk = yf.Ticker(ticker)
        expiries = list(tk.options or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_option_chain: failed to list expiries for %s: %s", ticker, exc)
        _log_dq("yf_client.fetch_option_chain", "expiries_unavailable", str(exc), ticker=ticker)
        return {"ticker": ticker, "spot": spot, "expiries": [], "chain": {}}

    # WHY: track consecutive empty responses. Yahoo's 429 / curl_cffi's
    # empty-body behaviour applies to the WHOLE option-chain endpoint
    # uniformly — once one expiry returns None, the rest will too. Bail
    # after a few empties to avoid burning the throttle on guaranteed misses.
    consecutive_empty = 0
    EMPTY_FAIL_FAST = 3

    for exp in expiries:
        try:
            yf_throttle()
            opt = tk.option_chain(exp)
            # WHY: yfinance returns the namedtuple but with .calls/.puts == None
            # when rate-limited or when the upstream HTTP body is empty. Treat
            # this as a soft-skip rather than a hard error.
            if opt is None or opt.calls is None or opt.puts is None:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    logger.warning(
                        "fetch_option_chain: %s exp=%s returned no data (rate-limited?)", ticker, exp
                    )
                if consecutive_empty >= EMPTY_FAIL_FAST:
                    logger.warning(
                        "fetch_option_chain: %s aborting after %d empty expiries (likely rate-limited)",
                        ticker, consecutive_empty,
                    )
                    break
                continue
            consecutive_empty = 0
            calls = opt.calls.copy()
            puts = opt.puts.copy()
            for col in _OPT_NUMERIC_COLS:
                if col in calls.columns:
                    calls[col] = pd.to_numeric(calls[col], errors="coerce")
                if col in puts.columns:
                    puts[col] = pd.to_numeric(puts[col], errors="coerce")
            for col in ("openInterest", "volume"):
                if col in calls.columns:
                    calls[col] = calls[col].fillna(0)
                if col in puts.columns:
                    puts[col] = puts[col].fillna(0)
            chain[exp] = {"calls": calls, "puts": puts}
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_option_chain: %s exp=%s failed: %s", ticker, exp, exc)
            continue

    return {"ticker": ticker, "spot": spot, "expiries": list(chain.keys()), "chain": chain}


# ---------------------------------------------------------------------------
# Close-only panel (used by correlation matrix)
# ---------------------------------------------------------------------------
def fetch_close_panel(tickers: list[str], period: str = "90d") -> pd.DataFrame:
    """Return a wide DataFrame of Close prices for ``tickers`` over ``period``.

    On failure returns an empty DataFrame. One yfinance call total (yfinance
    natively supports multi-ticker download).
    """
    if not tickers:
        return pd.DataFrame()
    try:
        yf_throttle()
        data = yf.download(tickers, period=period, auto_adjust=False, progress=False)
        if data is None or data.empty:
            return pd.DataFrame()
        if "Close" in data.columns.get_level_values(0) if isinstance(data.columns, pd.MultiIndex) else data.columns:
            close = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]
        else:
            return pd.DataFrame()
        if isinstance(close.columns, pd.MultiIndex):
            close.columns = close.columns.droplevel(1)
        return close
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_close_panel failed for %s: %s", tickers, exc)
        _log_dq("yf_client.fetch_close_panel", "download_error", str(exc), ticker=",".join(tickers))
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Daily OHLCV (for core/price_dynamic.py)
# ---------------------------------------------------------------------------
def fetch_daily_ohlcv(
    ticker: str,
    start,
    end,
    *,
    auto_adjust: bool = False,
    max_retries: int = 2,
    retry_base_delay: float = 3.0,
) -> pd.DataFrame:
    """Download daily OHLCV bars for ``ticker`` in ``[start, end)``.

    Returns a DataFrame indexed by Date with columns
    ``[Open, High, Low, Close, Adj Close, Volume]``. Empty DataFrame on
    failure. Includes simple retry loop for transient empty responses.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            yf_throttle()
            df = yf.download(
                ticker,
                start=start,
                end=end,
                interval="1d",
                progress=False,
                auto_adjust=auto_adjust,
            )
            if df is None or df.empty:
                if attempt < max_retries - 1:
                    time.sleep(retry_base_delay * (attempt + 1))
                    continue
                return pd.DataFrame()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.index = pd.DatetimeIndex(df.index)
            return df
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            is_rate_limit = "rate" in str(exc).lower() or "too many" in str(exc).lower()
            if is_rate_limit and attempt < max_retries - 1:
                time.sleep(retry_base_delay * (attempt + 1))
                continue
            break
    if last_err is not None:
        logger.warning("fetch_daily_ohlcv failed for %s: %s", ticker, last_err)
        is_rate_limit = "rate" in str(last_err).lower() or "too many" in str(last_err).lower()
        _log_dq(
            "yf_client.fetch_daily_ohlcv",
            "rate_limited" if is_rate_limit else "download_error",
            str(last_err),
            ticker=ticker,
        )
    return pd.DataFrame()

"""Market review data fetching.

Domain:    Market Review — Data Fetching
Context:
  - L1 in-memory cache (5-min TTL)
  - L2 SQLite market_review_prices table
  - L3 yfinance incremental download
Contracts:
  - fetch_market_data(instrument, start_date, end_date) -> tuple[pd.DataFrame, pd.DataFrame, list]
Dependencies UPWARD:
  - data_pipeline.yf_client, data_pipeline.db
Dependencies DOWNWARD:
  - core.market_review.compute, core.market_review.timeseries
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time

import pandas as pd

from data_pipeline.yf_client import fetch_close_panel
from utils.data_utils import calculate_recent_extreme_change

logger = logging.getLogger(__name__)

_mr_cache: dict = {}
_mr_cache_lock = threading.Lock()

# CONSTRAINT: prevents stale market-review data from being served indefinitely after market moves.
_MR_CACHE_TTL = 300

BENCHMARKS = {
    "USD": "DX-Y.NYB", "US10Y": "^TNX", "Gold": "GC=F",
    "SPX": "^SPX", "CSI300": "000300.SS", "HSI": "^HSI",
    "NKY": "^N225", "STOXX": "^STOXX",
}


def _canonicalize_instrument(instrument: str) -> str:
    inverse = {v: k for k, v in BENCHMARKS.items()}
    return inverse.get(instrument, instrument)


def fetch_market_data(instrument: str, start_date=None, end_date=None):
    cache_key = (instrument, str(start_date), str(end_date))
    with _mr_cache_lock:
        if cache_key in _mr_cache:
            ts, cached_data, cached_returns, cached_display = _mr_cache[cache_key]
            if time.monotonic() - ts < _MR_CACHE_TTL:
                return cached_data.copy(), cached_returns.copy(), list(cached_display)
            del _mr_cache[cache_key]

    _benchmark_inverse = {v: k for k, v in BENCHMARKS.items()}
    if instrument in _benchmark_inverse:
        all_tickers = list(BENCHMARKS.values())
        display_names = list(BENCHMARKS.keys())
    else:
        all_tickers = [instrument] + list(BENCHMARKS.values())
        display_names = [instrument] + list(BENCHMARKS.keys())
    ticker_to_display = dict(zip(all_tickers, display_names, strict=False))

    from data_pipeline.db import get_conn, init_db
    init_db()
    today_str = dt.date.today().isoformat()
    range_start = start_date.isoformat() if isinstance(start_date, dt.date) else (dt.date.today() - dt.timedelta(days=400)).isoformat()

    tickers_needing_download = []
    with get_conn() as conn:
        for t in all_tickers:
            row = conn.execute("SELECT MAX(date) FROM market_review_prices WHERE ticker = ?", (t,)).fetchone()
            latest = row[0] if row and row[0] else None
            if latest is None or latest < today_str:
                tickers_needing_download.append(t)

    if tickers_needing_download:
        try:
            download_start = range_start
            with get_conn() as conn:
                for t in tickers_needing_download:
                    row = conn.execute("SELECT MAX(date) FROM market_review_prices WHERE ticker = ?", (t,)).fetchone()
                    latest = row[0] if row and row[0] else None
                    if latest is None:
                        download_start = range_start
                        break
                    elif latest < download_start:
                        download_start = latest
            close_data = fetch_close_panel(tickers_needing_download, start=download_start, end=today_str)
            if not close_data.empty:
                rows = []
                for t in tickers_needing_download:
                    if t in close_data.columns:
                        series = close_data[t].dropna()
                        for date_idx, val in series.items():
                            rows.append((t, date_idx.strftime("%Y-%m-%d"), float(val)))
                if rows:
                    with get_conn() as conn:
                        conn.executemany(
                            "INSERT INTO market_review_prices (ticker, date, close) "
                            "VALUES (?, ?, ?) ON CONFLICT(ticker, date) DO UPDATE SET close=excluded.close",
                            rows,
                        )
                        conn.commit()
        except Exception as e:
            logger.warning("Market review yfinance download failed: %s", e)

    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT ticker, date, close FROM market_review_prices WHERE date >= ? ORDER BY date",
            conn, params=(range_start,), parse_dates=["date"],
        )
    if df.empty:
        logger.warning("No market review data in DB, falling back to yfinance")
        raw = fetch_close_panel(all_tickers, period="400d")
        data = raw.ffill() if raw is not None and not raw.empty else pd.DataFrame()
    else:
        data = df.pivot(index="date", columns="ticker", values="close").sort_index().ffill()

    valid_tickers = [t for t in all_tickers if t in data.columns and data[t].notna().any()]
    if instrument not in valid_tickers:
        raise ValueError("No data downloaded - check ticker symbols")
    data = data[valid_tickers].dropna()
    valid_display = [ticker_to_display[t] for t in valid_tickers]
    data.columns = valid_display
    returns = data.pct_change(fill_method=None).dropna()
    with _mr_cache_lock:
        _mr_cache[cache_key] = (time.monotonic(), data.copy(), returns.copy(), list(valid_display))
    return data, returns, valid_display

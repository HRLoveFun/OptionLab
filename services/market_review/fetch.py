"""Market review data fetching — panel assembly over the provider seam.

Domain:    Market Review — Data Fetching
Context:
  - L1 in-memory cache (5-min TTL) over the assembled (data, returns, display)
    triple.
  - The close-price panel itself comes from ``DataService.get_close_panel``,
    which reads ``clean_bars`` and heals coverage through the same
    ``ensure_range`` machinery every other read uses (ADR 0011, L5). Batch B10
    removed the old ``market_review_prices`` ladder (its own L2 table + a
    parallel yfinance download) so benchmark symbols now flow through the
    provider seam like any other ticker and the submit-time readiness pass can
    prefetch them.

Contracts:
  - fetch_market_data(instrument, start_date, end_date) -> tuple[pd.DataFrame, pd.DataFrame, list]
Dependencies:
  - data_pipeline.read.facade.DataService
  - core.market_review.constants (BENCHMARKS)
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time

import pandas as pd

from core.market_review.constants import BENCHMARKS
from data_pipeline.read.facade import DataService

logger = logging.getLogger(__name__)

_mr_cache: dict = {}
_mr_cache_lock = threading.Lock()

# CONSTRAINT: prevents stale market-review data from being served indefinitely after market moves.
_MR_CACHE_TTL = 300

# Bound on distinct cache keys (each holds a full multi-ticker price panel).
_MR_CACHE_MAX = 64

# DOMAIN: default lookback when the caller passes no explicit start date.
_DEFAULT_LOOKBACK_DAYS = 400


def fetch_market_data(instrument: str, start_date=None, end_date=None):
    cache_key = (instrument, str(start_date), str(end_date))
    with _mr_cache_lock:
        if cache_key in _mr_cache:
            ts, cached_data, cached_returns, cached_display = _mr_cache[cache_key]
            if time.monotonic() - ts < _MR_CACHE_TTL:
                return cached_data.copy(), cached_returns.copy(), list(cached_display)
            del _mr_cache[cache_key]
        # Bound growth: expired entries are only dropped on re-read of the same
        # key, so unrevisited (instrument, start, end) combinations would
        # otherwise accumulate forever. Shed to make room for this compute's
        # eventual insert.
        if len(_mr_cache) >= _MR_CACHE_MAX:
            now_ts = time.monotonic()
            for k in [k for k, v in _mr_cache.items() if (now_ts - v[0]) >= _MR_CACHE_TTL]:
                del _mr_cache[k]
            while len(_mr_cache) >= _MR_CACHE_MAX:
                oldest = min(_mr_cache, key=lambda k: _mr_cache[k][0])
                del _mr_cache[oldest]

    _benchmark_inverse = {v: k for k, v in BENCHMARKS.items()}
    if instrument in _benchmark_inverse:
        all_tickers = list(BENCHMARKS.values())
        display_names = list(BENCHMARKS.keys())
    else:
        all_tickers = [instrument] + list(BENCHMARKS.values())
        display_names = [instrument] + list(BENCHMARKS.keys())
    ticker_to_display = dict(zip(all_tickers, display_names, strict=False))

    range_start = (
        start_date if isinstance(start_date, dt.date) else (dt.date.today() - dt.timedelta(days=_DEFAULT_LOOKBACK_DAYS))
    )
    range_end = end_date if isinstance(end_date, dt.date) else dt.date.today()

    panel = DataService.get_close_panel(all_tickers, range_start, range_end)
    # ffill across the panel: benchmarks trade on different calendars, so a US
    # holiday leaves a NaN in one column that we carry forward rather than
    # dropping the whole row.
    data = panel.sort_index().ffill() if not panel.empty else pd.DataFrame()

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


# Historical alias so existing call sites / tests that referenced
# ``_fetch_market_data`` keep working.
_fetch_market_data = fetch_market_data

"""DB query wrappers for cleaned / processed / spot data."""

import datetime as dt
import logging
import os
import threading
import time

import pandas as pd

from data_pipeline import _state as _g
from data_pipeline.orchestrate import backfill as _bf
from data_pipeline.orchestrate import update as _u
from data_pipeline.store.db import fetch_df, init_db

logger = logging.getLogger(__name__)

# ── Background backfill ──────────────────────────────────────────────────────
# CONSTRAINT: a first-ever wide-range request (default start = today − 5y)
# means ~21 throttled download chunks — tens of seconds to minutes of work.
# That must never run on the request thread. The backfill is kicked into a
# daemon thread (ensure_range's own in-flight dedup collapses concurrent
# kicks), the request waits a short grace period so the common "one chunk
# missing" case still returns full data, then reads whatever coverage exists.
_BACKFILL_WAIT_SECONDS = float(os.environ.get("BACKFILL_WAIT_SECONDS", "8"))
_backfill_lock = threading.Lock()
_backfill_threads: dict[tuple, threading.Thread] = {}


def _kick_backfill(ticker: str, start, end) -> None:
    key = (ticker, str(start), str(end))
    with _backfill_lock:
        existing = _backfill_threads.get(key)
        if existing is not None and existing.is_alive():
            return
        t = threading.Thread(target=_run_backfill, args=(ticker, start, end, key), daemon=True)
        _backfill_threads[key] = t
        t.start()
    logger.info("background backfill kicked for %s [%s .. %s]", ticker, start, end)


def _run_backfill(ticker, start, end, key) -> None:
    try:
        _bf.ensure_range(ticker, start, end)
    except Exception as e:
        logger.warning("background backfill failed for %s: %s", ticker, e)
    finally:
        # Daemon threads never re-run dispatch's finally-cleanups; drop this
        # thread's SQLite connection so _all_conns doesn't grow per backfill.
        from data_pipeline.store.db import close_thread_conn

        close_thread_conn()
        with _backfill_lock:
            _backfill_threads.pop(key, None)


def _join_backfills(timeout: float | None = None) -> None:
    """Test helper: wait for all in-flight background backfills."""
    with _backfill_lock:
        threads = list(_backfill_threads.values())
    for t in threads:
        t.join(timeout=timeout)


def _wait_for_coverage(ticker, start, end, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _bf.needs_backfill(ticker, start, end):
            return True
        time.sleep(0.25)
    return not _bf.needs_backfill(ticker, start, end)


def get_cleaned_daily(ticker: str, start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
    """Return cleaned daily prices, triggering update + backfill if needed."""
    # INVARIANT: call sibling modules directly, never the DataService facade —
    # facade imports this module, so reaching back up would be an import cycle.
    start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
    end = end or dt.date.today()
    cache_key = (ticker, "clean", str(start), str(end))
    cached = _g._cache_get(cache_key)
    if cached is not None:
        # A live cache entry was written ≤ _QUERY_CACHE_TTL ago, right after an
        # update/backfill cycle — skip the update checks entirely so repeat
        # wide-range requests never re-enter the (potentially very slow)
        # ensure_range path.
        return cached
    _u.manual_update(ticker, days=7)
    if _bf.needs_backfill(ticker, start, end):
        # Missing span ⇒ keep the heavy download off the request thread; give
        # it a short grace period so "one chunk missing" still returns full
        # data, then fall through to whatever coverage the DB has now.
        _kick_backfill(ticker, start, end)
        _wait_for_coverage(ticker, start, end, _BACKFILL_WAIT_SECONDS)
    else:
        _bf.ensure_range(ticker, start, end)
    init_db()
    df = fetch_df(
        "SELECT date, open, high, low, close, adj_close, volume FROM clean_bars WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    # Never memoise a partial read: while the background backfill is running
    # this df may lack the requested span. ensure_range invalidates the
    # ticker's cache entries on success, so the completed data becomes visible
    # on the next request.
    if not _bf.needs_backfill(ticker, start, end):
        _g._cache_set(cache_key, df)
    return df


def get_processed(
    ticker: str, frequency: str = "D", start: dt.date | None = None, end: dt.date | None = None
) -> pd.DataFrame:
    start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
    end = end or dt.date.today()
    cache_key = (ticker, "processed", frequency, str(start), str(end))
    cached = _g._cache_get(cache_key)
    if cached is not None:
        return cached
    _u.manual_update(ticker, days=7)
    init_db()
    df = fetch_df(
        "SELECT * FROM feature_bars WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
        (ticker, frequency, start.isoformat(), end.isoformat()),
    )
    # Never memoise an empty read: a not-yet-generated frequency/range would
    # otherwise be pinned for _QUERY_CACHE_TTL and hide the data once the
    # processing pass completes (mirrors the partial-read guard in
    # get_cleaned_daily above).
    if not df.empty:
        _g._cache_set(cache_key, df)
    return df


def get_processed_data(ticker: str, start: dt.date, end: dt.date, frequency: str = "W") -> pd.DataFrame:
    """Backward-compatible alias of :func:`get_processed` that swallows errors."""
    try:
        return get_processed(ticker, frequency, start, end)
    except Exception as e:
        logger.error("Error fetching processed data: %s", e)
        return pd.DataFrame()


def get_latest_spot(ticker: str) -> float | None:
    """Return latest close price for *ticker* from clean_bars (provider-sourced)."""
    init_db()
    df = fetch_df(
        "SELECT close FROM clean_bars WHERE ticker=? AND close IS NOT NULL ORDER BY date DESC LIMIT 1",
        (ticker,),
    )
    if not df.empty:
        val = df.iloc[0]["close"] if "close" in df.columns else df.iloc[0, 0]
        try:
            return float(val)
        except (TypeError, ValueError):
            pass

    from data_pipeline.providers.yf_client import fetch_spot

    try:
        price = fetch_spot(ticker)
        if price and price > 0:
            return float(price)
    except Exception:
        logger.debug("yfinance spot fallback failed for %s", ticker)
    return None

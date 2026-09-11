"""DB query wrappers for cleaned / processed / spot data."""

import datetime as dt
import logging
import os
import time

import pandas as pd

from data_pipeline import _state as _g
from data_pipeline.orchestrate import backfill as _bf
from data_pipeline.orchestrate import update as _u
from data_pipeline.orchestrate.readiness import kick_backfill as _kick_backfill
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

# NOTE: the kicker itself lives in ``orchestrate/readiness.py`` — batch B5 made it
# shared between this per-slice path and the readiness pass on POST /. It is
# re-exported (as ``_kick_backfill`` / ``_join_backfills``) at the top of this
# module so existing callers and tests keep working.


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


# DOMAIN: default lookback for the market-review close panel when the caller
# passes no explicit range. Matches the 400-day window the old
# market_review_prices ladder used (services/market_review/fetch.py).
_PANEL_LOOKBACK_DAYS = 400


def get_close_panel(
    symbols: list[str],
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> pd.DataFrame:
    """Wide close-price panel from ``clean_bars`` for *symbols* (ADR 0011, L5).

    Replaces the old ``market_review_prices`` acquisition path: every symbol —
    the primary ticker and each benchmark — is coverage-healed through the same
    ``needs_backfill`` / background ``ensure_range`` machinery the rest of the
    read layer uses, then its ``close`` series is read from ``clean_bars``.

    Missing ranges are kicked once up front and then awaited **together** for a
    single short grace window, so a cold panel costs ~one grace period, not one
    per symbol. Whatever coverage exists at the end of that window is returned;
    the background backfills keep filling and the next call sees the rest.

    Returns a date-indexed frame with one column per symbol that had any data
    (input order), or an empty frame when nothing is available.
    """
    start = start or (dt.date.today() - dt.timedelta(days=_PANEL_LOOKBACK_DAYS))
    end = end or dt.date.today()
    init_db()

    kicked: list[str] = []
    for sym in symbols:
        try:
            _u.manual_update(sym, days=7)
            if _bf.needs_backfill(sym, start, end):
                _kick_backfill(sym, start, end)
                kicked.append(sym)
            else:
                _bf.ensure_range(sym, start, end)
        except Exception as exc:  # noqa: BLE001 — one bad symbol must not sink the panel
            logger.warning("close-panel coverage check failed for %s: %s", sym, exc)

    if kicked:
        deadline = time.monotonic() + _BACKFILL_WAIT_SECONDS
        while time.monotonic() < deadline:
            if not any(_bf.needs_backfill(s, start, end) for s in kicked):
                break
            time.sleep(0.25)

    series: dict[str, pd.Series] = {}
    for sym in symbols:
        # fetch_df indexes by date when the column is present.
        df = fetch_df(
            "SELECT date, close FROM clean_bars WHERE ticker=? AND date>=? AND date<=? ORDER BY date",
            (sym, start.isoformat(), end.isoformat()),
        )
        if df.empty or "close" not in df.columns:
            continue
        s = df["close"].dropna()
        if not s.empty:
            series[sym] = s
    if not series:
        return pd.DataFrame()
    return pd.DataFrame(series).sort_index()


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
    if _bf.needs_backfill(ticker, start, end):
        # A clean gap, or clean present but feature_bars lagging (plan §10 F4):
        # heal off the request thread with a short grace wait, then read
        # whatever coverage exists — same pattern as get_cleaned_daily.
        _kick_backfill(ticker, start, end)
        _wait_for_coverage(ticker, start, end, _BACKFILL_WAIT_SECONDS)
    init_db()
    df = fetch_df(
        "SELECT * FROM feature_bars WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
        (ticker, frequency, start.isoformat(), end.isoformat()),
    )
    # Never memoise an empty or partial read: a not-yet-generated frequency/range
    # would otherwise be pinned for _QUERY_CACHE_TTL and hide the data once the
    # processing pass completes (mirrors the guard in get_cleaned_daily above).
    if not df.empty and not _bf.needs_backfill(ticker, start, end):
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

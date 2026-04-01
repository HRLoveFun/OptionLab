import datetime as dt
import logging
import threading
import time

import pandas as pd

from .cleaning import clean_range
from .db import fetch_df, init_db
from .downloader import upsert_raw_prices
from .processing import process_frequencies

logger = logging.getLogger(__name__)

_update_locks: dict = {}  # ticker -> last_update_timestamp (monotonic)
_update_lock_mutex = threading.Lock()
_UPDATE_COOLDOWN = 60  # same ticker: at most one write per 60 seconds

# ── TTL cache for DB query results ────────────────────────────────
_QUERY_CACHE_TTL = 60  # seconds
_query_cache: dict = {}  # key -> (timestamp, DataFrame)
_query_cache_lock = threading.Lock()


def _cache_get(key: tuple) -> pd.DataFrame | None:
    """Return cached DataFrame if key exists and is within TTL, else None."""
    with _query_cache_lock:
        entry = _query_cache.get(key)
        if entry and (time.monotonic() - entry[0]) < _QUERY_CACHE_TTL:
            return entry[1].copy()
        if entry:
            del _query_cache[key]
    return None


def _cache_set(key: tuple, df: pd.DataFrame) -> None:
    with _query_cache_lock:
        _query_cache[key] = (time.monotonic(), df)


def _cache_invalidate(ticker: str) -> None:
    """Remove all cached entries for a given ticker."""
    with _query_cache_lock:
        keys_to_remove = [k for k in _query_cache if k[0] == ticker]
        for k in keys_to_remove:
            del _query_cache[k]


class DataService:
    """
    Facade for data operations.
    - manual_update: on each access, update past week and recompute
    - get_prices: return cleaned or processed data
    """

    @staticmethod
    def initialize():
        init_db()

    @staticmethod
    def manual_update(ticker: str, days: int = 7):
        """Incremental update with concurrency throttle.
        Skips if the same ticker was updated within _UPDATE_COOLDOWN seconds.
        Returns True if the pipeline ran, False if skipped due to cooldown.
        """
        with _update_lock_mutex:
            last = _update_locks.get(ticker, 0)
            now = time.monotonic()
            if now - last < _UPDATE_COOLDOWN:
                logger.debug(f"Skipping update for {ticker} (cooldown)")
                return False
            # Reserve the slot atomically so no other thread can start the same ticker
            _update_locks[ticker] = now

        # Actual write happens outside the mutex so other tickers aren't blocked
        try:
            end = dt.date.today()
            start = end - dt.timedelta(days=days - 1)
            dl_result = upsert_raw_prices(ticker, start, end)
            if not dl_result.ok:
                logger.warning(f"Download stage failed for {ticker}: {dl_result.error}")
                return False
            cl_result = clean_range(ticker, start, end)
            if not cl_result.ok:
                logger.warning(f"Cleaning stage failed for {ticker}: {cl_result.error}")
                return False
            pr_result = process_frequencies(ticker, start, end)
            if not pr_result.ok:
                logger.warning(f"Processing stage failed for {ticker}: {pr_result.error}")
                return False
            # Log any warnings from stages
            for w in dl_result.warnings + cl_result.warnings + pr_result.warnings:
                logger.info(f"Pipeline warning for {ticker}: {w}")
            # Invalidate cached query results for this ticker
            _cache_invalidate(ticker)
            return True
        except Exception:
            # Pipeline failed — clear the cooldown so a retry is possible
            with _update_lock_mutex:
                _update_locks.pop(ticker, None)
            raise

    @staticmethod
    def has_data_for_date(ticker: str, date: dt.date) -> bool:
        """Return True if `clean_prices` contains a row for the given ticker and date.

        This is useful for checking whether the DB contains market data for a requested
        inclusive end date (to distinguish 'no market data yet' from 'code excluded end').
        """
        # Ensure DB exists
        init_db()
        df = fetch_df(
            "SELECT * FROM clean_prices WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        if not df.empty:
            return True
        # Fallback: check raw_prices table
        df2 = fetch_df(
            "SELECT * FROM raw_prices WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        return not df2.empty

    @staticmethod
    def seed_history(ticker: str, years: int = 5):
        """One-time helper to seed multi-year history for a ticker into the DB.

        This downloads the full range [today - years*365, today] (inclusive) via the
        existing downloader/clean/processing pipeline and upserts records into the DB.
        Use this when you want to avoid PriceDynamic falling back to a live download
        for long historical ranges.
        """
        end = dt.date.today()
        start = end - dt.timedelta(days=years * 365)
        # Download raw for full range, clean, and process
        upsert_raw_prices(ticker, start, end)
        clean_range(ticker, start, end)
        process_frequencies(ticker, start, end)

    @staticmethod
    def get_cleaned_daily(ticker: str, start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
        start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
        end = end or dt.date.today()
        DataService.manual_update(ticker, days=7)  # manual update on access
        cache_key = (ticker, "clean", str(start), str(end))
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        df = fetch_df(
            "SELECT date, open, high, low, close, adj_close, volume FROM clean_prices WHERE ticker=? AND date>=? AND date<=?",
            (ticker, start.isoformat(), end.isoformat()),
        )
        _cache_set(cache_key, df)
        return df

    @staticmethod
    def get_processed(
        ticker: str, frequency: str = "D", start: dt.date | None = None, end: dt.date | None = None
    ) -> pd.DataFrame:
        start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
        end = end or dt.date.today()
        DataService.manual_update(ticker, days=7)
        cache_key = (ticker, "processed", frequency, str(start), str(end))
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached
        df = fetch_df(
            "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
            (ticker, frequency, start.isoformat(), end.isoformat()),
        )
        _cache_set(cache_key, df)
        return df

    @staticmethod
    def get_processed_data(ticker: str, start: dt.date, end: dt.date, frequency: str = "W") -> pd.DataFrame:
        """Get processed data including osc_high, osc_low, and other features."""
        try:
            DataService.manual_update(ticker, days=7)
            cache_key = (ticker, "processed", frequency, str(start), str(end))
            cached = _cache_get(cache_key)
            if cached is not None:
                return cached
            df = fetch_df(
                "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
                (ticker, frequency, start.isoformat(), end.isoformat()),
            )
            _cache_set(cache_key, df)
            return df
        except Exception as e:
            logger.error(f"Error fetching processed data: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_latest_spot(ticker: str) -> float | None:
        """Return latest close price for *ticker* from clean_prices (Yahoo-sourced).

        Falls back to yfinance fast_info if DB has no data.
        Returns None when no price can be determined.
        """
        init_db()
        df = fetch_df(
            "SELECT close FROM clean_prices WHERE ticker=? AND close IS NOT NULL ORDER BY date DESC LIMIT 1",
            (ticker,),
        )
        if not df.empty:
            val = df.iloc[0]["close"] if "close" in df.columns else df.iloc[0, 0]
            try:
                return float(val)
            except (TypeError, ValueError):
                pass

        # Fallback: live yfinance quote
        try:
            import yfinance as yf

            from utils.utils import yf_throttle

            yf_throttle()
            price = yf.Ticker(ticker).fast_info.last_price
            if price and price > 0:
                return float(price)
        except Exception:
            logger.debug("yfinance spot fallback failed for %s", ticker)
        return None

"""Data service layer: orchestrates download, cleaning, and storage of market data."""
import datetime as dt
import logging
import os
import threading
import time

import pandas as pd

from .cleaning import clean_range
from .db import fetch_df, init_db
from .downloader import find_missing_business_days, upsert_raw_prices
from .processing import process_frequencies

logger = logging.getLogger(__name__)

_update_locks: dict = {}  # ticker -> last_update_timestamp (monotonic)
_update_lock_mutex = threading.Lock()
# DOMAIN: 60-second per-ticker write cooldown.
# WHY: Multiple UI panels often request the same ticker at the same instant
# (initial dashboard load). Without the cooldown, each panel triggers its
# own yfinance download — a thundering herd that burns the rate-limit
# budget instantly. See ADR 0002 / 0005.
_UPDATE_COOLDOWN = 60  # same ticker: at most one write per 60 seconds

# WHY: manual_update's cost-path download window is small (`days` arg,
# default 7), but we scan further back for missing business days so
# historical holes from past machine-off periods get back-filled.
# CONSTRAINT: capped to keep yfinance load bounded — see
# downloader.MAX_AUTO_BACKFILL_DAYS and docs/constraints.md §4.
GAP_SCAN_DAYS = int(os.environ.get("GAP_SCAN_DAYS", "30"))

# ── TTL cache for DB query results ────────────────────────────────
# WHY: identical SELECTs from concurrent panel renders waste SQLite reads.
# A 60s TTL matches the data-write cooldown so cache and DB stay aligned.
# INVARIANT: every write path that touches a ticker must call
# ``_cache_invalidate(ticker)`` afterwards, or stale data is served.
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
        # WHY: Reject syntactically invalid tickers up-front. Otherwise any
        # call site (validate_ticker → MarketAnalyzer → get_cleaned_daily →
        # manual_update) will fire a yfinance request and write to clean_prices
        # for arbitrary attacker-controlled strings.
        from utils.ticker_utils import is_valid_ticker_format

        if not is_valid_ticker_format(ticker):
            logger.debug(f"Skipping manual_update for invalid ticker: {ticker!r}")
            return False
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
            # Widen the start to cover any historical gaps within GAP_SCAN_DAYS.
            # The downloader is gap-aware: when no gaps exist this is essentially
            # free (no extra Yahoo round-trip). When gaps exist, we recompute
            # clean/processed over the actual download range so analyzer tables
            # stay in sync with raw.
            scan_start = end - dt.timedelta(days=GAP_SCAN_DAYS)
            gaps = find_missing_business_days(ticker, scan_start, end)
            if gaps and min(gaps) < start:
                logger.info(
                    f"Gap detected for {ticker} at {min(gaps)}; expanding update range to {min(gaps)}..{end}"
                )
                start = min(gaps)
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

    # WHY: ensure_range can be called many times within a single page render
    # (4 streaming slices × N tickers). Without a memo, each call re-issues
    # the chunked yfinance backfill, multiplying the rate-limit footprint.
    # The TTL is generous because backfill rarely changes within a session.
    _ENSURE_RANGE_TTL = 300  # 5 minutes
    _ensure_range_memo: dict = {}  # ticker -> (last_ts, last_start, last_end)
    _ensure_range_lock = threading.Lock()
    # WHY: in-flight dedup. The memo only deduplicates SEQUENTIAL calls — if
    # 4 streaming slices fire ensure_range(NVDA, …) concurrently, they all
    # see an empty memo and proceed in parallel. A per-ticker condition
    # makes followers wait for the leader and inherit its memo result.
    _ensure_range_inflight: dict = {}  # ticker -> threading.Event
    _ensure_range_inflight_lock = threading.Lock()

    # CONSTRAINT: yfinance has very thin coverage before ~1990 and most
    # equities don't trade that far back at all. Walking from today back to
    # 1900-01-01 in 90d chunks would issue ~500 calls per ticker and trip
    # the 429 rate-limit immediately. Clamp the practical lower bound here.
    _BACKFILL_MIN_DATE = dt.date(1990, 1, 1)

    # WHY: when the caller passes a sentinel "give me everything" start
    # (e.g. PriceDynamic uses 1900-01-01 to ask for max history), and the DB
    # already has years of coverage, do NOT attempt a multi-year backfill of
    # the gap. yfinance won't typically return pre-IPO data anyway. We treat
    # this as "DB coverage is the practical maximum."
    _SENTINEL_GAP_THRESHOLD_DAYS = 365  # if start is >1y before existing_min, treat as sentinel
    # INVARIANT: only treat DB as authoritative when it actually spans a
    # meaningful horizon. If DB has e.g. only 30 days of recent data, the
    # sentinel short-circuit must NOT fire — we still need to backfill so
    # statistical analyses over multi-year windows have data points.
    _SENTINEL_MIN_DB_SPAN_DAYS = 365

    @staticmethod
    def ensure_range(ticker: str, start: dt.date, end: dt.date) -> bool:
        """Ensure clean_prices covers [start, end].

        WHY: manual_update only scans GAP_SCAN_DAYS (~30 days) back, so if a
        user requests a 2-year range and the DB only has the last month, the
        gap detector silently misses 23 missing months. This method:
          1) Inspects existing date coverage in clean_prices.
          2) If start is earlier than the earliest existing row (or the DB is
             empty), triggers a full pipeline run for [start, end] via
             upsert_raw_prices → clean_range → process_frequencies.
        Returns True on success, False on skip/failure.
        """
        from utils.ticker_utils import is_valid_ticker_format

        if not is_valid_ticker_format(ticker):
            return False
        # WHY: detect the sentinel-start case BEFORE clamping so we can
        # distinguish "PriceDynamic asked for max history" (where we should
        # accept whatever DB has) from "user asked for an explicit 5-year
        # range" (where we MUST backfill). Without this distinction we'd
        # silently swallow legitimate multi-year requests when DB only has
        # 30 recent days.
        original_start_was_sentinel = start < DataService._BACKFILL_MIN_DATE
        # Clamp absurd lower bounds so PriceDynamic's sentinel 1900-01-01
        # doesn't trigger a 500-chunk yfinance walk.
        if start < DataService._BACKFILL_MIN_DATE:
            start = DataService._BACKFILL_MIN_DATE
        # WHY: per-ticker memo prevents the 4-slice page render from issuing
        # 4 identical multi-year backfills. Same (ticker, start, end) within
        # TTL ⇒ skip and trust the previous attempt.
        now = time.monotonic()
        with DataService._ensure_range_lock:
            memo = DataService._ensure_range_memo.get(ticker)
            if memo is not None:
                last_ts, last_start, last_end = memo
                if (now - last_ts) < DataService._ENSURE_RANGE_TTL and last_start <= start and last_end >= end:
                    return True
        # WHY: in-flight dedup. If another thread is already running
        # ensure_range for this ticker, wait for it (up to TTL) and trust
        # its memo result rather than starting a duplicate backfill.
        with DataService._ensure_range_inflight_lock:
            event = DataService._ensure_range_inflight.get(ticker)
            if event is not None:
                # Another thread is the leader; we're a follower.
                follower = True
            else:
                follower = False
                event = threading.Event()
                DataService._ensure_range_inflight[ticker] = event
        if follower:
            event.wait(timeout=DataService._ENSURE_RANGE_TTL)
            # Leader recorded its memo; re-check.
            with DataService._ensure_range_lock:
                memo = DataService._ensure_range_memo.get(ticker)
            if memo is not None:
                _last_ts, last_start, last_end = memo
                return last_start <= start and last_end >= end
            return False

        try:
            return DataService._ensure_range_impl(ticker, start, end, now, original_start_was_sentinel)
        finally:
            # Release followers regardless of success/failure.
            with DataService._ensure_range_inflight_lock:
                DataService._ensure_range_inflight.pop(ticker, None)
            event.set()

    @staticmethod
    def _ensure_range_impl(
        ticker: str, start: dt.date, end: dt.date, now: float, was_sentinel: bool = False
    ) -> bool:
        """Internal: actual backfill. Caller must hold the in-flight slot."""
        cov = fetch_df(
            "SELECT MIN(date) AS min_d, MAX(date) AS max_d, COUNT(*) AS n FROM clean_prices WHERE ticker=?",
            (ticker,),
        )
        existing_min = None
        existing_max = None
        if not cov.empty and cov.iloc[0]["n"]:
            try:
                existing_min = dt.date.fromisoformat(str(cov.iloc[0]["min_d"]))
                existing_max = dt.date.fromisoformat(str(cov.iloc[0]["max_d"]))
            except (ValueError, TypeError):
                existing_min = existing_max = None
        # If we have full coverage, nothing to do.
        if existing_min is not None and existing_min <= start and existing_max >= end - dt.timedelta(days=3):
            with DataService._ensure_range_lock:
                DataService._ensure_range_memo[ticker] = (now, start, end)
            return True
        # WHY: when DB has years of data AND the original caller used a
        # sentinel "give me everything" start (e.g. PriceDynamic's
        # 1900-01-01), do NOT attempt a multi-year pre-existing-min
        # backfill. yfinance won't return pre-IPO data and the chunked walk
        # would burn rate-limit budget for nothing.
        # NOTE: this branch is gated on `was_sentinel`. A user-explicit
        # multi-year range (e.g. 2021-03-01) MUST proceed to backfill even
        # if DB only has recent rows.
        if (
            was_sentinel
            and existing_min is not None
            and existing_max is not None
            and (existing_min - start).days > DataService._SENTINEL_GAP_THRESHOLD_DAYS
            and existing_max >= end - dt.timedelta(days=3)
            # INVARIANT: DB span must itself cover at least ~1y, otherwise
            # we have no basis for treating it as authoritative.
            and (existing_max - existing_min).days >= DataService._SENTINEL_MIN_DB_SPAN_DAYS
        ):
            logger.debug(
                "ensure_range: %s start=%s far before existing_min=%s; "
                "treating DB coverage as authoritative (skip backfill)",
                ticker, start, existing_min,
            )
            with DataService._ensure_range_lock:
                DataService._ensure_range_memo[ticker] = (now, start, end)
            return True
        # Determine the missing range to fetch.
        fetch_start = start if existing_min is None or start < existing_min else existing_min
        fetch_end = end
        try:
            logger.info(
                f"ensure_range: backfilling {ticker} [{fetch_start} .. {fetch_end}] "
                f"(existing={existing_min}..{existing_max})"
            )
            # WHY: upsert_raw_prices caps auto-backfill at MAX_AUTO_BACKFILL_DAYS
            # (~90d). For multi-year ranges we must bypass the cap by chunking
            # the download into ≤90d windows and calling upsert_raw_prices for
            # each. This is still a single user request, so the throttle
            # naturally limits load.
            from .downloader import MAX_AUTO_BACKFILL_DAYS

            chunk_end = fetch_end
            chunk_size = max(MAX_AUTO_BACKFILL_DAYS - 1, 30)
            while chunk_end > fetch_start:
                chunk_start = max(fetch_start, chunk_end - dt.timedelta(days=chunk_size))
                dl = upsert_raw_prices(ticker, chunk_start, chunk_end)
                if not dl.ok:
                    logger.warning(f"ensure_range download failed for {ticker} chunk {chunk_start}..{chunk_end}: {dl.error}")
                    with DataService._ensure_range_lock:
                        DataService._ensure_range_memo[ticker] = (now, start, end)
                    return False
                if chunk_start <= fetch_start:
                    break
                chunk_end = chunk_start - dt.timedelta(days=1)
            cl = clean_range(ticker, fetch_start, fetch_end)
            if not cl.ok:
                logger.warning(f"ensure_range cleaning failed for {ticker}: {cl.error}")
                with DataService._ensure_range_lock:
                    DataService._ensure_range_memo[ticker] = (now, start, end)
                return False
            pr = process_frequencies(ticker, fetch_start, fetch_end)
            if not pr.ok:
                logger.warning(f"ensure_range processing failed for {ticker}: {pr.error}")
                with DataService._ensure_range_lock:
                    DataService._ensure_range_memo[ticker] = (now, start, end)
                return False
            _cache_invalidate(ticker)
            with DataService._ensure_range_lock:
                DataService._ensure_range_memo[ticker] = (now, start, end)
            return True
        except Exception as e:
            logger.warning(f"ensure_range exception for {ticker}: {e}")
            # WHY: also memo failures (rate-limit/proxy) so we don't retry
            # the same multi-year backfill 4× per page render. Caller will
            # see the existing partial DB coverage instead.
            with DataService._ensure_range_lock:
                DataService._ensure_range_memo[ticker] = (now, start, end)
            return False

    @staticmethod
    def get_cleaned_daily(ticker: str, start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
        start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
        end = end or dt.date.today()
        DataService.manual_update(ticker, days=7)  # manual update on access
        # WHY: ensure DB covers requested range; otherwise a user asking
        # for 2024-01-01 .. 2025-12-31 on a ticker the DB only has 30
        # recent rows for would silently get an empty result.
        DataService.ensure_range(ticker, start, end)
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

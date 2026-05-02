"""Range backfill logic with memoisation and chunking."""

import datetime as dt
import logging
import threading
import time

import data_pipeline.db as _db

logger = logging.getLogger(__name__)

_ENSURE_RANGE_TTL = 300
_ensure_range_memo: dict = {}
_ensure_range_lock = threading.Lock()
_ensure_range_inflight: dict = {}
_ensure_range_inflight_lock = threading.Lock()

_BACKFILL_MIN_DATE = dt.date(1990, 1, 1)
_SENTINEL_GAP_THRESHOLD_DAYS = 365
_SENTINEL_MIN_DB_SPAN_DAYS = 365


def ensure_range(ticker: str, start: dt.date, end: dt.date) -> bool:
    """Ensure clean_prices covers [start, end]."""
    from utils.ticker_utils import is_valid_ticker_format

    if not is_valid_ticker_format(ticker):
        return False

    original_start_was_sentinel = start < _BACKFILL_MIN_DATE
    if start < _BACKFILL_MIN_DATE:
        start = _BACKFILL_MIN_DATE

    now = time.monotonic()
    with _ensure_range_lock:
        memo = _ensure_range_memo.get(ticker)
        if memo is not None:
            last_ts, last_start, last_end = memo
            if (now - last_ts) < _ENSURE_RANGE_TTL and last_start <= start and last_end >= end:
                return True

    with _ensure_range_inflight_lock:
        event = _ensure_range_inflight.get(ticker)
        if event is not None:
            follower = True
        else:
            follower = False
            event = threading.Event()
            _ensure_range_inflight[ticker] = event
    if follower:
        event.wait(timeout=_ENSURE_RANGE_TTL)
        with _ensure_range_lock:
            memo = _ensure_range_memo.get(ticker)
        if memo is not None:
            _last_ts, last_start, last_end = memo
            return last_start <= start and last_end >= end
        return False

    try:
        return _ensure_range_impl(ticker, start, end, now, original_start_was_sentinel)
    finally:
        with _ensure_range_inflight_lock:
            _ensure_range_inflight.pop(ticker, None)
        event.set()


def _ensure_range_impl(
    ticker: str, start: dt.date, end: dt.date, now: float, was_sentinel: bool = False
) -> bool:
    """Internal: actual backfill. Caller must hold the in-flight slot."""
    import time as _time

    import data_pipeline.cleaning as _cl
    import data_pipeline.downloader as _dl
    import data_pipeline.processing as _pr
    from data_pipeline.downloader import MAX_AUTO_BACKFILL_DAYS

    cov = _db.fetch_df(
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

    if existing_min is not None and existing_min <= start and existing_max >= end - dt.timedelta(days=3):
        with _ensure_range_lock:
            _ensure_range_memo[ticker] = (now, start, end)
        return True

    if (
        was_sentinel
        and existing_min is not None
        and existing_max is not None
        and (existing_min - start).days > _SENTINEL_GAP_THRESHOLD_DAYS
        and existing_max >= end - dt.timedelta(days=3)
        and (existing_max - existing_min).days >= _SENTINEL_MIN_DB_SPAN_DAYS
    ):
        logger.debug(
            "ensure_range: %s start=%s far before existing_min=%s; "
            "treating DB coverage as authoritative (skip backfill)",
            ticker, start, existing_min,
        )
        with _ensure_range_lock:
            _ensure_range_memo[ticker] = (now, start, end)
        return True

    fetch_start = start if existing_min is None or start < existing_min else existing_min
    fetch_end = end
    try:
        logger.info(
            "ensure_range: backfilling %s [%s .. %s] (existing=%s..%s)",
            ticker, fetch_start, fetch_end, existing_min, existing_max,
        )
        chunk_end = fetch_end
        chunk_size = max(MAX_AUTO_BACKFILL_DAYS - 1, 30)
        while chunk_end > fetch_start:
            chunk_start = max(fetch_start, chunk_end - dt.timedelta(days=chunk_size))
            dl = _dl.upsert_raw_prices(ticker, chunk_start, chunk_end)
            if not dl.ok:
                logger.warning("ensure_range download failed for %s chunk %s..%s: %s", ticker, chunk_start, chunk_end, dl.error)
                with _ensure_range_lock:
                    _ensure_range_memo[ticker] = (now, start, end)
                return False
            if chunk_start <= fetch_start:
                break
            chunk_end = chunk_start - dt.timedelta(days=1)
        cl = _cl.clean_range(ticker, fetch_start, fetch_end)
        if not cl.ok:
            logger.warning("ensure_range cleaning failed for %s: %s", ticker, cl.error)
            with _ensure_range_lock:
                _ensure_range_memo[ticker] = (now, start, end)
            return False
        pr = _pr.process_frequencies(ticker, fetch_start, fetch_end)
        if not pr.ok:
            logger.warning("ensure_range processing failed for %s: %s", ticker, pr.error)
            with _ensure_range_lock:
                _ensure_range_memo[ticker] = (now, start, end)
            return False
        from . import _globals as _g
        _g._cache_invalidate(ticker)
        with _ensure_range_lock:
            _ensure_range_memo[ticker] = (now, start, end)
        return True
    except Exception as e:
        logger.warning("ensure_range exception for %s: %s", ticker, e)
        with _ensure_range_lock:
            _ensure_range_memo[ticker] = (now, start, end)
        return False

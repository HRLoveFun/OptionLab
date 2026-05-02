"""Incremental update and seed helpers."""

import datetime as dt
import logging
import time

from utils.ticker_utils import is_valid_ticker_format

from . import _globals as _g

logger = logging.getLogger(__name__)


def manual_update(ticker: str, days: int = 7) -> bool:
    """Incremental update with concurrency throttle.

    Skips if the same ticker was updated within _UPDATE_COOLDOWN seconds.
    Returns True if the pipeline ran, False if skipped due to cooldown.
    """
    if not is_valid_ticker_format(ticker):
        logger.debug("Skipping manual_update for invalid ticker: %r", ticker)
        return False
    with _g._update_lock_mutex:
        last = _g._update_locks.get(ticker, 0)
        now = time.monotonic()
        if now - last < _g._UPDATE_COOLDOWN:
            logger.debug("Skipping update for %s (cooldown)", ticker)
            return False
        _g._update_locks[ticker] = now

    try:
        end = dt.date.today()
        start = end - dt.timedelta(days=days - 1)
        scan_start = end - dt.timedelta(days=_g.GAP_SCAN_DAYS)

        from data_pipeline.downloader import find_missing_business_days

        gaps = find_missing_business_days(ticker, scan_start, end)
        if gaps and min(gaps) < start:
            logger.info(
                "Gap detected for %s at %s; expanding update range to %s..%s",
                ticker, min(gaps), min(gaps), end,
            )
            start = min(gaps)

        import data_pipeline.downloader as _dl
        import data_pipeline.cleaning as _cl
        import data_pipeline.processing as _pr

        dl_result = _dl.upsert_raw_prices(ticker, start, end)
        if not dl_result.ok:
            logger.warning("Download stage failed for %s: %s", ticker, dl_result.error)
            return False
        cl_result = _cl.clean_range(ticker, start, end)
        if not cl_result.ok:
            logger.warning("Cleaning stage failed for %s: %s", ticker, cl_result.error)
            return False
        pr_result = _pr.process_frequencies(ticker, start, end)
        if not pr_result.ok:
            logger.warning("Processing stage failed for %s: %s", ticker, pr_result.error)
            return False
        for w in dl_result.warnings + cl_result.warnings + pr_result.warnings:
            logger.info("Pipeline warning for %s: %s", ticker, w)
        _g._cache_invalidate(ticker)
        return True
    except Exception:
        with _g._update_lock_mutex:
            _g._update_locks.pop(ticker, None)
        raise


def seed_history(ticker: str, years: int = 5) -> None:
    """One-time helper to seed multi-year history for a ticker into the DB."""
    end = dt.date.today()
    start = end - dt.timedelta(days=years * 365)
    import data_pipeline.downloader as _dl
    import data_pipeline.cleaning as _cl
    import data_pipeline.processing as _pr

    _dl.upsert_raw_prices(ticker, start, end)
    _cl.clean_range(ticker, start, end)
    _pr.process_frequencies(ticker, start, end)

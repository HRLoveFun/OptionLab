"""History bootstrap helpers for regime data pipeline."""

import datetime as dt
import logging

from data_pipeline.cleaning import clean_range
from data_pipeline.data_ops import _cache_invalidate
from data_pipeline.db import fetch_df, init_db
from data_pipeline.downloader import upsert_raw_prices
from data_pipeline.processing import process_frequencies
from core.regime import SMA_WINDOW, SLOPE_LOOKBACK

logger = logging.getLogger(__name__)

BOOTSTRAP_DAYS = 400  # ≈ 280 trading days
MIN_TRADING_ROWS = SMA_WINDOW + SLOPE_LOOKBACK + 5


def _count_clean_rows(ticker: str) -> int:
    """Return how many priced rows the DB holds for ``ticker``."""
    init_db()
    df = fetch_df(
        "SELECT COUNT(*) AS n FROM clean_prices WHERE ticker=? AND close IS NOT NULL",
        (ticker,),
    )
    if df.empty:
        return 0
    try:
        return int(df.iloc[0]["n"])
    except (KeyError, TypeError, ValueError):
        return 0


def _bootstrap_history(ticker: str, days: int = BOOTSTRAP_DAYS) -> None:
    """Run the full data pipeline over a wide date range for ``ticker``."""
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    logger.info("Regime: bootstrapping %d days of history for %s", days, ticker)
    try:
        dl = upsert_raw_prices(ticker, start, end)
        if not dl.ok:
            logger.warning("Regime bootstrap (download) failed for %s: %s", ticker, dl.error)
            return
        cl = clean_range(ticker, start, end)
        if not cl.ok:
            logger.warning("Regime bootstrap (clean) failed for %s: %s", ticker, cl.error)
            return
        pr = process_frequencies(ticker, start, end)
        if not pr.ok:
            logger.warning("Regime bootstrap (process) failed for %s: %s", ticker, pr.error)
    except Exception as e:
        logger.error("Regime bootstrap for %s crashed: %s", ticker, e, exc_info=True)
    finally:
        _cache_invalidate(ticker)




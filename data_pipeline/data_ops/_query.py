"""DB query wrappers for cleaned / processed / spot data."""

import datetime as dt
import logging

import pandas as pd

from data_pipeline.db import fetch_df, init_db

from . import _globals as _g

logger = logging.getLogger(__name__)


def get_cleaned_daily(ticker: str, start: dt.date | None = None, end: dt.date | None = None) -> pd.DataFrame:
    """Return cleaned daily prices, triggering update + backfill if needed."""
    from . import _service as _svc

    start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
    end = end or dt.date.today()
    _svc.DataService.manual_update(ticker, days=7)
    _svc.DataService.ensure_range(ticker, start, end)
    cache_key = (ticker, "clean", str(start), str(end))
    cached = _g._cache_get(cache_key)
    if cached is not None:
        return cached
    init_db()
    df = fetch_df(
        "SELECT date, open, high, low, close, adj_close, volume FROM clean_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    _g._cache_set(cache_key, df)
    return df


def get_processed(
    ticker: str, frequency: str = "D", start: dt.date | None = None, end: dt.date | None = None
) -> pd.DataFrame:
    start = start or (dt.date.today() - dt.timedelta(days=365 * 5))
    end = end or dt.date.today()
    from . import _service as _svc

    _svc.DataService.manual_update(ticker, days=7)
    cache_key = (ticker, "processed", frequency, str(start), str(end))
    cached = _g._cache_get(cache_key)
    if cached is not None:
        return cached
    init_db()
    df = fetch_df(
        "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
        (ticker, frequency, start.isoformat(), end.isoformat()),
    )
    _g._cache_set(cache_key, df)
    return df


def get_processed_data(ticker: str, start: dt.date, end: dt.date, frequency: str = "W") -> pd.DataFrame:
    """Get processed data including osc_high, osc_low, and other features."""
    try:
        from . import _service as _svc

        _svc.DataService.manual_update(ticker, days=7)
        cache_key = (ticker, "processed", frequency, str(start), str(end))
        cached = _g._cache_get(cache_key)
        if cached is not None:
            return cached
        init_db()
        df = fetch_df(
            "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
            (ticker, frequency, start.isoformat(), end.isoformat()),
        )
        _g._cache_set(cache_key, df)
        return df
    except Exception as e:
        logger.error("Error fetching processed data: %s", e)
        return pd.DataFrame()


def get_latest_spot(ticker: str) -> float | None:
    """Return latest close price for *ticker* from clean_prices (Yahoo-sourced)."""
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

"""Data-context acquisition — the I/O half of the old ``build_data_context``.

Domain:    Market Analysis — Data Context Acquisition
Context:
  - Batch B4 of the reorg closed the last ``core-purity`` leak: the DB-first
    read + provider fallback that used to live in
    ``core/market/data_context.py`` moved here, and ``core`` now only holds the
    pure container (``DataContext``) plus ``refrequency``.
  - WHY services/ owns it: choosing *what* to read (DB first, provider fallback,
    how far back) is orchestration, not computation — exactly the distinction
    ADR 0001 draws between ``core/`` and ``services/``.
Contracts:
  - ``fetch_data_context(ticker, start_date, frequency="W", end_date=None) -> DataContext``
    — never raises; a failed acquisition yields an invalid ``DataContext``.
Dependencies UPWARD:
  - data_pipeline.read (DataService), data_pipeline.providers.yf_client
    (provider fallback), core.market.data_context (pure container + builder),
    core.market.models (Horizon), utils.ticker_utils
Dependencies DOWNWARD:
  - services.market.facade, services.market.analysis.facade,
    services.options.chain
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd

from core.market.data_context import DataContext, build_data_context, empty_data_context
from core.market.models import Horizon

logger = logging.getLogger(__name__)

# CONSTRAINT: bounded retries prevent transient yfinance failures from crashing the pipeline.
_YF_MAX_RETRIES = 2

# CONSTRAINT: sub-second retries hit Yahoo rate-limiting; 3 s is the minimum stable back-off.
_YF_RETRY_BASE_DELAY = 3  # seconds


def _normalize_ticker(ticker: str) -> str:
    from utils.ticker_utils import normalize_ticker

    try:
        yahoo_ticker, _ = normalize_ticker(ticker)
        return yahoo_ticker or ticker
    except (ValueError, ImportError):
        return ticker


def _validate_inputs(ticker, start_date, frequency, end_date=None):
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError("Ticker must be a non-empty string")
    if not isinstance(start_date, dt.date):
        raise ValueError("start_date must be a datetime.date object")
    if frequency not in ("D", "W", "ME", "QE"):
        raise ValueError("frequency must be one of ['D', 'W', 'ME', 'QE']")
    if end_date is not None and not isinstance(end_date, dt.date):
        raise ValueError("end_date must be a datetime.date object or None")
    if end_date is not None and end_date < start_date:
        raise ValueError("end_date must be on or after start_date")


def _fetch_daily_from_db(ticker: str, download_start: dt.date):
    from data_pipeline.read import DataService

    try:
        DataService.initialize()
    except Exception:
        pass
    try:
        df = DataService.get_cleaned_daily(ticker, download_start, dt.date.today())
        if df is None or df.empty:
            return None
        df = df.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "adj_close": "Adj Close",
                "volume": "Volume",
            }
        )
        for col in ("Open", "High", "Low", "Close", "Adj Close", "Volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        price_cols = [c for c in ("Open", "High", "Low", "Close", "Adj Close") if c in df.columns]
        if price_cols:
            df = df.dropna(subset=price_cols, how="all")
        return df if not df.empty else None
    except Exception as e:
        logger.warning("DB fetch failed for %s: %s", ticker, e)
        return None


def _download_data(ticker: str, download_start: dt.date):
    from data_pipeline.providers.yf_client import fetch_daily_ohlcv

    yf_end = dt.date.today() + dt.timedelta(days=1)
    df = fetch_daily_ohlcv(
        ticker,
        download_start,
        yf_end,
        auto_adjust=False,
        max_retries=_YF_MAX_RETRIES,
        retry_base_delay=_YF_RETRY_BASE_DELAY,
    )
    if df.empty:
        logger.warning("No data downloaded for %s", ticker)
        return None
    required_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error("Missing columns for %s: %s", ticker, missing_columns)
        return None
    return df[required_columns]


def _fetch_raw_data(ticker: str, user_start_date: dt.date, frequency: str):
    """L1: DB  L2: provider fallback.  Returns (daily_df, ticker)."""
    download_start = dt.date(1900, 1, 1)
    raw_data = _fetch_daily_from_db(ticker, download_start)
    db_data = raw_data
    db_min = raw_data.index.min().date() if raw_data is not None and not raw_data.empty else None
    needs_yfinance = raw_data is None or raw_data.empty or (db_min is not None and db_min > user_start_date)
    if needs_yfinance:
        yf_data = _download_data(ticker, download_start)
        if yf_data is not None and not yf_data.empty:
            raw_data = yf_data
        elif db_data is not None and not db_data.empty:
            logger.warning("yfinance download failed for %s, using available DB data.", ticker)
            raw_data = db_data
    return raw_data, ticker


def fetch_data_context(
    ticker: str,
    start_date: dt.date,
    frequency: str = "W",
    end_date: dt.date | None = None,
) -> DataContext:
    """Fetch (DB-first) and assemble a ``DataContext``.

    Data pipeline:
      1. Normalise ticker (futu-format -> yahoo-format).
      2. Validate inputs.
      3. Fetch from the DB first; fall back to the provider if coverage is short.
      4. Resample to the requested frequency (pure ``build_data_context``).
    """
    try:
        _validate_inputs(ticker, start_date, frequency, end_date)
        norm_ticker = _normalize_ticker(ticker)
        raw_data, final_ticker = _fetch_raw_data(norm_ticker, start_date, frequency)
        return build_data_context(
            ticker=final_ticker,
            frequency=frequency,
            horizon=Horizon(
                start=start_date,
                end=end_date or dt.date.today(),
                user_provided_end=end_date is not None,
                frequency=frequency,
            ),
            raw_data=raw_data,
        )
    except Exception as e:
        logger.error("Failed to build DataContext for %s: %s", ticker, e)
        return empty_data_context(ticker, start_date, frequency, end_date)

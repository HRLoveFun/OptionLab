"""Market data context — explicit data container with data-fetching logic.

Domain:    Market Analysis — Data Context
Context:
  - Encapsulates data-fetching/resampling logic previously inside PriceDynamic.
  - Returns plain DataFrames so downstream features/charts are fully decoupled.
  - No feature calculation, no matplotlib, no business logic.
Contracts:
  - build_data_context(ticker, start_date, frequency, end_date) -> DataContext
  - DataContext exposes bars, daily_bars, horizon, ticker, frequency, is_valid
Dependencies DOWNWARD:
  - core.market.features, core.market.charts, services.analysis_service
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from core._shared.types import Frequency
from core.market.models import Horizon

logger = logging.getLogger(__name__)

# CONSTRAINT: bounded retries prevent transient yfinance failures from crashing the pipeline.
_YF_MAX_RETRIES = 2

# CONSTRAINT: sub-second retries hit Yahoo rate-limiting; 3 s is the minimum stable back-off.
_YF_RETRY_BASE_DELAY = 3  # seconds


# ---------------------------------------------------------------------------
# Internal helpers (extracted from former PriceDynamic)
# ---------------------------------------------------------------------------

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
    from data_pipeline.data_service import DataService

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
    from data_pipeline.yf_client import fetch_daily_ohlcv

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


def _refrequency(df: pd.DataFrame | None, frequency: str) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    try:
        if frequency == "D":
            df = df.copy()
            df["LastClose"] = df["Close"].shift(1)
            df["LastAdjClose"] = df["Adj Close"].shift(1)
            return df
        resampled = (
            df.resample(frequency)
            .agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Adj Close": "last",
                    "Volume": "sum",
                }
            )
            .dropna()
        )
        resampled["LastClose"] = resampled["Close"].shift(1)
        resampled["LastAdjClose"] = resampled["Adj Close"].shift(1)
        date_agg = df.resample(frequency).agg(
            {
                "Open": lambda x: x.index[0] if len(x) > 0 else pd.NaT,
                "High": lambda x: x.index[x.argmax()] if len(x) > 0 else pd.NaT,
                "Low": lambda x: x.index[x.argmin()] if len(x) > 0 else pd.NaT,
                "Close": lambda x: x.index[-1] if len(x) > 0 else pd.NaT,
            }
        )
        resampled["OpenDate"] = date_agg["Open"]
        resampled["HighDate"] = date_agg["High"]
        resampled["LowDate"] = date_agg["Low"]
        resampled["CloseDate"] = date_agg["Close"]
        return resampled
    except Exception as e:
        logger.error("Error resampling data: %s", e)
        return None


def _fetch_raw_data(ticker: str, user_start_date: dt.date, frequency: str):
    """L1: DB  L2: yfinance fallback.  Returns (daily_df, ticker)."""
    download_start = dt.date(1900, 1, 1)
    raw_data = _fetch_daily_from_db(ticker, download_start)
    db_data = raw_data
    db_min = raw_data.index.min().date() if raw_data is not None and not raw_data.empty else None
    needs_yfinance = (
        raw_data is None
        or raw_data.empty
        or (db_min is not None and db_min > user_start_date)
    )
    if needs_yfinance:
        yf_data = _download_data(ticker, download_start)
        if yf_data is not None and not yf_data.empty:
            raw_data = yf_data
        elif db_data is not None and not db_data.empty:
            logger.warning("yfinance download failed for %s, using available DB data.", ticker)
            raw_data = db_data
    return raw_data, ticker


# ---------------------------------------------------------------------------
# DataContext
# ---------------------------------------------------------------------------

class DataContext:
    """Immutable-ish container for market data fetched for a given ticker/horizon."""

    def __init__(
        self,
        ticker: str,
        frequency: Frequency,
        horizon: Horizon,
        bars: pd.DataFrame | None,
        daily_bars: pd.DataFrame | None,
    ):
        self.ticker = ticker
        self.frequency = frequency
        self.horizon = horizon
        self.bars = bars
        self.daily_bars = daily_bars

    def is_valid(self) -> bool:
        return self.bars is not None and not self.bars.empty

    @property
    def features_df(self) -> pd.DataFrame:
        """Lazy-assembled feature DataFrame (backward-compat shim)."""
        from core.market.features import osc, price_difference, price_returns

        if not self.is_valid():
            return pd.DataFrame()
        try:
            return pd.DataFrame(
                {
                    "Oscillation": osc(self.bars, on_effect=True),
                    "Osc_high": self._safe_series("Osc_high"),
                    "Osc_low": self._safe_series("Osc_low"),
                    "Returns": price_returns(self.bars),
                    "Difference": price_difference(self.bars),
                }
            ).dropna(how="all")
        except Exception as e:
            logger.warning("features_df assembly failed: %s", e)
            return pd.DataFrame()

    def _safe_series(self, name: str) -> pd.Series | None:
        from core.market.features import osc_high, osc_low

        if name == "Osc_high":
            return osc_high(self.bars)
        if name == "Osc_low":
            return osc_low(self.bars)
        return None

    @property
    def current_price(self) -> float | None:
        if not self.is_valid():
            return None
        try:
            return float(self.bars["Close"].iloc[-1])
        except Exception:
            return None

    @property
    def bars_date_range(self) -> tuple[str, str] | None:
        if not self.is_valid():
            return None
        try:
            return (
                self.bars.index.min().date().isoformat(),
                self.bars.index.max().date().isoformat(),
            )
        except Exception:
            return None


def build_data_context(
    ticker: str,
    start_date: dt.date,
    frequency: Frequency = "W",
    end_date: dt.date | None = None,
) -> DataContext:
    """Build a DataContext by fetching and resampling market data.

    Data pipeline:
      1. Normalise ticker (futu-format -> yahoo-format).
      2. Validate inputs.
      3. Fetch from DB first; fall back to yfinance if DB coverage is insufficient.
      4. Resample to requested frequency.
    """
    try:
        _validate_inputs(ticker, start_date, frequency, end_date)
        norm_ticker = _normalize_ticker(ticker)
        raw_data, final_ticker = _fetch_raw_data(norm_ticker, start_date, frequency)
        bars = _refrequency(raw_data, frequency)
        horizon = Horizon(
            start=start_date,
            end=end_date or dt.date.today(),
            user_provided_end=end_date is not None,
            frequency=frequency,
        )
        return DataContext(
            ticker=final_ticker,
            frequency=frequency,
            horizon=horizon,
            bars=bars,
            daily_bars=raw_data,
        )
    except Exception as e:
        logger.error("Failed to build DataContext for %s: %s", ticker, e)
        horizon = Horizon(
            start=start_date,
            end=end_date or dt.date.today(),
            user_provided_end=end_date is not None,
            frequency=frequency,
        )
        return DataContext(
            ticker=ticker,
            frequency=frequency,
            horizon=horizon,
            bars=None,
            daily_bars=None,
        )

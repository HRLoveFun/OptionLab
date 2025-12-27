import datetime as dt
import logging
from typing import Optional

import pandas as pd

from .db import init_db, fetch_df
from .downloader import upsert_raw_prices
from .cleaning import clean_range
from .processing import process_frequencies

logger = logging.getLogger(__name__)


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
        # Treat end as inclusive
        end = dt.date.today()
        start = end - dt.timedelta(days=days - 1)
        upsert_raw_prices(ticker, start, end)
        clean_range(ticker, start, end)
        process_frequencies(ticker, start, end)

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
    def get_cleaned_daily(ticker: str, start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> pd.DataFrame:
        start = start or (dt.date.today() - dt.timedelta(days=365*5))
        end = end or dt.date.today()
        DataService.manual_update(ticker, days=7)  # manual update on access
        return fetch_df(
            "SELECT date, open, high, low, close, adj_close, volume FROM clean_prices WHERE ticker=? AND date>=? AND date<=?",
            (ticker, start.isoformat(), end.isoformat()),
        )

    @staticmethod
    def get_processed(ticker: str, frequency: str = "D", start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> pd.DataFrame:
        start = start or (dt.date.today() - dt.timedelta(days=365*5))
        end = end or dt.date.today()
        DataService.manual_update(ticker, days=7)
        df = fetch_df(
            "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
            (ticker, frequency, start.isoformat(), end.isoformat()),
        )
        return df

    @staticmethod
    def get_processed_data(ticker: str, start: dt.date, end: dt.date, frequency: str = "W") -> pd.DataFrame:
        """Get processed data including osc_high, osc_low, and other features."""
        try:
            DataService.manual_update(ticker, days=7)
            df = fetch_df(
                "SELECT * FROM processed_prices WHERE ticker=? AND frequency=? AND date>=? AND date<=?",
                (ticker, frequency, start.isoformat(), end.isoformat()),
            )
            return df
        except Exception as e:
            logger.error(f"Error fetching processed data: {e}")
            return pd.DataFrame()

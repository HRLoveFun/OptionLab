import os
import sys
import tempfile
import datetime as dt

# Ensure workspace root is on sys.path so we can import data_pipeline as a package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Create a temp DB file and set MARKET_DB_PATH before importing pipeline modules
fd, path = tempfile.mkstemp(suffix='.sqlite')
os.close(fd)
os.environ['MARKET_DB_PATH'] = path

import pandas as pd

from data_pipeline import db as dbmod
from data_pipeline.data_service import DataService
from data_pipeline.cleaning import clean_range


def test_inclusive_end_semantics():
    # Use a temp DB file
    try:
        # Initialize DB
        dbmod.init_db(path)

        ticker = 'TEST'
        # Insert a single raw_prices row for 2025-09-23
        date = dt.date(2025, 9, 23)
        rows = [(
            ticker,
            date.isoformat(),
            100.0,
            105.0,
            99.0,
            104.0,
            104.0,
            100000.0,
            'yfinance'
        )]
        dbmod.upsert_many(
            'raw_prices',
            ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"],
            rows,
            db_path=path,
        )

        # Run cleaning for that date (inclusive)
        clean_range(ticker, start=date, end=date)

        # Now the DataService should report that there is data for the date
        assert DataService.has_data_for_date(ticker, date) is True

        # Directly query clean_prices to confirm the cleaned row exists for that date
        df2 = dbmod.fetch_df('SELECT * FROM clean_prices WHERE ticker=? AND date=?', (ticker, date.isoformat()), db_path=path)
        assert not df2.empty
        assert pd.to_datetime(df2.index.max()).date() == date

    finally:
        try:
            os.remove(path)
        except Exception:
            pass

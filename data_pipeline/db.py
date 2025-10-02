import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

DB_PATH = os.environ.get("MARKET_DB_PATH", os.path.join(os.getcwd(), "market_data.sqlite"))


def init_db(db_path: Optional[str] = None):
    path = db_path or DB_PATH
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        cur = conn.cursor()
        # Raw OHLCV data
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume REAL,
                provider TEXT DEFAULT 'yfinance',
                PRIMARY KEY (ticker, date)
            )
            """
        )
        # Cleaned daily OHLCV with flags
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clean_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume REAL,
                is_trading_day INTEGER DEFAULT 1,
                missing_any INTEGER DEFAULT 0,
                price_jump_flag INTEGER DEFAULT 0,
                vol_anom_flag INTEGER DEFAULT 0,
                ohlc_inconsistent INTEGER DEFAULT 0,
                PRIMARY KEY (ticker, date)
            )
            """
        )
        # Processed features per frequency
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                frequency TEXT NOT NULL, -- D/W/M
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume REAL,
                last_close REAL,
                log_return REAL,
                amplitude REAL,
                log_hl_spread REAL,
                parkinson_var REAL,
                gk_var REAL,
                log_vol_delta REAL,
                vol_zscore REAL,
                ma_5 REAL,
                ma_10 REAL,
                ma_20 REAL,
                ma_60 REAL,
                ma_120 REAL,
                ma_250 REAL,
                mom_10 REAL,
                mom_20 REAL,
                mom_60 REAL,
                PRIMARY KEY (ticker, date, frequency)
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn(db_path: Optional[str] = None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        yield conn
    finally:
        conn.close()


def upsert_many(table: str, columns: Iterable[str], rows: Iterable[Iterable], db_path: Optional[str] = None):
    cols = list(columns)
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c not in ("ticker", "date", "frequency")])
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT DO UPDATE SET {updates}"
    with get_conn(db_path) as conn:
        conn.executemany(sql, rows)
        conn.commit()


def fetch_df(query: str, params: tuple = (), db_path: Optional[str] = None):
    import pandas as pd
    with get_conn(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])  # type: ignore
    if not df.empty:
        df = df.sort_values("date").set_index("date")
    return df

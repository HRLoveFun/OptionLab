import os
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get("MARKET_DB_PATH", os.path.join(os.getcwd(), "market_data.sqlite"))


def init_db(db_path: str | None = None):
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
                osc_high REAL,
                osc_low REAL,
                osc REAL,
                PRIMARY KEY (ticker, date, frequency)
            )
            """
        )
        # Market review benchmark close prices
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS market_review_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                close REAL,
                PRIMARY KEY (ticker, date)
            )
            """
        )
        # Market regime daily log (see core.regime)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS regime_log (
                date TEXT PRIMARY KEY,
                vol_regime TEXT,
                dir_regime TEXT,
                vix_value REAL,
                sma_20 REAL,
                sma_slope_5d REAL,
                close_vs_sma_pct REAL,
                regime_changed_from_previous INTEGER DEFAULT 0,
                fetch_timestamp TEXT,
                notes TEXT
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn(db_path: str | None = None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        yield conn
    finally:
        conn.close()


def upsert_many(table: str, columns: Iterable[str], rows: Iterable[Iterable], db_path: str | None = None):
    rows = list(rows)
    if not rows:
        return
    cols = list(columns)
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c not in ("ticker", "date", "frequency")])
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT DO UPDATE SET {updates}"
    with get_conn(db_path) as conn:
        try:
            conn.execute("BEGIN")
            conn.executemany(sql, rows)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


def fetch_df(query: str, params: tuple = (), db_path: str | None = None):
    import pandas as pd

    with get_conn(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])  # type: ignore
    # Only index by date when the query actually returned a 'date' column
    # (aggregate queries like `SELECT MAX(date) as max_date` don't include it).
    if not df.empty and "date" in df.columns:
        df = df.sort_values("date").set_index("date")
    return df

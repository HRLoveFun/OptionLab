import logging
import os
import sqlite3
import threading
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("MARKET_DB_PATH", os.path.join(os.getcwd(), "market_data.sqlite"))

# ── Thread-local connection cache ────────────────────────────────
# SQLite connections are not safe to share across threads, but creating a new
# one per query is wasteful. We keep one persistent connection per (thread, path)
# and reuse it for the lifetime of the thread. PRAGMAs are applied once on first
# acquisition. Worker threads in a ThreadPoolExecutor get distinct connections.
_thread_local = threading.local()
# Track all opened connections so background tasks (tests, scheduler shutdown)
# can close them explicitly. Indexed by (thread_id, path).
_all_conns_lock = threading.Lock()
_all_conns: dict = {}


def _get_or_create_conn(path: str) -> sqlite3.Connection:
    """Return a persistent connection scoped to the current thread.

    Creates and caches one on first call per thread. Applies PRAGMAs once.
    """
    cache = getattr(_thread_local, "conns", None)
    if cache is None:
        cache = {}
        _thread_local.conns = cache
    conn = cache.get(path)
    if conn is not None:
        return conn

    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    cache[path] = conn
    with _all_conns_lock:
        _all_conns[(threading.get_ident(), path)] = conn
    logger.debug("Opened SQLite connection (thread=%s, path=%s)", threading.get_ident(), path)
    return conn


def close_thread_conn(db_path: str | None = None) -> None:
    """Close the current thread's cached connection(s).

    Safe to call from teardown hooks (tests, request teardown). If db_path is
    None, closes all cached connections for this thread.
    """
    cache = getattr(_thread_local, "conns", None)
    if not cache:
        return
    paths = [db_path or DB_PATH] if db_path else list(cache.keys())
    for p in paths:
        conn = cache.pop(p, None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
            with _all_conns_lock:
                _all_conns.pop((threading.get_ident(), p), None)


def close_all_conns() -> None:
    """Close every cached connection across all threads. Test/shutdown helper."""
    with _all_conns_lock:
        items = list(_all_conns.items())
        _all_conns.clear()
    for _, conn in items:
        try:
            conn.close()
        except sqlite3.Error:
            pass
    # Also clear current thread's cache so re-acquire works.
    if getattr(_thread_local, "conns", None) is not None:
        _thread_local.conns.clear()


def init_db(db_path: str | None = None):
    path = db_path or DB_PATH
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    conn = _get_or_create_conn(path)
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
    """Yield a per-thread persistent SQLite connection.

    The connection is cached for the lifetime of the calling thread (see
    `_get_or_create_conn`). The context manager does NOT close the connection
    on exit — call `close_thread_conn()` explicitly to release it. This
    matches the request lifecycle: a Flask worker thread reuses one connection
    across many queries, avoiding the per-call connect/PRAGMA cost.
    """
    path = db_path or DB_PATH
    conn = _get_or_create_conn(path)
    yield conn


def upsert_many(table: str, columns: Iterable[str], rows: Iterable[Iterable], db_path: str | None = None):
    rows = list(rows)
    if not rows:
        return
    cols = list(columns)
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{c}=excluded.{c}" for c in cols if c not in ("ticker", "date", "frequency")])
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT DO UPDATE SET {updates}"
    conn = _get_or_create_conn(db_path or DB_PATH)
    try:
        conn.execute("BEGIN")
        conn.executemany(sql, rows)
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


def fetch_df(query: str, params: tuple = (), db_path: str | None = None):
    import pandas as pd

    conn = _get_or_create_conn(db_path or DB_PATH)
    df = pd.read_sql_query(query, conn, params=params, parse_dates=["date"])  # type: ignore
    # Only index by date when the query actually returned a 'date' column
    # (aggregate queries like `SELECT MAX(date) as max_date` don't include it).
    if not df.empty and "date" in df.columns:
        df = df.sort_values("date").set_index("date")
    return df

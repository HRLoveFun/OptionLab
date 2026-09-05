"""Repository layer — the only place that builds SQL.

INVARIANT (doc_guard `db-access`): upper layers (routes/services) must import
these functions instead of touching ``data_pipeline.db`` connection primitives
directly, so WAL pragmas and the query cache apply uniformly (ADR 0003).

This module is part of ``data_pipeline`` (an I/O layer); importing
``data_pipeline.db`` here is the intended single exception and is not flagged
by the guardrail.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import Any

import pandas as pd

from data_pipeline.db import fetch_df, get_conn, init_db, upsert_many


# ── Health / data-quality inventory ─────────────────────────────────
def fetch_ticker_inventory() -> list[tuple[Any, ...]]:
    """Return one row per ticker from ``raw_prices`` with row counts + NaN tallies.

    Columns: ``(ticker, rows, latest_date, earliest_date, null_close,
    null_volume)`` ordered by ticker.
    """
    sql = """
        SELECT
            ticker,
            COUNT(*) AS rows,
            MAX(date) AS latest_date,
            MIN(date) AS earliest_date,
            SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) AS null_close,
            SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) AS null_volume
        FROM raw_prices
        GROUP BY ticker
        ORDER BY ticker
    """
    with get_conn() as conn:
        return conn.execute(sql).fetchall()


# ── Tracked strategies (portfolio positions) ───────────────────────
def insert_tracked_strategy(values: Iterable[Any]) -> int:
    """Insert a ``tracked_strategies`` row; return the new row id."""
    sql = """
        INSERT INTO tracked_strategies
          (ticker, template, expiry, entry_date, entry_spot,
           entry_net_premium, qty, legs_json, entry_meta_json,
           status, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """
    with get_conn() as conn:
        cur = conn.execute(sql, tuple(values))
        conn.commit()
        return cur.lastrowid


def select_tracked_strategies(cols: list[str], status: str | None) -> list[tuple[Any, ...]]:
    """Return selected ``tracked_strategies`` columns ordered by id DESC.

    When ``status`` is ``None`` every row is returned; otherwise only rows
    matching ``status`` are returned.
    """
    where = "WHERE status = ?" if status else ""
    params = (status,) if status else ()
    with get_conn() as conn:
        return conn.execute(
            f"SELECT {', '.join(cols)} FROM tracked_strategies {where} ORDER BY id DESC",
            params,
        ).fetchall()


def update_tracked_strategy_closed(position_id: int, closed_date: str, closed_value: float) -> int:
    """Mark a tracked strategy closed; return rowcount (0 == not found)."""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tracked_strategies SET status='closed', closed_date=?, closed_value=? WHERE id=?",
            (closed_date, float(closed_value), int(position_id)),
        )
        conn.commit()
        return cur.rowcount


# ── Market review (benchmark / instrument close panel) ────────────
def ensure_schema() -> None:
    """Bootstrap the SQLite schema (idempotent). Safe to call before any read."""
    init_db()


def fetch_market_review_latest_dates(tickers: list[str]) -> dict[str, str | None]:
    """Return ``{ticker: latest date string | None}`` from ``market_review_prices``."""
    out: dict[str, str | None] = {}
    with get_conn() as conn:
        for t in tickers:
            row = conn.execute("SELECT MAX(date) FROM market_review_prices WHERE ticker = ?", (t,)).fetchone()
            out[t] = row[0] if row and row[0] else None
    return out


def upsert_market_review_prices(rows: Iterable[tuple[str, str, float]]) -> None:
    """Insert or replace ``(ticker, date, close)`` rows in ``market_review_prices``."""
    rows = list(rows)
    if not rows:
        return
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO market_review_prices (ticker, date, close) "
            "VALUES (?, ?, ?) ON CONFLICT(ticker, date) DO UPDATE SET close=excluded.close",
            rows,
        )
        conn.commit()


def fetch_market_review_panel(range_start: str) -> pd.DataFrame:
    """Return ``market_review_prices`` rows with ``date >= range_start`` as a DataFrame."""
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT ticker, date, close FROM market_review_prices WHERE date >= ? ORDER BY date",
            conn,
            params=(range_start,),
            parse_dates=["date"],
        )


# ── Regime log ───────────────────────────────────────────────────
_REGIME_LOG_COLS = (
    "date",
    "vol_regime",
    "dir_regime",
    "vix_value",
    "sma_20",
    "sma_slope_5d",
    "close_vs_sma_pct",
    "regime_changed_from_previous",
    "fetch_timestamp",
    "notes",
)


def count_clean_rows(ticker: str) -> int:
    """Return how many priced rows the DB holds for ``ticker``."""
    ensure_schema()
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


def load_regime_log() -> pd.DataFrame:
    """Return the full persisted regime log, date-indexed and ascending."""
    ensure_schema()
    return fetch_df("SELECT * FROM regime_log ORDER BY date ASC")


def previous_regime_log_row(date: dt.date) -> dict | None:
    """Return the most recent log row strictly before ``date``, or None."""
    ensure_schema()
    df = fetch_df(
        "SELECT * FROM regime_log WHERE date < ? ORDER BY date DESC LIMIT 1",
        (date.isoformat(),),
    )
    if df.empty:
        return None
    return df.iloc[0].to_dict()


def upsert_regime_log_rows(rows: list[dict]) -> None:
    """Insert or replace regime_log rows (idempotent per date)."""
    if not rows:
        return
    ensure_schema()
    ordered = [tuple(r.get(c) for c in _REGIME_LOG_COLS) for r in rows]
    upsert_many("regime_log", _REGIME_LOG_COLS, ordered)


def fetch_regime_log_window(start: dt.date, end: dt.date) -> pd.DataFrame:
    """Return regime_log rows within ``[start, end]``, date-indexed, ascending."""
    ensure_schema()
    return fetch_df(
        "SELECT * FROM regime_log WHERE date>=? AND date<=? ORDER BY date ASC",
        (start.isoformat(), end.isoformat()),
    )

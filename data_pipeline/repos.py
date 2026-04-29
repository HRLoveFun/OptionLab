"""Repository pattern wrappers around the SQLite tables.

The original codebase intermixes raw SQL with feature logic inside
``data_pipeline/data_service.py`` and ``downloader.py``. As the schema grows
(adding aggregates, regimes, options snapshots etc.) this becomes painful to
test and replace.

These thin repositories give every persistence operation a named method on a
typed object, making it trivial to:

* mock at the test boundary (no patching of bare SQL strings),
* swap to PostgreSQL/Timescale later without touching call sites,
* discover all queries that hit a given table via "find references".

Existing call sites are NOT migrated wholesale — this module establishes the
pattern. New code should prefer the repository API; older modules can be
migrated incrementally.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from data_pipeline.db import get_conn


@dataclass(frozen=True)
class PriceRow:
    """A single OHLCV row from ``raw_prices`` / ``clean_prices``."""

    ticker: str
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: float | None


class PriceRepo:
    """Read/write access to the raw OHLCV table."""

    TABLE = "raw_prices"

    @classmethod
    def latest_date(cls, ticker: str) -> str | None:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT MAX(date) FROM {cls.TABLE} WHERE ticker = ?",
                (ticker.upper(),),
            ).fetchone()
        return row[0] if row else None

    @classmethod
    def row_count(cls, ticker: str) -> int:
        with get_conn() as conn:
            row = conn.execute(
                f"SELECT COUNT(*) FROM {cls.TABLE} WHERE ticker = ?",
                (ticker.upper(),),
            ).fetchone()
        return int(row[0] or 0) if row else 0

    @classmethod
    def get_range(
        cls,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Return raw OHLCV between ``start`` and ``end`` inclusive (ISO dates)."""
        clauses = ["ticker = ?"]
        params: list[Any] = [ticker.upper()]
        if start:
            clauses.append("date >= ?")
            params.append(start)
        if end:
            clauses.append("date <= ?")
            params.append(end)
        sql = (
            f"SELECT date, open, high, low, close, adj_close, volume "
            f"FROM {cls.TABLE} WHERE {' AND '.join(clauses)} ORDER BY date ASC"
        )
        with get_conn() as conn:
            df = pd.read_sql_query(sql, conn, params=params, parse_dates=["date"])
        df = df.set_index("date") if not df.empty else df
        return df

    @classmethod
    def upsert_many(cls, ticker: str, rows: Iterable[PriceRow]) -> int:
        """Insert-or-replace many rows. Returns count written."""
        payload = [
            (
                r.ticker.upper(),
                r.date,
                r.open,
                r.high,
                r.low,
                r.close,
                r.adj_close,
                r.volume,
            )
            for r in rows
            if r.ticker.upper() == ticker.upper()
        ]
        if not payload:
            return 0
        with get_conn() as conn:
            conn.executemany(
                f"INSERT OR REPLACE INTO {cls.TABLE} "
                "(ticker, date, open, high, low, close, adj_close, volume) "
                "VALUES (?,?,?,?,?,?,?,?)",
                payload,
            )
            conn.commit()
        return len(payload)


class CleanPriceRepo:
    """Read access to the cleaned-prices table."""

    TABLE = "clean_prices"

    @classmethod
    def get_range(
        cls,
        ticker: str,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        clauses = ["ticker = ?"]
        params: list[Any] = [ticker.upper()]
        if start:
            clauses.append("date >= ?")
            params.append(start)
        if end:
            clauses.append("date <= ?")
            params.append(end)
        sql = (
            f"SELECT date, open, high, low, close, adj_close, volume "
            f"FROM {cls.TABLE} WHERE {' AND '.join(clauses)} ORDER BY date ASC"
        )
        with get_conn() as conn:
            df = pd.read_sql_query(sql, conn, params=params, parse_dates=["date"])
        return df.set_index("date") if not df.empty else df

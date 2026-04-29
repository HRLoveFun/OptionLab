"""Tests for services/health_service.py."""

from __future__ import annotations

import pandas as pd

from data_pipeline.db import get_conn
from services.health_service import overall_summary, per_ticker_summary


def _seed(ticker: str, dates: list[str], close_vals: list[float | None]) -> None:
    from data_pipeline.db import init_db

    init_db()
    with get_conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO raw_prices (ticker,date,open,high,low,close,adj_close,volume) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [(ticker, d, 1.0, 1.0, 1.0, c, c, 100.0) for d, c in zip(dates, close_vals)],
        )
        conn.commit()


def test_per_ticker_summary_counts_rows_and_nans():
    _seed("AAA", ["2024-01-02", "2024-01-03", "2024-01-04"], [10.0, None, 12.0])
    rows = per_ticker_summary()
    aaa = next(r for r in rows if r["ticker"] == "AAA")
    assert aaa["rows"] == 3
    assert aaa["null_close"] == 1
    assert aaa["latest_date"] == "2024-01-04"


def test_overall_summary_marks_stale_and_nan():
    _seed("OLD", ["2020-01-02"], [50.0])
    today = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    _seed("FRESH", [today], [100.0])
    out = overall_summary()
    assert "OLD" in out["stale_tickers"]
    assert out["status"] in {"ok", "degraded"}
    assert out["ticker_count"] >= 2

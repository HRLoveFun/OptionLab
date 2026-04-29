"""Data quality monitoring service.

Provides aggregate health metrics over the SQLite cache: per-ticker latest
date, row counts, NaN counts, and basic freshness checks. Used by the
``/health/data`` endpoint and ad-hoc CLI inspection.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

from data_pipeline.db import get_conn

_FRESHNESS_DAYS = int(os.environ.get("DATA_FRESHNESS_DAYS", "5"))


def _last_business_day(today: date | None = None) -> date:
    """Return the most recent weekday (Mon–Fri) on or before ``today``."""
    d = today or date.today()
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


def per_ticker_summary() -> list[dict[str, Any]]:
    """Return a row per ticker with latest date, row count, and NaN counts."""
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
    out: list[dict[str, Any]] = []
    last_bday = _last_business_day().isoformat()
    threshold = (date.today() - timedelta(days=_FRESHNESS_DAYS)).isoformat()
    with get_conn() as conn:
        for row in conn.execute(sql).fetchall():
            ticker, rows, latest, earliest, null_close, null_volume = row
            stale = (latest or "") < threshold
            out.append(
                {
                    "ticker": ticker,
                    "rows": int(rows or 0),
                    "earliest_date": earliest,
                    "latest_date": latest,
                    "last_business_day": last_bday,
                    "stale": bool(stale),
                    "null_close": int(null_close or 0),
                    "null_volume": int(null_volume or 0),
                }
            )
    return out


def overall_summary() -> dict[str, Any]:
    """Aggregate health snapshot across the entire DB."""
    per = per_ticker_summary()
    total_rows = sum(t["rows"] for t in per)
    stale = [t["ticker"] for t in per if t["stale"]]
    nan_tickers = [t["ticker"] for t in per if t["null_close"] > 0]

    # Recent yfinance / pipeline failures from data_quality_log.
    try:
        from data_pipeline.quality_log import failure_counts, recent_failures

        failures_24h = failure_counts(hours=24)
        recent = recent_failures(hours=24, limit=20)
    except Exception:  # noqa: BLE001
        failures_24h = {}
        recent = []

    status = "ok"
    if stale or nan_tickers or failures_24h:
        status = "degraded"

    return {
        "status": status,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ticker_count": len(per),
        "total_rows": total_rows,
        "stale_tickers": stale,
        "tickers_with_nan_close": nan_tickers,
        "freshness_threshold_days": _FRESHNESS_DAYS,
        "failures_24h_by_class": failures_24h,
        "recent_failures": recent,
        "tickers": per,
    }

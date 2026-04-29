"""Data-quality logging — yfinance failures, scheduler errors, anomalies.

Writes one row per incident into ``data_quality_log``. Read paths live in
:mod:`services.health_service` (already aggregated by ``/health/data``).

The logger NEVER raises: a logging failure must not mask the original error
the caller is reporting. Callers may safely ``log_failure(...)`` from inside
``except`` blocks.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from data_pipeline.db import get_conn

_logger = logging.getLogger(__name__)


def log_failure(
    source: str,
    error_class: str,
    message: str = "",
    *,
    ticker: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Insert a row into ``data_quality_log``. Never raises.

    Parameters
    ----------
    source
        Subsystem reporting the failure: ``"yf_client"``, ``"scheduler"``,
        ``"cleaning"``, etc.
    error_class
        Short symbolic class: ``"rate_limited"``, ``"empty_dataframe"``,
        ``"network_error"``, ``"unhandled"``.
    message
        Free-form human-readable detail.
    ticker
        Optional ticker the failure relates to.
    details
        Optional structured payload (serialised as JSON).
    """
    try:
        ts = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(details, default=str) if details else None
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO data_quality_log (ts, ticker, source, error_class, message, details) "
                "VALUES (?,?,?,?,?,?)",
                (ts, ticker, source, error_class, message, payload),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — must not raise from logging path
        _logger.warning("data_quality_log write failed: %s", exc)


def recent_failures(hours: int = 24, limit: int = 100) -> list[dict[str, Any]]:
    """Return the most recent failure rows, newest first."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT ts, ticker, source, error_class, message FROM data_quality_log "
            "WHERE ts >= ? ORDER BY ts DESC LIMIT ?",
            (cutoff_iso, limit),
        )
        rows = cur.fetchall()
    return [
        {
            "ts": r[0],
            "ticker": r[1],
            "source": r[2],
            "error_class": r[3],
            "message": r[4],
        }
        for r in rows
    ]


def failure_counts(hours: int = 24) -> dict[str, int]:
    """Aggregate counts by ``error_class`` over a time window."""
    cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT error_class, COUNT(*) FROM data_quality_log "
            "WHERE ts >= ? GROUP BY error_class",
            (cutoff_iso,),
        )
        return {row[0]: int(row[1]) for row in cur.fetchall()}

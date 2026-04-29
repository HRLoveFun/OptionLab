"""Tests for data_pipeline/quality_log.py."""

from __future__ import annotations

from data_pipeline.db import init_db
from data_pipeline.quality_log import failure_counts, log_failure, recent_failures


def test_log_and_query_recent():
    init_db()
    log_failure("yf_client.test", "rate_limited", "429", ticker="AAPL")
    log_failure("scheduler", "unhandled", "boom", details={"job": "daily"})
    rows = recent_failures(hours=1)
    assert len(rows) >= 2
    assert any(r["error_class"] == "rate_limited" for r in rows)


def test_failure_counts_aggregates_by_class():
    init_db()
    for _ in range(3):
        log_failure("yf_client.test", "rate_limited", "x", ticker="MSFT")
    log_failure("yf_client.test", "download_error", "y", ticker="MSFT")
    counts = failure_counts(hours=1)
    assert counts.get("rate_limited", 0) >= 3
    assert counts.get("download_error", 0) >= 1


def test_log_failure_swallows_db_errors(monkeypatch):
    """Logging path must never raise — caller is in an except block."""
    import data_pipeline.quality_log as ql

    def boom(*a, **kw):
        raise RuntimeError("db down")

    monkeypatch.setattr(ql, "get_conn", boom)
    log_failure("test", "x", "msg")  # must not raise

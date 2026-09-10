"""Contract tests for the canonical store tables (ADR 0011, batch B2).

Domain:    Tests — Canonical Store
Context:
  - Batch B2 renamed the store tables to ``raw_bars`` / ``clean_bars`` /
    ``feature_bars`` and kept the pre-rename names as shadow tables for one
    release. These tests pin the two properties that make the compatibility
    window safe: the pairs have identical column sets, and a write under either
    name reaches both.
  - They also pin the *direction* of the migration — reads must hit the
    canonical names, and ``scripts/migrate_canonical_tables.py`` must backfill a
    DB that only has legacy rows.
Contracts:
  - Column-set parity per pair (decision gate §8 Q4 = minimal rename).
  - ``upsert_many`` mirrors canonical ↔ legacy in both directions.
  - A pipeline run (download → clean → process) populates both families.
  - ``fetch_ticker_inventory`` (the /health data source) reads the canonical table.
  - The one-shot migration backfills legacy-only rows into the canonical table.
Dependencies UPWARD:
  - (none — stdlib + pytest + the package under test)
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
from pathlib import Path

import pytest

from data_pipeline.db import CANONICAL_TABLES, canonical_table, get_conn, init_db, upsert_many

REPO_ROOT = Path(__file__).resolve().parent.parent

_RAW_COLS = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"]


def _table_info(table: str) -> list[tuple]:
    with get_conn() as conn:
        return [tuple(row) for row in conn.execute(f"PRAGMA table_info({table})")]


def _count(table: str, ticker: str | None = None) -> int:
    with get_conn() as conn:
        if ticker is None:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE ticker=?", (ticker,)).fetchone()[0])


# ---------------------------------------------------------------------------
# Column parity
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("legacy,canonical", sorted(CANONICAL_TABLES.items()))
def test_canonical_table_mirrors_legacy_columns(legacy, canonical):
    """Decision gate Q4 = minimal rename, so the column sets must be identical."""
    init_db()
    canon_info = _table_info(canonical)
    assert canon_info, f"{canonical} was not created by init_db()"
    assert canon_info == _table_info(legacy)


def test_canonical_table_is_identity_for_names_without_a_pair():
    assert canonical_table("raw_prices") == "raw_bars"
    assert canonical_table("raw_bars") == "raw_bars"
    assert canonical_table("regime_log") == "regime_log"


# ---------------------------------------------------------------------------
# Transitional dual-write
# ---------------------------------------------------------------------------
def test_upsert_many_writes_both_table_families():
    init_db()
    upsert_many("raw_bars", _RAW_COLS, [("DUAL_CANON", "2026-01-02", 1.0, 1.0, 1.0, 1.0, 1.0, 10.0, "yfinance")])
    assert _count("raw_bars", "DUAL_CANON") == 1
    assert _count("raw_prices", "DUAL_CANON") == 1

    # A legacy name must also reach the canonical table: old call sites and test
    # fixtures seed under the pre-rename names during the window.
    upsert_many("raw_prices", _RAW_COLS, [("DUAL_LEGACY", "2026-01-02", 2.0, 2.0, 2.0, 2.0, 2.0, 20.0, "yfinance")])
    assert _count("raw_prices", "DUAL_LEGACY") == 1
    assert _count("raw_bars", "DUAL_LEGACY") == 1


def test_pipeline_run_populates_both_table_families():
    """B2 exit criterion: one pipeline run leaves both families populated."""
    from data_pipeline.cleaning import clean_range
    from data_pipeline.downloader import upsert_raw_prices
    from data_pipeline.processing import process_frequencies

    ticker = "TEST_CANON"
    end = dt.date.today()
    start = end - dt.timedelta(days=45)

    init_db()
    assert upsert_raw_prices(ticker, start, end).ok
    assert clean_range(ticker, start, end).ok
    assert process_frequencies(ticker, start, end).ok

    for legacy, canonical in CANONICAL_TABLES.items():
        canonical_rows = _count(canonical, ticker)
        assert canonical_rows > 0, f"{canonical} was not written for {ticker}"
        assert canonical_rows == _count(legacy, ticker), f"{legacy} / {canonical} diverged"


# ---------------------------------------------------------------------------
# Reads target the canonical tables
# ---------------------------------------------------------------------------
def test_health_inventory_reads_canonical_table():
    """A row that exists only in ``raw_bars`` must be visible to the health read."""
    from data_pipeline.repos import fetch_ticker_inventory

    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO raw_bars (ticker,date,open,high,low,close,adj_close,volume) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ("CANON_ONLY", "2026-01-06", 7.0, 7.0, 7.0, 7.0, 7.0, 70.0),
        )
        conn.execute("DELETE FROM raw_prices WHERE ticker=?", ("CANON_ONLY",))
        conn.commit()

    rows = [r for r in fetch_ticker_inventory() if r[0] == "CANON_ONLY"]
    assert rows, "fetch_ticker_inventory did not read raw_bars"
    assert rows[0][1] == 1


# ---------------------------------------------------------------------------
# One-shot backfill script
# ---------------------------------------------------------------------------
def test_migration_script_backfills_legacy_only_rows():
    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO raw_prices (ticker,date,close) VALUES (?,?,?)",
            ("LEGACY_ONLY", "2026-01-05", 42.0),
        )
        conn.execute("DELETE FROM raw_bars WHERE ticker=?", ("LEGACY_ONLY",))
        conn.commit()

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "migrate_canonical_tables.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    with get_conn() as conn:
        row = conn.execute("SELECT close FROM raw_bars WHERE ticker=?", ("LEGACY_ONLY",)).fetchone()
    assert row is not None and row[0] == pytest.approx(42.0)


def test_migration_dry_run_has_no_side_effects():
    """`--dry-run` must report without creating or copying anything."""
    import os

    db_file = os.environ["MARKET_DB_PATH"]
    init_db(db_file)
    with get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS raw_bars")
        conn.execute(
            "INSERT OR REPLACE INTO raw_prices (ticker,date,close) VALUES (?,?,?)",
            ("DRY_RUN", "2026-01-05", 3.0),
        )
        conn.commit()

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "migrate_canonical_tables.py"), "--db", db_file, "--dry-run"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nothing written" in result.stdout

    with get_conn() as conn:
        created = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='raw_bars'").fetchone()[
            0
        ]
    assert created == 0, "dry run created the canonical table"


def test_migration_script_is_idempotent():
    """Re-running the backfill must not duplicate or clobber canonical rows."""
    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO raw_prices (ticker,date,close) VALUES (?,?,?)",
            ("IDEMPOTENT", "2026-01-05", 1.0),
        )
        conn.commit()

    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "migrate_canonical_tables.py")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    assert _count("raw_bars", "IDEMPOTENT") == 1

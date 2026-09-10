#!/usr/bin/env python3
"""One-shot backfill of the canonical tables from the pre-rename ones.

Domain:    Data Pipeline — canonical table names (ADR 0011, batch B2)
Context:
  - Batch B2 renamed the store tables (: ``raw_prices``/``clean_prices``/
    ``processed_prices`` → ``raw_bars``/``clean_bars``/``feature_bars``). The
    pipeline now reads and writes the canonical names, and writes the legacy
    names too for one release (see ``data_pipeline/db.py::_TABLE_SHADOWS``), but
    a DB created *before* B2 only has rows under the legacy names.
  - This script copies legacy → canonical so an existing ``market_data.sqlite``
    becomes readable by the new code without waiting for a re-download.
  - It is deliberately NOT a migration framework (constraints §3): no version
    table, no ordering, no schema changes — just an idempotent row copy.
Contracts:
  - Idempotent: ``INSERT OR IGNORE``, so re-running is a no-op.
  - Never overwrites the canonical table (canonical wins on a conflict), so it
    is safe to run after the pipeline has already written new data.
  - Column sets must match; a mismatch aborts with a non-zero exit code instead
    of silently dropping columns.
Usage:
    python scripts/migrate_canonical_tables.py [--db PATH] [--dry-run]
Dependencies:
  - data_pipeline.db (schema + connection pragmas); stdlib only otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.db import CANONICAL_TABLES, DB_PATH, get_conn, init_db  # noqa: E402


def _columns(conn, table: str) -> list[str]:
    """Return the column names of ``table`` (empty when it does not exist)."""
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _count(conn, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _copy_table(conn, legacy: str, canonical: str) -> int:
    """Copy ``legacy`` → ``canonical``; return how many rows were added."""
    legacy_cols = _columns(conn, legacy)
    canonical_cols = _columns(conn, canonical)
    if not legacy_cols:
        print(f"  {legacy}: absent — nothing to do")
        return 0
    dropped = [c for c in legacy_cols if c not in canonical_cols]
    if dropped:
        sys.exit(
            f"[migrate] {canonical} is missing column(s) {dropped} present in {legacy}; "
            "refusing to drop data — fix the schema first"
        )
    before = _count(conn, canonical)
    cols = ",".join(legacy_cols)
    conn.execute(f"INSERT OR IGNORE INTO {canonical} ({cols}) SELECT {cols} FROM {legacy}")
    conn.commit()
    added = _count(conn, canonical) - before
    print(f"  {legacy} → {canonical}: +{added} row(s) (canonical now {before + added})")
    return added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None, help="override the DB path (default: MARKET_DB_PATH / data/)")
    ap.add_argument("--dry-run", action="store_true", help="report what would be copied, change nothing")
    args = ap.parse_args()

    if args.dry_run:
        # WHY: a dry run must have NO side effects — in particular it must not
        # create the canonical tables, otherwise "dry" would already have
        # changed the database it is reporting on.
        db_file = Path(args.db) if args.db else Path(DB_PATH)
        if not db_file.exists():
            sys.exit(f"[migrate] no database at {db_file}")
        with get_conn(str(db_file)) as conn:
            for legacy, canonical in CANONICAL_TABLES.items():
                legacy_n = _count(conn, legacy) if _columns(conn, legacy) else 0
                canonical_n = _count(conn, canonical) if _columns(conn, canonical) else 0
                print(f"  {legacy} ({legacy_n} rows) → {canonical} ({canonical_n} rows)")
        print(f"[migrate] dry run on {db_file} — nothing written")
        return 0

    init_db(args.db)
    with get_conn(args.db) as conn:
        print("[migrate] copying pre-rename tables into the canonical store")
        total = sum(_copy_table(conn, legacy, canonical) for legacy, canonical in CANONICAL_TABLES.items())
    print(f"[migrate] done — {total} row(s) backfilled")
    return 0


if __name__ == "__main__":
    sys.exit(main())

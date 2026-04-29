# 0003. SQLite + WAL for Single-Machine Deployment

- **Status**: Accepted
- **Date**: 2025-01-15 (retroactive)
- **Deciders**: project author

## Context

We need to persist OHLCV history, processed indicators, scheduler job state, and quality logs.
Workload is dominated by reads (UI requests) with occasional writes (scheduler jobs every few minutes).
The app runs on a single machine — laptop or small VPS.

## Options Considered

1. **PostgreSQL** — robust, but requires running a separate server, backups, migrations. Heavy.
2. **DuckDB** — great for analytics, but write-heavy concurrent access still maturing.
3. **MySQL** — no advantages over Postgres for this use case.
4. **SQLite (default journal mode)** — simple but writers block readers.
5. **SQLite + WAL mode** — readers and one writer concurrent, fast enough for our scale.

## Decision

SQLite with `journal_mode=WAL` and `synchronous=NORMAL`, applied via `PRAGMA` on every connection
in `data_pipeline/db.py`.

Connections are **thread-local** (cached per-thread) because:
- SQLite connections are not safe to share across threads.
- Per-query reconnect adds overhead and re-applies PRAGMAs unnecessarily.
- One persistent connection per worker thread is the documented sweet spot.

## Consequences

- **Positive**: zero ops overhead; the entire DB is one file (`market_data.sqlite`).
- **Positive**: WAL allows the scheduler to write while UI reads — no blocking.
- **Trade-off — `synchronous=NORMAL`**: small risk of losing the last committed transaction on power loss. Acceptable for market data we can re-download.
- **Trade-off — no migration framework**: schemas use `CREATE TABLE IF NOT EXISTS`. Breaking changes need manual SQL in `scripts/`.
- **Limit**: this design will not scale to multi-machine. If needed, switch to Postgres (new ADR superseding this one).

## References

- `data_pipeline/db.py` — `_get_or_create_conn`, PRAGMA setup
- [SQLite WAL documentation](https://www.sqlite.org/wal.html)

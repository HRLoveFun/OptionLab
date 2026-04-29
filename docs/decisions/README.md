# Architecture Decision Records

This folder records significant decisions about the codebase: **why** something is built this way,
**what alternatives were considered**, and **what we accept as consequences**.

## When to write an ADR

Write a new ADR when you:
- Choose between materially different technical approaches.
- Lock in a constraint that future contributors might want to challenge.
- Remove or change a previously-recorded decision (link the superseding ADR).
- Adopt a non-obvious workaround for an external system bug.

You do **not** need an ADR for routine bug fixes, refactors that don't change behaviour, or documentation tweaks.

## Format

Copy [`TEMPLATE.md`](TEMPLATE.md), name the file `NNNN-short-title.md` (4-digit zero-padded sequence),
and fill in every section. Keep ADRs short — 1 page is ideal, 2 pages max.

## Status lifecycle

- **Proposed** — under discussion.
- **Accepted** — in force; reflected in code.
- **Superseded by NNNN** — replaced by a later ADR (link it).
- **Deprecated** — no longer applies but kept for historical context.

## Index

| ID | Title | Status |
|----|-------|--------|
| [0001](0001-three-layer-architecture.md) | Three-Layer Architecture | Accepted |
| [0002](0002-yfinance-as-sole-data-source.md) | yfinance as Sole Market Data Source | Accepted |
| [0003](0003-sqlite-wal-single-machine.md) | SQLite + WAL for Single-Machine Deployment | Accepted |
| [0004](0004-no-iv-history-from-yfinance.md) | No IV Rank / IV History from yfinance — Use HV Percentile | Accepted |
| [0005](0005-token-bucket-throttle.md) | Token-Bucket Throttle for yfinance Calls | Accepted |
| [0006](0006-vanilla-js-frontend.md) | Vanilla JS Frontend, No Build Step | Accepted |

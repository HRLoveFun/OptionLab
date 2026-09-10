# 0011. Pluggable Data-Provider Seam & Canonical Internal Schema

- **Status**: Accepted
- **Date**: 2026-09-10
- **Deciders**: repo owner

> **Accepted as a target, implemented in stages.** The layer moves, guard rules
> and `constraints.md` §1 amendment land batch-by-batch per
> [`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md) §6
> (B1–B4). Until a batch lands, the current code still stands.

## Context

[ADR 0002](0002-yfinance-as-sole-data-source.md) locked yfinance as the only
market-data source, and [`docs/constraints.md`](../constraints.md) §1 treats that
as a hard constraint. In practice this has leaked into the *shape* of the code,
not just the choice of vendor:

- `data_pipeline/raw_prices` **is** yfinance's column set. `downloader._download_yf`
  only renames `Adj Close`→`Adj_Close`; there is no canonical schema.
- Two modules import `yfinance` — `data_pipeline/yf_client.py` (the documented
  chokepoint) and `data_pipeline/downloader.py` (a registered
  `# doc-guard: allow=single-yf-exit` exception).
- `core/market/data_context.py` reaches down into `data_pipeline` to do its own
  fetching (2× `# doc-guard: allow=core-purity`).
- `services/market_review/fetch.py` runs a *second*, parallel acquisition path
  (its own L1/L2/L3 cache ladder writing `market_review_prices`).

The owner now wants acquisition to be able to accept "various APIs" by mapping
their fields onto one internal table. The immediate decision is **not** to add a
second vendor — it is whether to build the seam that would make a second vendor a
localised change instead of a cross-cutting rewrite.

Forces:

- This is a personal research tool; paid feeds are still not in scope (ADR 0002's
  cost argument stands).
- yfinance has no stable schema and breaks on releases — a mapping layer is useful
  even with one vendor, because it pins the internal contract.
- `docs/constraints.md` §3 forbids a migration framework; §6 forbids a job queue.
- `archive/futu_integration/field_mapping.md` already documents a futu↔yfinance
  field map from a previous integration attempt, so the "second provider" shape is
  known enough to design against.

## Options Considered

1. **Do nothing — keep yfinance-shaped storage.**
   - Pros: zero work; ADR 0002 unchanged.
   - Cons: a second provider (or a yfinance schema break) is a pipeline-wide
     rewrite; `core-purity` / `single-yf-exit` debt stays open; the owner's
     request is unmet.

2. **Full multi-provider now — add futu (or Polygon) alongside yfinance.**
   - Pros: delivers a real second source.
   - Cons: new paid/credentialed dependency; doubles the acquisition test surface;
     the canonical schema would be designed against a moving target under time
     pressure. Explicitly out of scope per the 2026-09-10 decision.

3. **Build the seam only — provider adapter protocol + canonical schema, yfinance
   as the sole implementation.**
   - Pros: localises any future vendor to one `providers/*.py` file; pins the
     internal contract against yfinance schema drift; lets `transform/` and
     `read/` stop importing `providers/` at all (checkable); closes L1/L2/L5.
   - Cons: a rename/re-home churn across `data_pipeline/`; `arch_baseline` resets;
     one round of "why is there an abstraction with a single impl" until the
     second impl exists.

## Decision

We choose **Option 3**. `data_pipeline/` is re-homed into stages with a one-way
call graph, and acquisition moves behind a provider protocol:

```
data_pipeline/
  providers/    base.py (MarketDataProvider protocol + Canonical* dataclasses)
                yfinance_provider.py (maps yfinance → canonical; sole `import yfinance`)
                _registry.py (name → instance; env-selected, default "yfinance")
  ingest/       gap detection + chunking + upsert into raw_* (was downloader + _range loop)
  transform/    cleaning.py, processing.py — canonical in, canonical out
  store/        db.py, repos.py — schema + the only SQL
  read/         facade.py (DataService), _query.py — the read API for services
  orchestrate/  readiness.py, backfill.py, scheduler.py, job_cache.py
```

Canonical tables (`CREATE TABLE IF NOT EXISTS`, no migration framework):

| Table | Columns |
|---|---|
| `raw_bars` | `provider, symbol, date, open, high, low, close, adj_close, volume` |
| `clean_bars` | today's `clean_prices` columns |
| `feature_bars` | today's `processed_prices` columns |

Live option/spot data stays **not persisted** (ADR 0004 unchanged) but is returned
as canonical `OptionChainSnapshot` / `float` from the provider, never as yfinance
objects.

**ADR 0002 is amended, not superseded**: "yfinance is the only data source" becomes
"yfinance is the only data-source *implementation*; it lives behind
`data_pipeline/providers/` and may be joined by others without touching
`transform/`, `read/`, `services/` or `core/`." The option-history caveats
(no IV rank / percentile / backtests — ADR 0004) are unchanged.

## Consequences

- Positive: a second provider is one file + one registry line + a field-map test.
  `transform/` / `read/` become provider-agnostic and enforceably so. The
  `single-yf-exit` and both `core-purity` debt rows close.
- Positive: the canonical schema pins the internal contract, so a yfinance schema
  break is contained in `yfinance_provider.py`.
- Negative / accepted: churn across `data_pipeline/` imports and docstrings;
  `arch_baseline.json` / `tag_baseline.json` reset; old `raw_prices` etc. kept for
  one release alongside the canonical tables (a one-shot copy script, not a
  migration).
- Negative / accepted: an abstraction with a single implementation until a second
  provider is actually written.
- Follow-up: implementation batches B1–B4 in
  [`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md) §6;
  update `docs/constraints.md` §1, `docs/l0_architecture.md`,
  `docs/architecture_review.md` §2, and `scripts/doc_guard.py::_ALLOWED_DEPS`
  in the same batches.

## References

- Related code: `data_pipeline/yf_client.py`, `data_pipeline/downloader.py`,
  `data_pipeline/data_ops/_range.py`, `data_pipeline/db.py`,
  `core/market/data_context.py`, `services/market_review/fetch.py`
- Related ADR: [0002](0002-yfinance-as-sole-data-source.md) (amended),
  [0004](0004-no-iv-history-from-yfinance.md) (unchanged),
  [0005](0005-token-bucket-throttle.md) (throttle stays in the provider),
  [0012](0012-parameter-ownership-and-prefetch.md) (consumes `read/` + `orchestrate/`)
- Plan: [`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md)
- External: `archive/futu_integration/field_mapping.md`

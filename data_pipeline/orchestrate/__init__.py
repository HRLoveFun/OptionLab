"""ORCHESTRATE — the "make the data ready" layer.

Domain:    Data Pipeline — Orchestrate
Context:
  - ADR 0011: this package owns everything that *sequences* the pipeline:
    the incremental/full update drivers, the chunked backfill loop, the
    streaming slice memo, and the optional cron scheduler. It is the only
    layer allowed to call ingest + transform + store together.
  - CONSTRAINT (docs/constraints.md §6): no job queue. Work either runs inside
    a request or on a bounded daemon thread with an 8s grace window.
Contracts:
  - ``update.manual_update`` / ``update.seed_history`` — the pipeline drivers.
  - ``backfill.ensure_range`` / ``backfill.needs_backfill`` — chunked coverage repair.
  - ``job_cache`` — TTL'd streaming slice memo (``create_job`` / ``compute_or_get``).
  - ``scheduler`` — optional APScheduler entry point (leader-locked).
Dependencies UPWARD:
  - ingest, transform, store, data_pipeline (PipelineResult + _state)
Dependencies DOWNWARD:
  - services/, routes/, app.py
"""

from __future__ import annotations

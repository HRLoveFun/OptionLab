"""READ — the DB-first read API services call.

Domain:    Data Pipeline — Read
Context:
  - ADR 0011: ``DataService`` is the single entry point above ``data_pipeline/``.
    It is DB-first and, when coverage is missing, triggers the orchestration
    layer rather than downloading inline (that is why this package may import
    ``orchestrate`` — see the layer table in docs/architecture_review.md §3).
Contracts:
  - ``DataService`` — the facade used by services/, routes/ and app.py.
  - ``_query`` — memoised reads with in-flight de-duplication.
Dependencies UPWARD:
  - store, orchestrate (refresh triggers), providers (spot fallback)
Dependencies DOWNWARD:
  - services/, routes/
"""

from __future__ import annotations

from data_pipeline.read.facade import DataService

__all__ = ["DataService"]

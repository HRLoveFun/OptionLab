"""STORE — schema, SQL, and the failure log.

Domain:    Data Pipeline — Store
Context:
  - ADR 0011 split ``data_pipeline/`` into stages. This package owns the SQLite
    boundary: the schema, the only SQL builder, and the ``data_quality_log``
    writer. Nothing here knows about vendors, pandas transforms, or Flask.
Contracts:
  - ``db`` — connections (thread-local WAL), ``init_db``, ``upsert_many``, ``fetch_df``.
  - ``repos`` — the only place that builds SQL.
  - ``quality_log`` — the append-only fetch-failure log.
Dependencies UPWARD:
  - (none — stdlib + pandas only)
Dependencies DOWNWARD:
  - everything above: providers, ingest, transform, read, orchestrate
"""

from __future__ import annotations

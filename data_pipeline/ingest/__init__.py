"""INGEST — acquisition → store glue.

Domain:    Data Pipeline — Ingest
Context:
  - ADR 0011: ``providers/`` touches the external API and returns canonical
    data; this package is the glue that decides *what* to fetch (business-day
    gap detection, the auto-backfill cap) and writes it to ``raw_bars``.
  - Live snapshots (spot / option chain) have no ingest module on purpose: they
    are never persisted (ADR 0004), so there is nothing to ingest — callers go
    to ``providers`` directly.
Contracts:
  - ``ohlcv.download_bars`` — canonical bars for a window, provider-agnostic.
  - ``ohlcv.upsert_raw_prices`` — never raises; degrades through ``PipelineResult``.
Dependencies UPWARD:
  - providers (acquisition), store (raw_bars), data_pipeline (PipelineResult)
Dependencies DOWNWARD:
  - orchestrate (the "make it ready" driver)
"""

from __future__ import annotations

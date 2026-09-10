"""Compatibility shim over the yfinance provider seam.

Domain:    Data Pipeline — yfinance compatibility surface
Context:
  - Batch B1 (docs/plans/business_line_reorg.md §6) moved every yfinance call
    into ``data_pipeline/providers/``. This module is kept for one release so the
    existing importers (``services/``, ``data_pipeline/read/``) do not have to
    change in the same PR as the extraction. See ADR 0011. (``core/`` used to
    import it too; batch B4 removed that — ``core`` no longer touches
    ``data_pipeline``.)
  - New code should import from ``data_pipeline.providers`` (canonical shapes)
    instead of here.
Contracts:
  - Re-exports the legacy function contracts unchanged: ``fetch_spot``,
    ``fetch_spots_bulk``, ``fetch_option_chain``, ``fetch_close_panel``,
    ``fetch_daily_ohlcv``.
Design rules:
  - CONSTRAINT: this module must not import ``yfinance``; the single exit point
    is ``data_pipeline/providers/`` (enforced by doc_guard ``single-yf-exit``).
Dependencies UPWARD:
  - providers/yf_snapshot (live snapshots), providers/yfinance_provider (bars)
Dependencies DOWNWARD:
  - services/*, data_pipeline/read/*
"""

from __future__ import annotations

from data_pipeline.providers.yf_snapshot import fetch_option_chain, fetch_spot, fetch_spots_bulk
from data_pipeline.providers.yfinance_provider import fetch_close_panel, fetch_daily_ohlcv

__all__ = [
    "fetch_close_panel",
    "fetch_daily_ohlcv",
    "fetch_option_chain",
    "fetch_spot",
    "fetch_spots_bulk",
]

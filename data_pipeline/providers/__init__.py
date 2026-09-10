"""Data-provider seam — the only package that touches an external market-data API.

Domain:    Data Pipeline — Providers
Context:
  - ADR 0011. Every external acquisition call lives under this package and is
    mapped onto the canonical schema in ``providers/base.py``; processing and
    serving stay provider-agnostic.
  - ``yf_client.py`` is a compatibility shim over this package for one release;
    ``downloader.py`` keeps only gap detection + DB upsert.
Contracts:
  - ``get_provider(name=None)``: resolve a ``MarketDataProvider`` implementation.
  - ``available_providers()``: registered provider names.
  - Canonical shapes: ``CanonicalBar`` / ``OptionLeg`` / ``OptionChainSnapshot``.
Dependencies UPWARD:
  - (none)
Dependencies DOWNWARD:
  - providers/base, providers/_registry, providers/yfinance_provider,
    providers/yf_snapshot
"""

from __future__ import annotations

from data_pipeline.providers._registry import available_providers, get_provider
from data_pipeline.providers.base import (
    CANONICAL_BAR_COLUMNS,
    CANONICAL_LEG_COLUMNS,
    CanonicalBar,
    MarketDataProvider,
    OptionChainSnapshot,
    OptionLeg,
    bars_to_frame,
)

__all__ = [
    "CANONICAL_BAR_COLUMNS",
    "CANONICAL_LEG_COLUMNS",
    "CanonicalBar",
    "MarketDataProvider",
    "OptionChainSnapshot",
    "OptionLeg",
    "available_providers",
    "bars_to_frame",
    "get_provider",
]

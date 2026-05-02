"""Portfolio P&L attribution and Greeks aggregation — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.portfolio
  from core.portfolio import Position, aggregate_greeks, attribute_pnl

This module re-exports the canonical implementation from core.portfolio.*
to preserve existing import paths.
"""

from core.portfolio.attribution import attribute_pnl
from core.portfolio.greeks import aggregate_greeks, leg_greeks
from core.portfolio.models import Position

__all__ = [
    "Position",
    "leg_greeks",
    "aggregate_greeks",
    "attribute_pnl",
]

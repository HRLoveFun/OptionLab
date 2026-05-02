"""Portfolio P&L attribution and Greeks aggregation.

Dependency graph:
    models.py      # Position dataclass
    greeks.py      # Per-leg Greeks
    attribution.py # First-order Taylor P&L attribution
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

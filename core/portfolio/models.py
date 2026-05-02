"""Portfolio data contracts.

Domain:    Portfolio Analysis
Contracts:
  - Position: ticker, legs, entry_date, entry_spot, entry_net_premium, qty
Dependencies UPWARD:
  - dataclasses, datetime
Dependencies DOWNWARD:
  - core.portfolio.greeks, core.portfolio.attribution
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.strategies.models import Leg


@dataclass
class Position:
    """A single open multi-leg position."""

    ticker: str
    legs: list[Leg]
    entry_date: date
    entry_spot: float
    entry_net_premium: float
    qty: int = 1

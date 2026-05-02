"""Decision process data contracts.

Domain:    Option Decision
Contracts:
  - Candidate: placeholder for structured candidate row
Dependencies UPWARD:
  - dataclasses
Dependencies DOWNWARD:
  - core.decision.*
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Candidate:
    """A single option candidate with enriched metrics."""

    strike: float
    dte: int
    expiry: str
    bid: float
    ask: float
    last_price: float
    mid_price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float
    derived: dict[str, Any] = field(default_factory=dict)
    ev: float = 0.0
    ev_ratio: float = 0.0

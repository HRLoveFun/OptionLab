"""Strategy data contracts.

Domain:    Strategy Analysis
Contracts:
  - Leg: side, option_type, strike, premium, qty, dte, iv
Dependencies UPWARD:
  - dataclasses
Dependencies DOWNWARD:
  - core.strategies.*, core.portfolio
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OptionType = Literal["call", "put"]
LegSide = Literal["long", "short"]


@dataclass
class Leg:
    """A single option leg."""

    side: LegSide
    option_type: OptionType
    strike: float
    premium: float
    qty: int = 1
    dte: int = 30
    iv: float = 0.25

    @property
    def sign(self) -> int:
        return 1 if self.side == "long" else -1

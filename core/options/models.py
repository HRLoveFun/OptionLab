"""Data contracts for the options analysis domain.

Domain:    Options Analysis
Context:
  - Lightweight dataclasses for option legs, Greeks snapshots, and chain rows.
Contracts:
  - GreeksSnapshot: delta, gamma, theta, vega, bs_price, intrinsic, time_value
  - OptionLeg: side, option_type, strike, premium, qty, dte, iv
Dependencies UPWARD:
  - dataclasses, typing
Dependencies DOWNWARD:
  - core.options.greeks, core.options.chain, core.strategies
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OptionType = Literal["call", "put"]
LegSide = Literal["long", "short"]


@dataclass(frozen=True)
class GreeksSnapshot:
    """Immutable Greeks for a single option contract."""

    delta: float
    gamma: float
    theta: float
    vega: float
    bs_price: float
    intrinsic: float
    time_value: float


@dataclass
class OptionLeg:
    """A single option leg (replaces strategies.Leg to unify naming)."""

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

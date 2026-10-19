"""Data contracts for the option-portfolio simulator.

Domain:    Option Simulation — Models
Context:
  - Inputs are hypothetical: the caller states spot, rates and an IV smile;
    nothing here reads market data.
  - Legs reuse ``core.strategies.models.Leg`` so strategy-builder output can be
    simulated directly. ``Leg.premium`` is the entry price per share and is the
    P&L reference; the builders below fill it with the model price at entry.
  - IVs are sticky-strike: each leg keeps its own IV as spot and time move.
Contracts:
  - Market(spot, rate, div_yield)
  - Smile(atm_iv, skew, curvature, floor).iv(strike, spot) -> float
  - Position(legs, style, multiplier, product, name)
  - make_leg(kind, side, strike, dte, market, smile|iv, qty, style) -> Leg
  - strike_for_delta(kind, delta, dte, market, smile, step) -> float
Dependencies UPWARD:
  - core.strategies.models, core.optsim.pricing
Dependencies DOWNWARD:
  - core.optsim.engine, core.optsim.margin, scripts/optsim.py, tests
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.optsim.pricing import european, option_greeks
from core.strategies.models import Leg

STYLES = ("european", "american")


@dataclass(frozen=True)
class Market:
    """Hypothetical market state at entry."""

    spot: float
    rate: float = 0.045
    div_yield: float = 0.0


@dataclass(frozen=True)
class Smile:
    """Parametric IV smile in log-moneyness k = ln(K/S): atm + skew·k + ½·curvature·k²."""

    atm_iv: float
    skew: float = 0.0
    curvature: float = 0.0
    floor: float = 0.05

    def iv(self, strike: float, spot: float) -> float:
        k = math.log(strike / spot)
        return max(self.floor, self.atm_iv + self.skew * k + 0.5 * self.curvature * k * k)


@dataclass
class Position:
    """A multi-leg option position; ``style`` and ``product`` apply to every leg."""

    legs: list[Leg]
    style: str = "european"
    multiplier: int = 100
    product: str = "index"
    name: str = ""

    def __post_init__(self) -> None:
        if self.style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}, got {self.style!r}")
        if not self.legs:
            raise ValueError("a position needs at least one leg")


def make_leg(
    kind: str,
    side: str,
    strike: float,
    dte: int,
    market: Market,
    *,
    smile: Smile | None = None,
    iv: float | None = None,
    qty: int = 1,
    style: str = "european",
) -> Leg:
    """Build a Leg whose IV comes from ``iv`` or ``smile`` and whose premium is the model price."""
    if iv is None:
        if smile is None:
            raise ValueError("give either iv or smile")
        iv = smile.iv(strike, market.spot)
    price = option_greeks(kind, market.spot, strike, dte / 365.0, market.rate, market.div_yield, iv, style)["price"]
    return Leg(side=side, option_type=kind, strike=float(strike), premium=float(price), qty=qty, dte=dte, iv=float(iv))


def strike_for_delta(
    kind: str, delta: float, dte: int, market: Market, smile: Smile, step: float | None = None
) -> float:
    """Strike whose Black-Scholes delta (smile IV) equals ``delta``; e.g. -0.16 for a 16-delta put."""
    if (kind == "call") != (delta > 0):
        raise ValueError("call deltas are positive, put deltas negative")
    T = dte / 365.0
    lo, hi = market.spot * 0.2, market.spot * 3.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        d = float(
            european(kind, market.spot, mid, T, market.rate, market.div_yield, smile.iv(mid, market.spot))["delta"]
        )
        if d > delta:  # both call and put deltas fall as the strike rises
            lo = mid
        else:
            hi = mid
    strike = 0.5 * (lo + hi)
    if step:
        strike = round(strike / step) * step
    return float(strike)

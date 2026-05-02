"""Payoff curve computation at expiration.

Domain:    Strategy Analysis — Payoff
Contracts:
  - payoff_at_expiration(legs, prices) -> np.ndarray
  - net_premium(legs) -> float
  - find_breakevens(prices, pnl) -> list[float]
Dependencies UPWARD:
  - numpy
Dependencies DOWNWARD:
  - services.strategy_service, core.strategies.greeks
"""

from __future__ import annotations

import numpy as np

from core.strategies.models import Leg


def payoff_at_expiration(legs: list[Leg], prices: np.ndarray) -> np.ndarray:
    """Per-share P&L at expiration."""
    pnl = np.zeros_like(prices, dtype=float)
    for leg in legs:
        if leg.option_type == "call":
            intrinsic = np.maximum(prices - leg.strike, 0.0)
        else:
            intrinsic = np.maximum(leg.strike - prices, 0.0)
        pnl += leg.sign * leg.qty * (intrinsic - leg.premium)
    return pnl


def net_premium(legs: list[Leg]) -> float:
    """Negative = debit paid; positive = credit received."""
    return float(sum(-leg.sign * leg.qty * leg.premium for leg in legs))


def find_breakevens(prices: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Return all prices where P&L crosses zero (linear interpolation)."""
    breakevens: list[float] = []
    sign = np.sign(pnl)
    sign_changes = np.where(np.diff(sign) != 0)[0]
    for i in sign_changes:
        x0, x1 = prices[i], prices[i + 1]
        y0, y1 = pnl[i], pnl[i + 1]
        if y1 == y0:
            continue
        be = x0 - y0 * (x1 - x0) / (y1 - y0)
        breakevens.append(round(float(be), 4))
    return breakevens

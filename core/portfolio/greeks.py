"""Portfolio Greeks computation.

Domain:    Portfolio Analysis — Greeks
Contracts:
  - leg_greeks(leg, spot) -> dict[str, float]
  - aggregate_greeks(positions, spots) -> dict
Dependencies UPWARD:
  - core.options.greeks.black_scholes
  - core.strategies.models
Dependencies DOWNWARD:
  - services.portfolio_analysis_service
"""

from __future__ import annotations

from typing import Any

from core.options.greeks.black_scholes import greeks_vectorized
from core.portfolio.models import Position
from core.strategies.models import Leg


def leg_greeks(leg: Leg, spot: float, r: float = 0.05) -> dict[str, float]:
    """Per-share Greeks for a single leg at given spot."""
    T = max(leg.dte, 1) / 365.0
    g = greeks_vectorized(spot, leg.strike, T, r, leg.iv, option_type=leg.option_type)
    sign = 1 if leg.side == "long" else -1
    return {
        "delta": float(g["delta"]) * sign * leg.qty,
        "gamma": float(g["gamma"]) * sign * leg.qty,
        "theta": float(g["theta"]) * sign * leg.qty,
        "vega": float(g["vega"]) * sign * leg.qty,
        "bs_price": float(g["bs_price"]),
    }


def aggregate_greeks(positions: list[Position], spots: dict[str, float]) -> dict[str, Any]:
    """Net Greeks across positions (and per-ticker breakdown)."""
    by_ticker: dict[str, dict[str, float]] = {}
    net = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for pos in positions:
        spot = spots.get(pos.ticker)
        if spot is None or spot <= 0:
            continue
        slot = by_ticker.setdefault(pos.ticker, {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0})
        for leg in pos.legs:
            g = leg_greeks(leg, spot)
            for k in ("delta", "gamma", "theta", "vega"):
                slot[k] += g[k] * pos.qty
                net[k] += g[k] * pos.qty
    return {"net": net, "by_ticker": by_ticker}

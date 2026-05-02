"""Strategy-level Greeks aggregation.

Domain:    Strategy Analysis — Greeks
Contracts:
  - net_greeks(legs, spot, r) -> dict[str, float]
Dependencies UPWARD:
  - core.options.greeks.black_scholes
Dependencies DOWNWARD:
  - services.strategy_service, core.portfolio
"""

from __future__ import annotations

import numpy as np

from core.options.greeks.black_scholes import greeks_vectorized
from core.strategies.models import Leg


def net_greeks(legs: list[Leg], spot: float, r: float = 0.05) -> dict[str, float]:
    """Sum Greeks across legs at current spot, scaled by side and qty."""
    totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for leg in legs:
        T = max(leg.dte, 1) / 365.0
        g = greeks_vectorized(spot, leg.strike, T, r, leg.iv, option_type=leg.option_type)
        scale = leg.sign * leg.qty
        for k in totals:
            v = float(g[k])
            if np.isfinite(v):
                totals[k] += scale * v
    return {k: round(v, 4) for k, v in totals.items()}

"""Probability of profit under BS lognormal assumption.

Domain:    Strategy Analysis — PoP
Contracts:
  - prob_profit(prices, pnl, spot, sigma, dte, r) -> float
Dependencies UPWARD:
  - scipy.stats, numpy
Dependencies DOWNWARD:
  - services.strategy_service
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def prob_profit(prices: np.ndarray, pnl: np.ndarray, spot: float, sigma: float, dte: int, r: float = 0.05) -> float:
    """Probability that P&L > 0 at expiration under BS lognormal assumption."""
    if sigma <= 0 or dte <= 0 or spot <= 0:
        return float("nan")
    T = dte / 365.0
    mu = np.log(spot) + (r - 0.5 * sigma**2) * T
    sd = sigma * np.sqrt(T)
    log_p = np.log(prices)
    pdf = norm.pdf(log_p, loc=mu, scale=sd) / prices
    mask = pnl > 0
    if not mask.any():
        return 0.0
    # Integrate per contiguous profitable region. A naive np.trapz(pdf[mask],
    # prices[mask]) would wrongly bridge disjoint regions (e.g. a straddle's two
    # wings) with one big trapezoid spanning the gap, over-counting probability.
    idx = np.where(mask)[0]
    prob = 0.0
    start = prev = idx[0]
    for cur in idx[1:]:
        if cur == prev + 1:
            prev = cur
            continue
        seg = np.arange(start, prev + 1)
        prob += float(np.trapz(pdf[seg], prices[seg]))
        start = prev = cur
    seg = np.arange(start, prev + 1)
    prob += float(np.trapz(pdf[seg], prices[seg]))
    return max(0.0, min(1.0, prob))

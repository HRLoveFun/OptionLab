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
    prob = float(np.trapz(pdf[mask], prices[mask]))
    return max(0.0, min(1.0, prob))

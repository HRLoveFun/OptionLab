"""Derived metrics enrichment.

Domain:    Option Decision — Enrichment
Contracts:
  - enrich_contract(contract, budget, spot_price, target_move_pct) -> dict | None
Dependencies UPWARD:
  - None
Dependencies DOWNWARD:
  - core.decision.ev
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def enrich_contract(contract: dict, budget: float, spot_price: float, target_move_pct: float) -> dict | None:
    mid = contract["mid_price"]
    if mid <= 0:
        return None
    contracts_n = int(budget / (mid * 100))
    if contracts_n == 0:
        return None
    delta = contract["delta"]
    delta_per_dollar = abs(delta) / mid
    target_price = spot_price * (1 + target_move_pct)
    intrinsic_at_target = max(contract["strike"] - target_price, 0)
    payoff_at_target = intrinsic_at_target - mid
    total_payoff = payoff_at_target * 100 * contracts_n
    odds_ratio = total_payoff / budget if budget > 0 else 0.0
    theta = contract["theta"]
    vega = contract["vega"]
    vega_theta_ratio = (abs(vega) / abs(theta)) if theta != 0 else float("inf")
    vega_per_dollar = abs(vega) / mid
    implied_win_rate = abs(delta)
    contract["derived"] = {
        "contracts_n": contracts_n,
        "delta_per_dollar": round(delta_per_dollar, 4),
        "target_price": round(target_price, 2),
        "payoff_at_target": round(payoff_at_target, 2),
        "total_payoff": round(total_payoff, 2),
        "odds_ratio": round(odds_ratio, 2),
        "vega_theta_ratio": round(vega_theta_ratio, 2) if math.isfinite(vega_theta_ratio) else 999.99,
        "vega_per_dollar": round(vega_per_dollar, 4),
        "implied_win_rate": round(implied_win_rate, 4),
    }
    return contract

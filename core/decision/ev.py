"""Subjective expected value computation.

Domain:    Option Decision — EV
Contracts:
  - compute_ev(contract, directional_conviction, vol_conviction, budget, time_horizon_days) -> dict
Dependencies UPWARD:
  - None
Dependencies DOWNWARD:
  - core.decision.filter_rank
"""

from __future__ import annotations


def compute_ev(
    contract: dict, directional_conviction: float, vol_conviction: float, budget: float, time_horizon_days: int
) -> dict:
    p_direction = directional_conviction
    iv_expansion_gain = contract["derived"]["vega_per_dollar"] * vol_conviction * 5.0
    adjusted_payoff = contract["derived"]["payoff_at_target"] + contract["mid_price"] * iv_expansion_gain
    adjusted_total = adjusted_payoff * 100 * contract["derived"]["contracts_n"]
    theta_drag = abs(contract["theta"]) * time_horizon_days * 100 * contract["derived"]["contracts_n"]
    net_if_right = adjusted_total - theta_drag
    loss_if_wrong = budget
    ev = p_direction * net_if_right - (1 - p_direction) * loss_if_wrong
    ev_ratio = ev / budget if budget > 0 else 0.0
    contract["ev"] = round(ev, 2)
    contract["ev_ratio"] = round(ev_ratio, 4)
    return contract

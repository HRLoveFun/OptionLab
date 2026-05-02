"""Unified strategy analysis aggregator.

Domain:    Strategy Analysis — Orchestrator
Contracts:
  - analyze_strategy(legs, spot, price_range, n_points, r) -> dict
Dependencies UPWARD:
  - core.strategies.payoff, core.strategies.greeks, core.strategies.prob_profit
Dependencies DOWNWARD:
  - services.strategy_service, tests
"""

from __future__ import annotations

import numpy as np

from core.strategies.greeks import net_greeks
from core.strategies.models import Leg
from core.strategies.payoff import find_breakevens, net_premium, payoff_at_expiration
from core.strategies.prob_profit import prob_profit


def analyze_strategy(
    legs: list[Leg],
    spot: float,
    *,
    price_range: tuple[float, float] | None = None,
    n_points: int = 401,
    r: float = 0.05,
) -> dict:
    """Compute payoff, breakevens, Greeks, max P&L, and probability of profit.

    Returns dict with keys: prices, pnl, breakevens, max_profit, max_loss,
    net_premium, greeks, prob_profit.
    """
    if not legs:
        raise ValueError("analyze_strategy: legs must not be empty")
    if spot <= 0:
        raise ValueError("analyze_strategy: spot must be positive")

    strikes = [leg.strike for leg in legs]
    if price_range is None:
        lo = min(min(strikes), spot) * 0.85
        hi = max(max(strikes), spot) * 1.15
    else:
        lo, hi = price_range
    lo = max(lo, 0.01)
    prices = np.linspace(lo, hi, n_points)
    pnl = payoff_at_expiration(legs, prices)

    edge_left = pnl[1] - pnl[0]
    edge_right = pnl[-1] - pnl[-2]
    long_calls = sum(leg.qty for leg in legs if leg.side == "long" and leg.option_type == "call")
    short_calls = sum(leg.qty for leg in legs if leg.side == "short" and leg.option_type == "call")
    long_puts = sum(leg.qty for leg in legs if leg.side == "long" and leg.option_type == "put")
    short_puts = sum(leg.qty for leg in legs if leg.side == "short" and leg.option_type == "put")
    upside_naked = short_calls > long_calls
    downside_naked = short_puts > long_puts

    max_profit = float(np.max(pnl))
    max_loss = float(np.min(pnl))
    if upside_naked and edge_right < 0:
        max_loss = float("-inf")
    if downside_naked and edge_left > 0:
        max_loss = float("-inf")
    if long_calls > short_calls and edge_right > 0:
        max_profit = float("inf")

    dte_max = max((leg.dte for leg in legs), default=30)
    iv_w_num = sum(leg.iv * leg.qty for leg in legs)
    iv_w_den = sum(leg.qty for leg in legs) or 1
    iv_avg = iv_w_num / iv_w_den

    return {
        "prices": prices.tolist(),
        "pnl": pnl.tolist(),
        "breakevens": find_breakevens(prices, pnl),
        "max_profit": max_profit,
        "max_loss": max_loss,
        "net_premium": net_premium(legs),
        "greeks": net_greeks(legs, spot, r=r),
        "prob_profit": prob_profit(prices, pnl, spot, iv_avg, dte_max, r=r),
    }

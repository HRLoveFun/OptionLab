"""Risk calculations for option portfolios: breakevens, position sizing, VaR."""

import numpy as np
from scipy.stats import norm


def _risk_breakdown(positions, spots, totals):
    """Aggregate delta exposure by ticker and by side."""
    by_ticker = {}
    by_side = {"long": 0, "short": 0}
    for pos in positions:
        t = pos["ticker"]
        side = pos.get("side", "long")
        qty = pos["quantity"]
        if t not in by_ticker:
            by_ticker[t] = {"delta": 0, "count": 0}
        by_ticker[t]["count"] += qty
        if side == "long":
            by_side["long"] += qty
        else:
            by_side["short"] += qty
    return {"by_ticker": by_ticker, "by_side": by_side}


def _find_breakevens(greeks_positions, spot):
    """Approximate breakevens from PnL curve via zero-crossing detection."""
    lo = spot * 0.5
    hi = spot * 1.5
    prices = np.linspace(lo, hi, 2000)
    total_pnl = np.zeros_like(prices)

    for pos in greeks_positions:
        is_call = pos["type"] in ("LC", "SC")
        is_long = pos["type"] in ("LC", "LP")
        sign = 1 if is_long else -1
        K = pos["strike"]
        premium = pos["premium"]
        qty = pos["qty"]
        if is_call:
            intrinsic = np.maximum(prices - K, 0)
        else:
            intrinsic = np.maximum(K - prices, 0)
        total_pnl += (intrinsic - premium) * sign * qty * 100

    breakevens = []
    for i in range(len(total_pnl) - 1):
        if total_pnl[i] * total_pnl[i + 1] < 0:
            p = prices[i] - total_pnl[i] * (prices[i + 1] - prices[i]) / (total_pnl[i + 1] - total_pnl[i])
            breakevens.append(round(float(p), 2))
    return breakevens


def _position_sizing(greeks_positions, spot, account_size, max_risk_pct):
    """Compute position sizing recommendation based on max risk per contract."""
    lo = spot * 0.5
    hi = spot * 1.5
    prices = np.linspace(lo, hi, 2000)
    total_pnl = np.zeros_like(prices)

    for pos in greeks_positions:
        is_call = pos["type"] in ("LC", "SC")
        is_long = pos["type"] in ("LC", "LP")
        sign = 1 if is_long else -1
        K = pos["strike"]
        premium = pos["premium"]
        qty = pos["qty"]
        if is_call:
            intrinsic = np.maximum(prices - K, 0)
        else:
            intrinsic = np.maximum(K - prices, 0)
        total_pnl += (intrinsic - premium) * sign * qty * 100

    max_loss = float(np.min(total_pnl))
    if max_loss >= 0:
        return {"max_contracts": None, "note": "No loss scenario detected"}

    max_dollar_risk = account_size * (max_risk_pct / 100)
    max_lots = max(1, int(max_dollar_risk / abs(max_loss)))
    return {
        "max_contracts": max_lots,
        "max_loss_per_lot": round(abs(max_loss), 2),
        "max_dollar_risk": round(max_dollar_risk, 2),
    }


def _calc_var(positions, spots, greeks_totals, confidence=0.95):
    """Delta-approximate 1-day VaR."""
    if not positions:
        return 0.0

    avg_iv = np.mean([p.get("iv", 0.25) for p in positions]) or 0.25
    main_ticker = positions[0]["ticker"]
    S = spots.get(main_ticker, 100)
    delta = greeks_totals.get("delta", 0)
    sigma_1d = avg_iv / np.sqrt(252)
    z = norm.ppf(confidence)
    var_1d = abs(delta) * S * sigma_1d * z * 100
    return round(float(var_1d), 2)

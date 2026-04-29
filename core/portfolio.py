"""Portfolio P&L attribution and Greeks aggregation.

Given a list of currently-open multi-leg positions (each with entry-time
snapshots of spot / IV / DTE / premium) and current market state, decompose
the unrealised P&L into delta / theta / vega contributions via a first-order
Taylor expansion around entry::

    ΔP&L ≈ Δ × (S_now - S_entry)
         + Vega × (IV_now - IV_entry) × 100   # per 1 vol point
         + Θ × Δt                              # per day

This is intentionally simple: the goal is "where did my P&L come from",
not BS reprice. It does NOT depend on IV history (yfinance has none): only
two single-point IV samples are needed (entry and current).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from core.options_greeks import greeks_vectorized
from core.strategies import Leg

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """A single open multi-leg position, used for portfolio aggregation."""

    ticker: str
    legs: list[Leg]
    entry_date: date
    entry_spot: float
    entry_net_premium: float
    qty: int = 1


def _leg_greeks(leg: Leg, spot: float, r: float = 0.05) -> dict[str, float]:
    """Compute per-share Greeks for a single leg at given ``spot``."""
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
    """Net Greeks across positions (and per-ticker breakdown).

    ``spots`` maps ticker → current spot. Tickers missing from ``spots``
    contribute nothing (skipped). All Greek values are *contract*-scaled (×100
    is NOT applied — caller decides display units).
    """
    by_ticker: dict[str, dict[str, float]] = {}
    net = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for pos in positions:
        spot = spots.get(pos.ticker)
        if spot is None or spot <= 0:
            continue
        slot = by_ticker.setdefault(pos.ticker, {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0})
        for leg in pos.legs:
            g = _leg_greeks(leg, spot)
            for k in ("delta", "gamma", "theta", "vega"):
                slot[k] += g[k] * pos.qty
                net[k] += g[k] * pos.qty
    return {"net": net, "by_ticker": by_ticker}


def attribute_pnl(
    position: Position,
    *,
    spot_now: float,
    iv_now: dict[int, float] | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """First-order P&L attribution for one position.

    Parameters
    ----------
    position
        Open position with entry snapshot.
    spot_now
        Current underlying price.
    iv_now
        Optional ``{leg_index: current_iv}`` map. Missing → assume IV
        unchanged (vega contribution = 0).
    today
        Override "today" for tests. Defaults to ``date.today()``.

    Returns
    -------
    dict
        ``{ "delta_pnl", "vega_pnl", "theta_pnl", "residual", "total" }`` —
        all in dollars, scaled by qty × 100 (per-contract).
    """
    today = today or date.today()
    days_held = max((today - position.entry_date).days, 0)

    delta_pnl = 0.0
    vega_pnl = 0.0
    theta_pnl = 0.0
    for i, leg in enumerate(position.legs):
        g_entry = _leg_greeks(leg, position.entry_spot)
        delta_pnl += g_entry["delta"] * (spot_now - position.entry_spot) * 100
        theta_pnl += g_entry["theta"] * days_held * 100  # theta is per-day per-share
        if iv_now is not None and i in iv_now:
            d_iv = iv_now[i] - leg.iv
            # vega in greeks_vectorized is per 1 vol POINT (dividend by 100 inside),
            # so multiply by 100 to convert to per 1 unit of IV (e.g. 0.25 → 25).
            vega_pnl += g_entry["vega"] * (d_iv * 100) * 100

    delta_pnl *= position.qty
    vega_pnl *= position.qty
    theta_pnl *= position.qty
    total = delta_pnl + vega_pnl + theta_pnl
    return {
        "delta_pnl": delta_pnl,
        "vega_pnl": vega_pnl,
        "theta_pnl": theta_pnl,
        "total": total,
        "days_held": days_held,
        "method": "first_order_taylor",
        "note": "Approximation; ignores gamma and IV smile changes.",
    }

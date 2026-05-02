"""First-order P&L attribution.

Domain:    Portfolio Analysis — Attribution
Contracts:
  - attribute_pnl(position, spot_now, iv_now, today) -> dict
Dependencies UPWARD:
  - core.portfolio.greeks
Dependencies DOWNWARD:
  - services.portfolio_analysis_service
"""

from __future__ import annotations

from datetime import date

from core.portfolio.greeks import leg_greeks
from core.portfolio.models import Position


def attribute_pnl(
    position: Position,
    *,
    spot_now: float,
    iv_now: dict[int, float] | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    days_held = max((today - position.entry_date).days, 0)
    delta_pnl = vega_pnl = theta_pnl = 0.0
    for i, leg in enumerate(position.legs):
        g_entry = leg_greeks(leg, position.entry_spot)
        delta_pnl += g_entry["delta"] * (spot_now - position.entry_spot) * 100
        theta_pnl += g_entry["theta"] * days_held * 100
        if iv_now is not None and i in iv_now:
            d_iv = iv_now[i] - leg.iv
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

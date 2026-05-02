"""Portfolio-level Greeks aggregation.

Domain:    Options Analysis — Portfolio Greeks
Context:
  - Multi-leg position Greeks table and theta decay path.
Contracts:
  - portfolio_greeks_table(positions, spot) -> tuple[dict, pd.DataFrame]
  - theta_decay_path(positions, spot) -> tuple[np.ndarray, np.ndarray]
Dependencies UPWARD:
  - core.options.greeks.black_scholes
Dependencies DOWNWARD:
  - core.portfolio, services.portfolio_analysis_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core.options.greeks.black_scholes import _T_MIN, greeks_vectorized

logger = logging.getLogger(__name__)


def portfolio_greeks_table(positions: list, spot: float, r: float = 0.05) -> tuple:
    """Compute net Greeks and detail table for multi-leg portfolio.

    positions format: [{'type': 'LC'|'SC'|'LP'|'SP', 'strike': float,
                        'dte': int, 'iv': float, 'qty': int, 'premium': float}, ...]
    Returns (totals_dict, detail_df).
    """

    def _get_val(g: dict, key: str) -> float:
        v = g[key]
        return float(v) if np.isfinite(v) else 0.0

    totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "net_premium": 0.0}
    rows = []
    for pos in positions:
        try:
            is_call = pos["type"] in ("LC", "SC")
            is_long = pos["type"] in ("LC", "LP")
            sign = 1 if is_long else -1
            T = max(pos["dte"], 1) / 365
            g = greeks_vectorized(
                S=float(spot), K=float(pos["strike"]), T=T, r=r,
                sigma=float(pos["iv"]), option_type="call" if is_call else "put",
            )
            qty = int(pos["qty"]) * sign
            totals["delta"] += _get_val(g, "delta") * qty
            totals["gamma"] += _get_val(g, "gamma") * qty
            totals["theta"] += _get_val(g, "theta") * qty
            totals["vega"] += _get_val(g, "vega") * qty
            totals["net_premium"] += float(pos["premium"]) * int(pos["qty"]) * (-sign)
            rows.append({
                "Leg": pos["type"],
                "Strike": pos["strike"],
                "DTE": pos["dte"],
                "IV": f"{pos['iv'] * 100:.1f}%",
                "Qty": qty,
                "Delta": f"{_get_val(g, 'delta') * qty:+.3f}",
                "Gamma": f"{_get_val(g, 'gamma') * qty:+.5f}",
                "Theta/d": f"{_get_val(g, 'theta') * qty:+.2f}",
                "Vega/1%": f"{_get_val(g, 'vega') * qty:+.2f}",
            })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Skipping leg %s due to error: %s", pos, e)
    return totals, pd.DataFrame(rows)


def theta_decay_path(positions: list, spot: float, r: float = 0.05) -> tuple:
    """Compute portfolio theta as a function of remaining DTE.

    Returns (days_array, daily_theta_array).
    """
    if not positions:
        return np.array([]), np.array([])
    max_dte = max(max(pos.get("dte", 0) for pos in positions), 1)
    days = np.arange(0, max_dte + 1)
    total_theta = np.zeros(len(days))
    for pos in positions:
        try:
            is_call = pos["type"] in ("LC", "SC")
            is_long = pos["type"] in ("LC", "LP")
            sign = 1 if is_long else -1
            qty = int(pos["qty"]) * sign
            dte_remain = np.maximum(pos["dte"] - days, 0)
            T_arr = np.maximum(dte_remain / 365, _T_MIN)
            g = greeks_vectorized(
                S=float(spot), K=float(pos["strike"]), T=T_arr, r=r,
                sigma=float(pos["iv"]), option_type="call" if is_call else "put",
            )
            theta_series = np.where(np.isfinite(g["theta"]), g["theta"] * qty, 0.0)
            total_theta += theta_series
        except Exception as e:
            logger.warning("theta_decay_path skipping leg: %s", e)
    return days, total_theta

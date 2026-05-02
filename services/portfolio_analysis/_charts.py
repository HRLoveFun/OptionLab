"""Portfolio P&L and theta-decay chart rendering."""

import numpy as np
from matplotlib import pyplot as plt

from core.options.greeks.portfolio import theta_decay_path


def _plot_pnl(positions, spots):
    """Plot payoff diagram at expiration."""
    main_ticker = positions[0]["ticker"]
    spot = spots.get(main_ticker, 100)

    strikes = [p["strike"] for p in positions]
    lo = min(min(strikes), spot) * 0.85
    hi = max(max(strikes), spot) * 1.15
    prices = np.linspace(lo, hi, 500)

    total_pnl = np.zeros_like(prices)
    for pos in positions:
        is_call = pos["option_type"] in ("LC", "SC")
        is_long = pos["option_type"] in ("LC", "LP")
        sign = 1 if is_long else -1
        K = pos["strike"]
        premium = pos["price"]
        qty = pos["quantity"]

        if is_call:
            intrinsic = np.maximum(prices - K, 0)
        else:
            intrinsic = np.maximum(K - prices, 0)

        leg_pnl = (intrinsic - premium) * sign * qty * 100
        total_pnl += leg_pnl

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(prices, total_pnl, color="#3b82f6", linewidth=2)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.axvline(spot, color="#f59e0b", linewidth=1.2, linestyle=":", label=f"Spot {spot:.2f}")
    ax.fill_between(prices, total_pnl, 0, where=total_pnl >= 0, alpha=0.15, color="green")
    ax.fill_between(prices, total_pnl, 0, where=total_pnl < 0, alpha=0.15, color="red")
    ax.set_xlabel("Underlying Price")
    ax.set_ylabel("P&L ($)")
    ax.set_title("Portfolio P&L at Expiration")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def _plot_theta_decay(greeks_positions, spot):
    """Plot portfolio theta decay over time."""
    days, total_theta = theta_decay_path(greeks_positions, spot, r=0.05)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(days, total_theta, color="#ef4444", linewidth=1.8)
    ax.axhline(0, color="grey", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Days from Now")
    ax.set_ylabel("Portfolio Theta ($/day)")
    ax.set_title("Theta Decay Path")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig

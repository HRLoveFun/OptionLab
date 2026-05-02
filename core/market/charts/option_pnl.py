"""Option portfolio P&L chart renderer.

Domain:    Market Analysis — Option P&L Chart
Contracts:
  - render_option_pnl(matrix_df, current_price, option_data=None) -> str | None
Dependencies UPWARD:
  - matplotlib, core._shared.plotting
Dependencies DOWNWARD:
  - core.market_analyzer
"""

from __future__ import annotations

import logging

from core._shared.plotting import encode_figure, new_figure
from core.market.option_pnl import find_breakeven_points

logger = logging.getLogger(__name__)


def render_option_pnl(matrix_df, current_price, option_data=None) -> str | None:
    """Render an option portfolio P&L chart as a base64 PNG string."""
    try:
        with new_figure((12, 8)) as fig:
            ax = fig.subplots()
            ax.plot(matrix_df.index, matrix_df["PnL"], linewidth=3, color="blue")
            ax.axhline(y=0, color="black", linestyle="-", alpha=0.8, linewidth=1)
            ax.axvline(
                x=current_price,
                color="red",
                linestyle="--",
                alpha=0.8,
                linewidth=2,
                label=f"Current Price: ${current_price:.2f}",
            )
            ax.fill_between(
                matrix_df.index, matrix_df["PnL"], 0,
                where=(matrix_df["PnL"] > 0), color="green", alpha=0.3, label="Profit",
            )
            ax.fill_between(
                matrix_df.index, matrix_df["PnL"], 0,
                where=(matrix_df["PnL"] < 0), color="red", alpha=0.3, label="Loss",
            )
            ax.set_xlabel("Stock Price ($)", fontsize=12)
            ax.set_ylabel("P&L ($)", fontsize=12)
            ax.set_title("Options Portfolio P&L Analysis", fontsize=14, fontweight="bold")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11)

            max_profit = matrix_df["PnL"].max()
            max_loss = matrix_df["PnL"].min()
            breakeven_points = find_breakeven_points(matrix_df)
            stats_text = f"Max Profit: ${max_profit:.0f}\nMax Loss: ${max_loss:.0f}"
            if breakeven_points:
                stats_text += f"\nBreakeven: ${breakeven_points[0]:.0f}"
                if len(breakeven_points) > 1:
                    stats_text += f", ${breakeven_points[1]:.0f}"
            ax.text(
                0.02, 0.98, stats_text,
                transform=ax.transAxes, fontsize=12, verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )

            # Greeks summary overlay
            try:
                if option_data:
                    from core.options.greeks.portfolio import portfolio_greeks_table

                    positions = []
                    for opt in option_data:
                        if opt.get("dte") and opt.get("iv"):
                            positions.append({
                                "type": opt["option_type"],
                                "strike": float(opt["strike"]),
                                "dte": int(opt["dte"]),
                                "iv": float(opt["iv"]),
                                "qty": int(opt["quantity"]),
                                "premium": float(opt["premium"]),
                            })
                    if positions:
                        totals, _ = portfolio_greeks_table(positions, float(current_price))
                        greeks_text = (
                            f"Net Delta: {totals['delta']:+.3f}\n"
                            f"Net Gamma: {totals['gamma']:+.5f}\n"
                            f"Theta/day: {totals['theta']:+.2f}\n"
                            f"Vega/1%:   {totals['vega']:+.2f}"
                        )
                        ax.text(
                            0.98, 0.98, greeks_text,
                            transform=ax.transAxes, fontsize=10, verticalalignment="top",
                            horizontalalignment="right", family="monospace",
                            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8),
                        )
            except Exception as e:
                logger.debug("Greeks overlay skipped: %s", e)

            return encode_figure(fig)
    except Exception as e:
        logger.error("Error creating option P&L chart: %s", e)
        return None

"""IV Term Structure chart.

Domain:    Options Analysis — IV Term Structure
Contracts:
  - render_iv_term_structure(dates, atm_ivs, spot) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
"""

from __future__ import annotations

import logging

import matplotlib.ticker as mticker

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_iv_term_structure(dates: list[str], atm_ivs: list[float], spot: float) -> str | None:
    try:
        if len(dates) < 2:
            return None
        with new_figure((10, 5)) as fig:
            ax = fig.subplots()
            x = range(len(dates))
            for i in range(len(dates) - 1):
                color = "green" if atm_ivs[i + 1] >= atm_ivs[i] else "red"
                ax.plot([i, i + 1], [atm_ivs[i], atm_ivs[i + 1]], color=color, linewidth=2)
            ax.scatter(x, atm_ivs, color="tab:blue", zorder=5, s=40)
            for xi, iv in zip(x, atm_ivs, strict=False):
                ax.annotate(f"{iv:.1f}%", (xi, iv), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
            ax.set_xticks(list(x))
            ax.set_xticklabels(dates, rotation=45, ha="right", fontsize=7)
            ax.set_ylabel("ATM Put IV (%)")
            ax.set_title(f"IV Term Structure  |  Spot: {spot:.2f}")
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
            ax.grid(alpha=0.3)
            slope = atm_ivs[-1] - atm_ivs[0]
            label = "Contango (Normal)" if slope >= 0 else "Backwardation (Inverted)"
            color = "green" if slope >= 0 else "red"
            ax.text(0.98, 0.95, label, transform=ax.transAxes, ha="right", va="top",
                    color=color, fontsize=9, fontweight="bold")
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_iv_term_structure failed: %s", e)
        return None

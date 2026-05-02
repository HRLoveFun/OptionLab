"""Rolling correlation chart.

Domain:    Market Assessment — Correlation Dynamics
Contracts:
  - render_correlation(return_1y, return_5y, osc_1y, osc_5y) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging

import pandas as pd
from matplotlib.ticker import FuncFormatter

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_correlation(
    return_1y: pd.Series | None,
    return_5y: pd.Series | None,
    osc_1y: pd.Series | None,
    osc_5y: pd.Series | None,
) -> str | None:
    """Render consolidated correlation chart."""
    try:
        if all(x is None or x.empty for x in [return_1y, return_5y, osc_1y, osc_5y]):
            return None

        with new_figure((16, 7)) as fig:
            ax = fig.subplots()

            if return_1y is not None and not return_1y.empty:
                ax.plot(return_1y.index, return_1y.values, color="#1f77b4", linewidth=2,
                        label="Consecutive returns (1Y)", alpha=0.85, linestyle="-")
            if return_5y is not None and not return_5y.empty:
                ax.plot(return_5y.index, return_5y.values, color="#4d94d6", linewidth=2,
                        label="Consecutive returns (5Y)", alpha=0.7, linestyle="--")
            if osc_1y is not None and not osc_1y.empty:
                ax.plot(osc_1y.index, osc_1y.values, color="#ff7f0e", linewidth=2,
                        label="High-Low Corr (1Y)", alpha=0.85, linestyle="-", marker="o", markersize=3, markevery=10)
            if osc_5y is not None and not osc_5y.empty:
                ax.plot(osc_5y.index, osc_5y.values, color="#ffb366", linewidth=2,
                        label="High-Low Corr (5Y)", alpha=0.7, linestyle="--", marker="s", markersize=3, markevery=10)

            ax.axhline(y=0, color="gray", linestyle=":", linewidth=1.5, alpha=0.6)
            ax.set_xlabel("Date", fontsize=12, fontweight="bold")
            ax.set_ylabel("Correlation", fontsize=12, fontweight="bold")
            ax.set_title("Correlation Dynamics", fontsize=14, fontweight="bold", pad=15)
            ax.grid(True, alpha=0.3, linestyle="--")
            ax.set_ylim(-1, 1)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:.2f}"))

            legend = ax.legend(fontsize=8, framealpha=0.95, edgecolor="gray", ncol=2, title="Correlation", title_fontsize=9)
            legend.get_title().set_fontweight("bold")
            return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering correlation chart: %s", e)
        return None

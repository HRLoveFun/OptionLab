"""Price & Volatility dynamics chart.

Domain:    Market Assessment — Volatility Dynamics
Contracts:
  - render_volatility(daily_close, volatility, bull_bear_segs, ticker, frequency) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging

from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

from core._shared.plotting import COLOR_BEAR, COLOR_BULL, COLOR_VOL, encode_figure, new_figure
from core._shared.types import FREQUENCY_LABELS

logger = logging.getLogger(__name__)

VOLATILITY_WINDOWS = {"D": 5, "W": 5, "ME": 21, "QE": 63}


def render_volatility(daily_close, volatility, bull_bear_segs, ticker: str, frequency: str) -> str | None:
    """Render price & volatility dynamics with bull/bear colouring."""
    try:
        with new_figure((16, 10)) as fig:
            ax1 = fig.subplots()
            ax1.set_xlabel("Date", fontsize=12)
            ax1.set_ylabel("Price ($)", fontsize=12, color="black")

            for segment in bull_bear_segs.get("bull_segments", []):
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color=COLOR_BULL, linewidth=2, alpha=0.5)
            for segment in bull_bear_segs.get("bear_segments", []):
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color=COLOR_BEAR, linewidth=2, alpha=0.5)

            ax1.set_yscale("log")
            ax1.yaxis.set_major_locator(LogLocator(base=10.0, subs=[1.0, 2.0, 4.0], numticks=15))
            ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
            ax1.yaxis.set_minor_locator(LogLocator(base=10.0, subs="auto", numticks=15))
            ax1.yaxis.set_minor_formatter(NullFormatter())
            ax1.tick_params(axis="y", labelcolor="black")
            ax1.grid(True, alpha=0.3)

            ax2 = ax1.twinx()
            ax2.set_ylabel("Volatility (%)", fontsize=12, color="blue")
            ax2.plot(volatility.index, volatility.values, color=COLOR_VOL, linewidth=3, alpha=0.7,
                     label="Historical Volatility", linestyle="-")
            ax2.tick_params(axis="y", labelcolor="blue")

            current_vol = volatility.iloc[-1] if len(volatility) > 0 else volatility.mean()
            ax2.scatter(x=volatility.index[-1], y=current_vol, color="purple", s=100, marker="o",
                        linewidth=1.5, alpha=0.8, zorder=5)

            freq_name = FREQUENCY_LABELS.get(frequency, frequency)
            window = VOLATILITY_WINDOWS.get(frequency, 21)
            ax1.set_title(f"{ticker} - Price & Volatility Dynamics\nVolatility Window: {window} days ({freq_name} frequency)",
                          fontsize=14, fontweight="bold", pad=20)

            legend_elements = [
                Line2D([0], [0], color=COLOR_BULL, linewidth=2, label="Bull"),
                Line2D([0], [0], color=COLOR_BEAR, linewidth=2, label="Bear"),
                Line2D([0], [0], color=COLOR_VOL, linewidth=2, label=f"Volatility, *{current_vol:.1f}%"),
            ]
            ax1.legend(handles=legend_elements, loc="upper left", fontsize=10, framealpha=0.8,
                       bbox_to_anchor=(0.0, 1.0), borderaxespad=0.1)
            return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering volatility chart: %s", e)
        return None

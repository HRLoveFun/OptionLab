"""IV Smile chart.

Domain:    Options Analysis — IV Smile
Contracts:
  - render_iv_smile(calls, puts, spot, expiry) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
"""

from __future__ import annotations

import logging

import matplotlib.ticker as mticker
import pandas as pd

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_iv_smile(calls: pd.DataFrame, puts: pd.DataFrame, spot: float, expiry: str) -> str | None:
    try:
        calls = calls.dropna(subset=["impliedVolatility"])
        puts = puts.dropna(subset=["impliedVolatility"])
        atm = min(calls["strike"].tolist(), key=lambda x: abs(x - spot))

        with new_figure((10, 5)) as fig:
            ax = fig.subplots()
            ax.plot(calls["strike"], calls["impliedVolatility"] * 100, color="tab:blue",
                    linestyle="--", linewidth=1.8, label="Calls IV")
            ax.plot(puts["strike"], puts["impliedVolatility"] * 100, color="tab:orange",
                    linestyle="-", linewidth=1.8, label="Puts IV")
            ax.axvline(atm, color="grey", linestyle=":", linewidth=1.2, label=f"ATM ~{atm:.0f}")
            ax.axvline(spot, color="black", linestyle="-", linewidth=1, alpha=0.5, label=f"Spot {spot:.2f}")
            ax.set_xlabel("Strike")
            ax.set_ylabel("Implied Volatility (%)")
            ax.set_title(f"IV Smile — {expiry}  |  Spot: {spot:.2f}")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)
            ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_iv_smile failed: %s", e)
        return None

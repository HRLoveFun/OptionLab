"""OI / Volume profile chart.

Domain:    Options Analysis — OI/Volume Profile
Contracts:
  - render_oi_volume(calls, puts, spot, expiry) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
  - core.options.chain.metrics
"""

from __future__ import annotations

import logging

import pandas as pd

from core._shared.plotting import encode_figure, new_figure
from core.options.chain.metrics import max_pain

logger = logging.getLogger(__name__)


def render_oi_volume(calls: pd.DataFrame, puts: pd.DataFrame, spot: float, expiry: str) -> str | None:
    try:
        mp = max_pain(calls, puts)
        with new_figure((14, 7)) as fig:
            ax1, ax2 = fig.subplots(1, 2)

            ax1.barh(calls["strike"], calls["openInterest"], color="green", alpha=0.7, label="Call OI", height=2)
            ax1.barh(puts["strike"], -puts["openInterest"], color="red", alpha=0.7, label="Put OI", height=2)
            ax1.axhline(spot, color="black", linestyle="--", linewidth=1.5, label=f"Spot {spot:.0f}")
            ax1.axhline(mp, color="purple", linestyle=":", linewidth=1.5, label=f"Max Pain {mp:.0f}")
            ax1.set_xlabel("Open Interest  (Call +ve / Put −ve)")
            ax1.set_ylabel("Strike")
            ax1.set_title("OI Distribution")
            ax1.legend(fontsize=8)
            ax1.grid(axis="x", alpha=0.3)

            ax2.barh(calls["strike"], calls["volume"], color="green", alpha=0.7, label="Call Volume", height=2)
            ax2.barh(puts["strike"], -puts["volume"], color="red", alpha=0.7, label="Put Volume", height=2)
            ax2.axhline(spot, color="black", linestyle="--", linewidth=1.5, label=f"Spot {spot:.0f}")
            ax2.axhline(mp, color="purple", linestyle=":", linewidth=1.5, label=f"Max Pain {mp:.0f}")
            ax2.set_xlabel("Volume  (Call +ve / Put −ve)")
            ax2.set_title("Volume Distribution")
            ax2.legend(fontsize=8)
            ax2.grid(axis="x", alpha=0.3)

            fig.suptitle(f"OI / Volume Profile — {expiry}  |  Spot: {spot:.2f}", fontsize=12)
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_oi_volume failed: %s", e)
        return None

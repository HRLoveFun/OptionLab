"""Put/Call Ratio chart.

Domain:    Options Analysis — PCR
Contracts:
  - render_pcr(rows, ticker) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
"""

from __future__ import annotations

import logging

import pandas as pd

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_pcr(rows: list[dict], ticker: str) -> str | None:
    try:
        if not rows:
            return None
        df = pd.DataFrame(rows).dropna(subset=["vol_pcr", "oi_pcr"])
        if df.empty:
            return None

        with new_figure((14, max(4, len(df) * 0.6 + 1))) as fig:
            ax1, ax2 = fig.subplots(1, 2)
            for ax, col, title in [(ax1, "vol_pcr", "Volume PCR"), (ax2, "oi_pcr", "OI PCR")]:
                colors = ["red" if v > 1.3 else ("green" if v < 0.7 else "tab:blue") for v in df[col]]
                ax.barh(df["expiry"], df[col], color=colors, alpha=0.8)
                ax.axvline(1.0, color="grey", linestyle="--", linewidth=1.2, label="PCR=1 (Neutral)")
                ax.axvline(0.7, color="green", linestyle=":", linewidth=1.0, label="PCR=0.7 (Bullish)")
                ax.axvline(1.3, color="red", linestyle=":", linewidth=1.0, label="PCR=1.3 (Bearish)")
                ax.set_xlabel("PCR")
                ax.set_title(title)
                ax.legend(fontsize=7)
                ax.grid(axis="x", alpha=0.3)
            fig.suptitle(f"Put/Call Ratio by Expiry — {ticker}", fontsize=12)
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_pcr failed: %s", e)
        return None

"""Skew analysis chart.

Domain:    Options Analysis — Skew
Contracts:
  - render_skew(calls, puts, spot, expiry) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
  - core.options.chain.metrics
"""

from __future__ import annotations

import logging

import pandas as pd

from core._shared.plotting import encode_figure, new_figure
from core.options.chain.metrics import skew_25d

logger = logging.getLogger(__name__)


def render_skew(calls: pd.DataFrame, puts: pd.DataFrame, spot: float, expiry: str) -> str | None:
    try:
        calls = calls.dropna(subset=["impliedVolatility"])
        puts = puts.dropna(subset=["impliedVolatility"])
        atm_iv = float(puts.loc[(puts["strike"] - spot).abs().idxmin(), "impliedVolatility"]) * 100

        puts2 = puts.copy()
        puts2["moneyness"] = puts2["strike"] / spot
        puts2["put_skew"] = puts2["impliedVolatility"] * 100 - atm_iv
        puts2 = puts2[puts2["moneyness"] <= 1.0].sort_values("moneyness")

        merged = pd.merge_asof(
            puts2.sort_values("strike")[["strike", "moneyness", "impliedVolatility"]],
            calls.sort_values("strike")[["strike", "impliedVolatility"]],
            on="strike", suffixes=("_put", "_call"), direction="nearest",
        )
        merged["rr"] = (merged["impliedVolatility_put"] - merged["impliedVolatility_call"]) * 100

        with new_figure((10, 8)) as fig:
            ax1, ax2 = fig.subplots(2, 1, sharex=False)
            ax1.plot(puts2["moneyness"], puts2["put_skew"], color="tab:orange", linewidth=1.8)
            ax1.axhline(0, color="grey", linestyle="--", linewidth=1)
            ax1.axvline(1.0, color="black", linestyle=":", linewidth=1, alpha=0.5)
            ax1.set_ylabel("Put Skew (OTM Put IV − ATM IV) %")
            ax1.set_title(f"Skew Analysis — {expiry}")
            ax1.grid(alpha=0.3)

            ax2.bar(merged["moneyness"], merged["rr"],
                    color=["red" if v > 0 else "green" for v in merged["rr"]], width=0.005, alpha=0.8)
            ax2.axhline(0, color="grey", linestyle="--", linewidth=1)
            ax2.set_xlabel("Moneyness (Strike / Spot)")
            ax2.set_ylabel("Risk Reversal (Put IV − Call IV) %")
            ax2.grid(alpha=0.3)

            s25 = skew_25d(puts, calls, spot)
            if s25 is not None:
                ax2.text(0.02, 0.95, f"25Δ Skew: {s25 * 100:.2f}%",
                         transform=ax2.transAxes, fontsize=9, va="top", color="darkred", fontweight="bold")
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_skew failed: %s", e)
        return None

"""IV Surface (3D) chart.

Domain:    Options Analysis — IV Surface
Contracts:
  - render_iv_surface(records, spot, ticker) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
"""

from __future__ import annotations

import logging

import pandas as pd

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_iv_surface(records: list[dict], spot: float, ticker: str) -> str | None:
    try:
        if len(records) < 6:
            return None
        df = pd.DataFrame(records)
        X = df["moneyness"].values
        Y = df["dte"].values
        Z = df["iv"].values
        with new_figure((12, 7)) as fig:
            ax = fig.add_subplot(111, projection="3d")
            sc = ax.scatter(X, Y, Z, c=Z, cmap="RdYlGn_r", s=15, alpha=0.8)
            fig.colorbar(sc, ax=ax, shrink=0.5, pad=0.1, label="IV (%)")
            ax.set_xlabel("Moneyness\n(Strike / Spot)", labelpad=10)
            ax.set_ylabel("DTE (days)", labelpad=10)
            ax.set_zlabel("Put IV (%)", labelpad=10)
            ax.set_title(f"IV Surface — {ticker}  |  Spot: {spot:.2f}")
            return encode_figure(fig)
    except Exception as e:
        logger.error("render_iv_surface failed: %s", e)
        return None

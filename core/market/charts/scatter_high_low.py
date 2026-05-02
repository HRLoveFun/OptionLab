"""Osc_High vs Osc_Low scatter with marginal histograms.

Domain:    Market Assessment — High-Low Scatter
Contracts:
  - render_scatter_high_low(osc_low, osc_high) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging

import pandas as pd

from core._shared.plotting import encode_figure
from core.market.charts.scatter_osc import _create_scatter_fig

logger = logging.getLogger(__name__)


def render_scatter_high_low(osc_low: pd.Series, osc_high: pd.Series) -> str | None:
    """Render Osc_Low vs Osc_High scatter chart.

    Labels the top-5 spread points.
    """
    try:
        common = osc_low.index.intersection(osc_high.index)
        if len(common) == 0:
            return None
        x = osc_low.loc[common]
        y = osc_high.loc[common]
        x.name = "Osc_low"
        y.name = "Osc_high"

        spread = (y - x).dropna()
        top5_indices = spread.nlargest(5).index if len(spread) >= 5 else spread.sort_values(ascending=False).index

        fig = _create_scatter_fig(x, y, label_indices=top5_indices)
        return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering high-low scatter: %s", e)
        return None

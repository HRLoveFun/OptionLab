"""Return-Oscillation dynamics line chart.

Domain:    Market Assessment — Dynamics Chart
Contracts:
  - render_dynamics(returns, osc_high, osc_low, osc_high_full, osc_low_full,
                    rolling_window, risk_threshold) -> str | None
Dependencies UPWARD:
  - core._shared.plotting, core.market.charts._scales
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core._shared.plotting import encode_figure, new_figure
from core.market.charts._scales import build_date_ticks

logger = logging.getLogger(__name__)


def render_dynamics(
    returns: pd.Series,
    osc_high: pd.Series,
    osc_low: pd.Series,
    osc_high_full: pd.Series,
    osc_low_full: pd.Series,
    rolling_window: int = 20,
    risk_threshold: int = 90,
) -> str | None:
    """Render Return-Oscillation dynamics with rolling projections."""
    try:
        valid_mask = returns.notna() & osc_high.notna() & osc_low.notna()
        returns_valid = returns[valid_mask]
        osc_high_valid = osc_high[valid_mask]
        osc_low_valid = osc_low[valid_mask]
        n = len(returns_valid)
        if n == 0:
            return None

        with new_figure((14.5, 7.0)) as fig:
            ax = fig.subplots()
            t_idx = np.arange(n)

            high_proj_full = _rolling_projections(osc_high_full, rolling_window, risk_threshold)
            low_proj_full = _rolling_projections(osc_low_full, rolling_window, 100 - risk_threshold)
            high_proj = high_proj_full.reindex(osc_high_valid.index)
            low_proj = low_proj_full.reindex(osc_low_valid.index)

            ax.scatter(t_idx, returns_valid.values, color="tab:orange", s=25, marker="o", label="Returns", alpha=0.8, zorder=3)
            ax.scatter(t_idx, osc_high_valid.values, s=40, marker="s", facecolors="none", edgecolors="purple",
                       linewidths=1.4, label="Osc_high", alpha=0.9, zorder=4)
            ax.scatter(t_idx, osc_low_valid.values, s=40, marker="s", facecolors="none", edgecolors="blue",
                       linewidths=1.4, label="Osc_low", alpha=0.9, zorder=4)

            if high_proj is not None and not high_proj.empty:
                last = high_proj.iloc[-1]
                label = f"High Proj ({risk_threshold}%)"
                if last is not None and np.isfinite(last):
                    label += f" *{last:.2f}"
                ax.plot(t_idx, high_proj.to_numpy(), color="darkgreen", linewidth=2.0, linestyle="--", label=label, alpha=0.8, zorder=3)

            if low_proj is not None and not low_proj.empty:
                last = low_proj.iloc[-1]
                low_threshold = 100 - risk_threshold
                label = f"Low Proj ({low_threshold}%)"
                if last is not None and np.isfinite(last):
                    label += f" *{last:.2f}"
                ax.plot(t_idx, low_proj.to_numpy(), color="darkred", linewidth=2.0, linestyle="--", label=label, alpha=0.8, zorder=3)

            ax.axhline(y=0, color="gray", linestyle="-", linewidth=1, alpha=0.3)
            ax.set_xlabel("Index", fontsize=11)
            ax.set_ylabel("Percentage (%)", fontsize=11)
            ax.grid(True, alpha=0.3)

            try:
                tick_pos, tick_labels = build_date_ticks(returns_valid.index, n, approx_ticks=20)
                ax.set_xticks(tick_pos)
                ax.set_xticklabels(tick_labels, rotation=90, fontsize=9)
            except Exception:
                pass

            ax.legend(loc="upper left", fontsize=8, framealpha=0.85)
            ax.set_title("Return-Oscillation Dynamics", fontsize=13, fontweight="bold")
            return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering dynamics chart: %s", e)
        return None


def _rolling_projections(series: pd.Series, rolling_window: int, risk_threshold: int) -> pd.Series:
    """Calculate rolling projections using historical percentiles."""
    percentile = risk_threshold / 100.0
    projections = []
    for i in range(len(series)):
        if i < rolling_window:
            projections.append(np.nan)
        else:
            historical_window = series.iloc[i - rolling_window:i]
            projections.append(historical_window.quantile(percentile))
    return pd.Series(projections, index=series.index)

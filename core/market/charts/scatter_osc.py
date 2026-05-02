"""Oscillation vs Returns scatter with marginal histograms.

Domain:    Market Assessment — Scatter Chart
Context:
  - Renders a single scatter plot from pre-computed feature series.
Contracts:
  - render_scatter_osc(oscillation, returns, label_indices=None) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
  - numpy, pandas, matplotlib
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging
from typing import Iterable

import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_scatter_osc(
    oscillation: pd.Series,
    returns: pd.Series,
    *,
    label_indices: Iterable | None = None,
) -> str | None:
    """Render Oscillation vs Returns scatter with marginal histograms.

    Returns base64-encoded PNG or None on error.
    """
    try:
        x = oscillation.dropna()
        y = returns.dropna()
        common = x.index.intersection(y.index)
        if len(common) == 0:
            return None
        x = x.loc[common]
        y = y.loc[common]
        fig = _create_scatter_fig(x, y, label_indices=label_indices)
        return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering scatter osc: %s", e)
        return None


def _create_scatter_fig(x: pd.Series, y: pd.Series, label_indices: Iterable | None = None):
    with new_figure((10, 8)) as fig:
        gs = GridSpec(2, 2, width_ratios=(3, 1), height_ratios=(1, 3),
                      left=0.05, right=0.95, bottom=0.05, top=0.95, wspace=0.05, hspace=0.05)
        ax = fig.add_subplot(gs[1, 0])
        ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
        ax_histx.tick_params(axis="x", labelbottom=False)
        ax_histy.tick_params(axis="y", labelleft=False)

        ax.scatter(x, y, alpha=0.5, s=20, c="orange")
        ax.axhline(y=0, color="gray", linestyle="-", linewidth=5, alpha=0.05)
        ax.axvline(x=0, color="gray", linestyle="-", linewidth=5, alpha=0.05)

        # Percentile lines
        for p in np.percentile(x, [20, 40, 60, 80]):
            ax.axvline(p, color="blue", linestyle="dashed", linewidth=1, alpha=0.2)
        for p in np.percentile(y, [20, 40, 60, 80]):
            ax.axhline(p, color="blue", linestyle="dashed", linewidth=1, alpha=0.2)

        _add_highlight_labels(ax, x, y, label_indices)
        _add_histograms(ax_histx, ax_histy, x, y)
        _add_percentile_texts(ax_histx, ax_histy, x, y)

        ax.grid(True, alpha=0.3)
        ax.set_xlabel(f"{x.name} (%)", fontsize=12)
        ax.set_ylabel(f"{y.name} (%)", fontsize=12)
        fig.suptitle(f"{x.name} vs {y.name} Analysis", fontsize=14, fontweight="bold")
        return fig


def _add_highlight_labels(ax, x: pd.Series, y: pd.Series, label_indices):
    try:
        indices_to_label = None
        if label_indices is not None:
            indices_to_label = [idx for idx in label_indices if idx in x.index and idx in y.index]
        elif len(x) >= 5:
            indices_to_label = x.nlargest(5).index

        recent_indices = x.index[-5:] if len(x) >= 5 else []

        top_only = [idx for idx in (indices_to_label or []) if idx not in recent_indices]
        both = [idx for idx in (indices_to_label or []) if idx in recent_indices]
        recent_only = [idx for idx in recent_indices if indices_to_label is None or idx not in indices_to_label]

        if top_only:
            ax.scatter([x.loc[i] for i in top_only], [y.loc[i] for i in top_only], color="red", s=20, zorder=4, alpha=0.7)
        if recent_only:
            ax.scatter([x.loc[i] for i in recent_only], [y.loc[i] for i in recent_only], color="blue", s=20, zorder=4, alpha=0.7)
        if both:
            ax.scatter([x.loc[i] for i in both], [y.loc[i] for i in both], color="purple", s=20, zorder=5, alpha=0.7)

        if indices_to_label:
            for idx in indices_to_label:
                ax.annotate(f"{idx.strftime('%y%b')}", xy=(x.loc[idx], y.loc[idx]),
                            xytext=(5, -5), textcoords="offset points", fontsize=6, color="red")
        for idx in recent_indices:
            ax.annotate(f"{idx.strftime('%b')}", xy=(x.loc[idx], y.loc[idx]),
                        xytext=(5, 5), textcoords="offset points", fontsize=6, color="blue")
    except Exception as e:
        logger.warning("Failed to add labels: %s", e)


def _add_histograms(ax_histx, ax_histy, x: pd.Series, y: pd.Series):
    def make_bins(s: pd.Series):
        if len(s) == 0:
            return np.arange(-0.5, 5.5, 1)
        left = np.floor(s.min() + 0.5) - 0.5
        right = np.ceil(s.max() - 0.5) + 0.5
        return np.arange(left, right + 1, 1)

    ax_histx.hist(x, bins=make_bins(x), alpha=0.7, color="skyblue", edgecolor="black")
    ax_histy.hist(y, bins=make_bins(y), alpha=0.7, color="lightcoral", orientation="horizontal", edgecolor="black")


def _add_percentile_texts(ax_histx, ax_histy, x: pd.Series, y: pd.Series):
    try:
        if len(x) > 0:
            latest_x = x.iloc[-1]
            x_pct = float(((x <= latest_x).sum() / len(x)) * 100.0)
            ax_histx.text(0.98, 0.90, f"Osc Percentile: {x_pct:.1f}%",
                          transform=ax_histx.transAxes, ha="right", va="top", fontsize=9,
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        if len(y) > 0:
            latest_y = y.iloc[-1]
            y_pct = float(((y <= latest_y).sum() / len(y)) * 100.0)
            ax_histy.text(0.05, 0.98, f"Ret Percentile: {y_pct:.1f}%",
                          transform=ax_histy.transAxes, ha="left", va="top", fontsize=9,
                          bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    except Exception as e:
        logger.warning("Failed to add percentile labels: %s", e)

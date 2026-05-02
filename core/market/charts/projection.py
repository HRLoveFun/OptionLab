"""Oscillation projection chart.

Domain:    Market Assessment — Projection Chart
Contracts:
  - render_projection(proj_df, percentile, proj_volatility, bias_text,
                      oos_acc, n_train, n_valid) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
Dependencies DOWNWARD:
  - services.chart_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core._shared.plotting import encode_figure, new_figure

logger = logging.getLogger(__name__)


def render_projection(
    proj_df: pd.DataFrame,
    percentile: float,
    proj_volatility: float,
    bias_text: str,
    oos_acc: float | None = None,
    n_train: int | None = None,
    n_valid: int | None = None,
) -> str | None:
    """Render oscillation projection chart and return base64 PNG."""
    try:
        with new_figure((16, 10)) as fig:
            ax = fig.subplots()
            x_values = np.arange(len(proj_df.index))
            _plot_projection_points(ax, x_values, proj_df)
            _format_projection_axes(ax, proj_df, percentile, proj_volatility, bias_text, oos_acc, n_train, n_valid)
            return encode_figure(fig)
    except Exception as e:
        logger.error("Error rendering projection chart: %s", e)
        return None


def _plot_projection_points(ax, x_values: np.ndarray, proj_df: pd.DataFrame):
    close_mask = ~proj_df["Close"].isna()
    if close_mask.any():
        ax.scatter(x_values[close_mask], proj_df["Close"][close_mask], label="Close", color="green", s=50, marker="o", zorder=3)

    high_mask = ~proj_df["High"].isna()
    if high_mask.any():
        ax.scatter(x_values[high_mask], proj_df["High"][high_mask], label="High", color="purple", s=50, marker="^", zorder=3)
        ax.plot(x_values[high_mask], proj_df["High"][high_mask], color="purple", linewidth=1.5, alpha=0.8,
                solid_capstyle="round", label="_nolegend_")

    low_mask = ~proj_df["Low"].isna()
    if low_mask.any():
        ax.scatter(x_values[low_mask], proj_df["Low"][low_mask], label="Low", color="blue", s=50, marker="v", zorder=3)
        ax.plot(x_values[low_mask], proj_df["Low"][low_mask], color="blue", linewidth=1.5, alpha=0.8,
                solid_capstyle="round", label="_nolegend_")

    for col, color, label in [
        ("iHigh", "red", "Proj High (Current)"),
        ("iLow", "red", "Proj Low (Current)"),
        ("iHigh1", "orange", "Proj High (Next)"),
        ("iLow1", "orange", "Proj Low (Next)"),
    ]:
        mask = ~proj_df[col].isna()
        if mask.any():
            ax.scatter(x_values[mask], proj_df[col][mask], label=label, facecolors="none", edgecolors=color,
                       s=80, linewidth=2, zorder=3)


def _format_projection_axes(ax, proj_df, percentile, proj_volatility, bias_text, oos_acc, n_train, n_valid):
    ax.set_xticks(range(len(proj_df.index)))
    ax.set_xticklabels([d.strftime("%m/%d") for d in proj_df.index], rotation=90, fontsize=8)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Price", fontsize=12)
    ax.set_title("Oscillation Projection", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    oos_txt = f"{oos_acc:.1%}" if oos_acc is not None else "N/A"
    param_text = (
        f"Threshold: {percentile:.0%}\n"
        f"Volatility: {proj_volatility:.1f}%\n"
        f"Bias: {bias_text}\n"
        f"OOS Hit Rate: {oos_txt}\n"
        f"Train/Valid: {n_train or '?'}/{n_valid or '?'} periods"
    )
    ax.text(0.02, 0.98, param_text, transform=ax.transAxes, fontsize=12, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    ax.legend(fontsize=12, loc="upper right")

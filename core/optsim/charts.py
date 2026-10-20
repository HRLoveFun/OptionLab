"""Static charts for the scenario grid (matplotlib, PNG bytes).

Domain:    Option Simulation — Charts
Context:
  - Six small multiples sharing the spot axis: P&L by date, P&L at entry under
    IV shifts, and delta / gamma / theta / vega by date.
  - Dates are an ordered magnitude, so they use one blue hue from light (entry)
    to dark (last expiry), at most five steps; IV shifts are diverging
    (blue = lower IV, gray = unchanged, red = higher IV).
  - Rendering only: no I/O; the caller decides where the bytes go.
Contracts:
  - chart_days(days, max_lines=5) -> list[int]   # indices into grid.days
  - render_grid_png(grid) -> bytes
Dependencies UPWARD:
  - matplotlib, numpy, core._shared.plotting, core.optsim.engine
Dependencies DOWNWARD:
  - scripts/optsim.py, services.options.optsim (chart_days), tests
"""

from __future__ import annotations

import io

import numpy as np
from matplotlib.ticker import FuncFormatter

from core._shared.plotting import new_figure
from core.optsim.engine import Grid

# DOMAIN: validated ordinal ramp (one hue, monotone lightness, every step >= 2:1 on the surface).
_DATE_RAMP = ("#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281")
_IV_COLORS = {"down": "#2a78d6", "flat": "#52514e", "up": "#e34948"}
_SURFACE, _INK, _INK_2, _MUTED, _GRID, _AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
_LW = 1.1  # ~2 px at 150 dpi


def chart_days(days, max_lines: int = 5) -> list[int]:
    """Indices of up to ``max_lines`` dates: entry, quartiles of the horizon, last expiry."""
    days = np.asarray(days, dtype=float)
    if len(days) <= max_lines:
        return list(range(len(days)))
    targets = np.linspace(days[0], days[-1], max_lines)
    picked = sorted({int(np.argmin(np.abs(days - t))) for t in targets})
    return picked


def _ramp(n: int) -> list[str]:
    idx = np.round(np.linspace(0, len(_DATE_RAMP) - 1, n)).astype(int) if n > 1 else [len(_DATE_RAMP) - 1]
    return [_DATE_RAMP[i] for i in idx]


def _style(ax, title: str) -> None:
    ax.set_facecolor(_SURFACE)
    ax.set_title(title, loc="left", fontsize=10, color=_INK)
    ax.grid(True, color=_GRID, linewidth=0.6)
    ax.axhline(0.0, color=_AXIS, linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(_AXIS)
    ax.tick_params(colors=_INK_2, labelsize=8)


def _format_y(ax, values) -> None:
    """One number format per axis, chosen from the data range (not per tick)."""
    span = float(np.nanmax(np.abs(values))) if np.size(values) else 0.0
    nd = 0 if span >= 50 else (1 if span >= 5 else (2 if span >= 0.5 else 3))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.{nd}f}"))


def _day_label(grid: Grid, d: int) -> str:
    day = int(grid.days[d])
    expiries = {int(leg.dte) for leg in grid.position.legs}
    return f"day {day} (expiry)" if day in expiries else f"day {day}"


def render_grid_png(grid: Grid, *, dpi: int = 150) -> bytes:
    """Six-panel PNG of the grid at the unshifted IV (P&L-under-IV panel uses the shifts)."""
    flat = int(np.argmin(np.abs(grid.iv_shifts)))
    picks = chart_days(grid.days)
    colors = _ramp(len(picks))
    s0 = grid.market.spot
    panels = [
        ("pnl", "P&L by date ($)"),
        (None, "P&L at entry under IV shifts ($)"),
        ("delta", "Delta (shares)"),
        ("gamma", "Gamma (shares per $1 move)"),
        ("theta", "Theta ($ per day)"),
        ("vega", "Vega ($ per vol point)"),
    ]
    pos = grid.position
    title = f"{pos.name or 'position'} · {pos.style} · {pos.product} · S0 = {s0:,.2f}"
    with new_figure((12.0, 10.5), dpi=dpi) as fig:
        fig.patch.set_facecolor(_SURFACE)
        axes = fig.subplots(3, 2, sharex=True)
        for ax, (field, label) in zip(axes.ravel(), panels, strict=True):
            _style(ax, label)
            ax.axvline(s0, color=_MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
            if field is None:
                order = np.argsort(grid.iv_shifts)
                for v in order:
                    shift = grid.iv_shifts[v]
                    key = "flat" if np.isclose(shift, 0.0) else ("down" if shift < 0 else "up")
                    if key != "flat" and v not in (order[0], order[-1]):
                        continue
                    label = "IV unchanged" if key == "flat" else f"IV {shift * 100:+.0f} vol pts"
                    ax.plot(grid.spots, grid.pnl[v, 0], color=_IV_COLORS[key], linewidth=_LW, label=label)
                ax.legend(fontsize=8, frameon=False, labelcolor=_INK_2)
                _format_y(ax, grid.pnl[:, 0])
                continue
            values = getattr(grid, field)[flat]
            for d, color in zip(picks, colors, strict=True):
                ax.plot(grid.spots, values[d], color=color, linewidth=_LW, label=_day_label(grid, d))
            _format_y(ax, values[picks])
        for ax in axes[-1]:
            ax.set_xlabel("Spot", fontsize=9, color=_INK_2)
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(
            handles,
            labels,
            loc="upper center",
            ncol=len(labels),
            frameon=False,
            fontsize=9,
            bbox_to_anchor=(0.5, 0.955),
        )
        fig.suptitle(title, x=0.01, ha="left", fontsize=12, color=_INK)
        fig.tight_layout(rect=(0, 0, 1, 0.93))
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=_SURFACE)
    return buf.getvalue()

"""Shared plotting infrastructure.

Domain:    Chart rendering utilities
Context:
  - Eliminates matplotlib global pyplot state so AI can reason locally.
  - All chart modules should use ``new_figure()`` context manager.
Contracts:
  - new_figure(size, dpi) -> Iterator[Figure]
  - encode_figure(fig, fmt) -> str   # base64 PNG/SVG
Dependencies UPWARD:
  - matplotlib.figure, matplotlib.pyplot
Dependencies DOWNWARD:
  - core.market.charts, core.options.charts
"""

from __future__ import annotations

import base64
import io
import logging
from contextlib import contextmanager
from typing import Iterator

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)

# Default sizes (inches)
SIZE_SCATTER = (10, 8)
SIZE_DYNAMICS = (14.5, 7.0)
SIZE_SPREAD = (14.5, 5.2)
SIZE_VOLATILITY = (16, 10)
SIZE_OPTIONS = (12, 8)
SIZE_PROJECTION = (16, 10)
SIZE_CORRELATION = (14, 6)

# Semantic colours
COLOR_OSC = "tab:blue"
COLOR_RET = "tab:orange"
COLOR_BULL = "green"
COLOR_BEAR = "red"
COLOR_VOL = "orange"
COLOR_1Y = "#1f77b4"
COLOR_5Y = "#ff7f0e"


@contextmanager
def new_figure(size: tuple[float, float], *, dpi: int = 150) -> Iterator[Figure]:
    """Explicit figure lifecycle — no global pyplot state leakage."""
    fig = Figure(figsize=size, dpi=dpi)
    try:
        yield fig
    finally:
        plt.close(fig)


def encode_figure(fig: Figure, *, fmt: str = "png") -> str:
    """Convert figure to base64-encoded string."""
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=150, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


def fig_to_base64(fig: Figure) -> str:
    """Backward-compat alias for encode_figure."""
    return encode_figure(fig)

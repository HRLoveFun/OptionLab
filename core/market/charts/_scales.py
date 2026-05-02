"""Shared axis formatting helpers.

Domain:    Market Analysis — Chart Scales
Context:
  - Date tick builders, log formatters, percentile labels.
Contracts:
  - build_date_ticks(index, n_points, approx_ticks) -> tuple[list[int], list[str]]
  - format_projection_value(value) -> str
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.market.charts.*
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_date_ticks(index: pd.Index, n_points: int, approx_ticks: int = 20) -> tuple[list[int], list[str]]:
    """Return (positions, labels) for date-like x-axis ticks."""
    step = max(1, n_points // max(1, approx_ticks))
    positions = list(np.arange(0, n_points, step))
    labels = [pd.Timestamp(index[int(p)]).strftime("%y%b") for p in positions]
    return positions, labels


def format_projection_value(value) -> str:
    """Format projection values with dynamic precision."""
    if pd.isna(value) or value == "":
        return ""
    try:
        num_value = float(value)
        if num_value == 0:
            return "0.00"
        abs_value = abs(num_value)
        if abs_value >= 0.01:
            return f"{num_value:.2f}"
        decimal_places = 2
        temp_value = abs_value
        while temp_value < 0.1 and decimal_places < 10:
            temp_value *= 10
            decimal_places += 1
        decimal_places += 1
        return f"{num_value:.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)

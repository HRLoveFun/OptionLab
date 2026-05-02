"""Horizon filtering utilities.

Domain:    Market Analysis — Time-window filtering
Context:
  - Extracted from PriceDynamic._apply_horizon / _compute_effective_end_ts
  - Stateless pure functions operating on Series indices.
Contracts:
  - apply_horizon(series, horizon) -> pd.Series | None
  - compute_effective_end(frequency) -> pd.Timestamp
Dependencies UPWARD:
  - pandas, datetime
Dependencies DOWNWARD:
  - core.market.features.*
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from core._shared.types import Frequency


def apply_horizon(
    series: pd.Series | None,
    start: dt.date,
    end: dt.date,
    user_provided_end: bool = True,
    frequency: Frequency = "W",
) -> pd.Series | None:
    """Filter *series* to inclusive [start, end] window.

    If *user_provided_end* is False, *end* is extended to the current period
    boundary via ``compute_effective_end``.
    """
    if series is None or series.empty:
        return series
    try:
        start_ts = pd.Timestamp(start)
        if user_provided_end:
            end_ts = pd.Timestamp(end)
        else:
            end_ts = compute_effective_end(frequency)
        idx = series.index
        if hasattr(idx, "tz") and idx.tz is not None:
            if start_ts.tz is None:
                start_ts = start_ts.tz_localize(idx.tz)
            if end_ts.tz is None:
                end_ts = end_ts.tz_localize(idx.tz)
        return series[(idx >= start_ts) & (idx <= end_ts)]
    except Exception:
        return series


def compute_effective_end(frequency: Frequency) -> pd.Timestamp:
    """Compute period-end boundary when user left end date blank."""
    today = pd.Timestamp(dt.date.today())
    if frequency == "D":
        return today
    elif frequency == "W":
        weekday = today.weekday()
        days_to_sunday = (6 - weekday) % 7
        return today + pd.Timedelta(days=days_to_sunday)
    elif frequency == "ME":
        return today + pd.offsets.MonthEnd(0)
    elif frequency == "QE":
        return today + pd.offsets.QuarterEnd(0)
    else:
        return today

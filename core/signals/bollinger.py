"""Bollinger band position signal.

Domain:    Market Signals — Bollinger
Contracts:
  - bollinger_position(close, n, k) -> dict | None
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.signals.bundle
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def bollinger_position(close: pd.Series, n: int = 20, k: float = 2.0) -> dict | None:
    if close is None or len(close) < n:
        return None
    window = close.tail(n)
    ma = window.mean()
    sd = window.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return None
    last = float(close.iloc[-1])
    z = (last - ma) / sd
    upper = ma + k * sd
    lower = ma - k * sd
    if last < lower:
        position = "below"
    elif last < ma - 0.5 * sd:
        position = "lower_band"
    elif last <= ma + 0.5 * sd:
        position = "inside"
    elif last <= upper:
        position = "upper_band"
    else:
        position = "above"
    return {
        "ma": float(round(ma, 4)),
        "upper": float(round(upper, 4)),
        "lower": float(round(lower, 4)),
        "zscore": float(round(z, 3)),
        "position": position,
    }

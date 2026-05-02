"""RSI signal.

Domain:    Market Signals — RSI
Contracts:
  - rsi(close, n) -> float | None
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.signals.bundle
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, n: int = 14) -> float | None:
    if close is None or len(close) < n + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    if not np.isfinite(val):
        return None
    return float(round(val, 2))

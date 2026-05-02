"""Oscillation feature computation.

Domain:    Market Analysis — Oscillation
Context:
  - Computes oscillation, osc_high, osc_low from OHLCV bars.
  - All functions are vectorised and stateless.
Contracts:
  - osc(bars, on_effect=True) -> pd.Series
  - osc_high(bars) -> pd.Series
  - osc_low(bars) -> pd.Series
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.market.projections, core.market.charts
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def osc(bars: pd.DataFrame, *, on_effect: bool = True) -> pd.Series | None:
    """Calculate oscillation as (High − Low) / LastClose * 100.

    Args:
        bars: DataFrame with columns High, Low, LastClose.
        on_effect: If True, adjust high/low by LastClose (max/min).
    """
    if bars is None or bars.empty:
        return None
    try:
        if on_effect:
            high_adj = np.maximum(bars["High"], bars["LastClose"])
            low_adj = np.minimum(bars["Low"], bars["LastClose"])
            result = (high_adj - low_adj) / bars["LastClose"] * 100
        else:
            result = (bars["High"] - bars["Low"]) / bars["LastClose"] * 100
        result.name = "Oscillation"
        return result.dropna()
    except Exception as e:
        logger.error("Error calculating oscillation: %s", e)
        return None


def osc_high(bars: pd.DataFrame) -> pd.Series | None:
    """High oscillation: (High / LastClose − 1) * 100."""
    if bars is None or bars.empty:
        return None
    try:
        result = (bars["High"] / bars["LastClose"] - 1) * 100
        result.name = "Osc_high"
        return result.dropna()
    except Exception as e:
        logger.error("Error calculating osc_high: %s", e)
        return None


def osc_low(bars: pd.DataFrame) -> pd.Series | None:
    """Low oscillation: (Low / LastClose − 1) * 100."""
    if bars is None or bars.empty:
        return None
    try:
        result = (bars["Low"] / bars["LastClose"] - 1) * 100
        result.name = "Osc_low"
        return result.dropna()
    except Exception as e:
        logger.error("Error calculating osc_low: %s", e)
        return None

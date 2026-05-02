"""Return and difference feature computation.

Domain:    Market Analysis — Returns
Context:
  - Computes percentage returns and absolute differences from Adj Close.
Contracts:
  - price_returns(bars) -> pd.Series
  - price_difference(bars) -> pd.Series
Dependencies UPWARD:
  - pandas
Dependencies DOWNWARD:
  - core.market.charts
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def price_returns(bars: pd.DataFrame) -> pd.Series | None:
    """Percentage return from Adj Close: (Close − LastAdjClose) / LastAdjClose * 100."""
    if bars is None or bars.empty:
        return None
    try:
        result = ((bars["Adj Close"] - bars["LastAdjClose"]) / bars["LastAdjClose"]) * 100
        result.name = "Returns"
        return result.dropna()
    except Exception as e:
        logger.error("Error calculating returns: %s", e)
        return None


def price_difference(bars: pd.DataFrame) -> pd.Series | None:
    """Absolute difference in Adj Close."""
    if bars is None or bars.empty:
        return None
    try:
        result = bars["Adj Close"] - bars["LastAdjClose"]
        result.name = "Difference"
        return result.dropna()
    except Exception as e:
        logger.error("Error calculating difference: %s", e)
        return None

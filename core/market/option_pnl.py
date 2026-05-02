"""Option portfolio P&L matrix computation.

Domain:    Market Analysis — Option P&L
Context:
  - Computes per-share P&L across a price grid for a basket of options.
  - Input format matches the legacy MarketAnalyzer.analyze_options schema.
Contracts:
  - build_option_matrix(option_data, current_price) -> pd.DataFrame | None
  - single_option_pnl(prices, option_type, strike, quantity, premium) -> np.ndarray
  - find_breakeven_points(matrix_df) -> list[float]
Dependencies UPWARD:
  - numpy, pandas
Dependencies DOWNWARD:
  - core.market.charts.option_pnl, services.analysis_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def build_option_matrix(option_data: list, current_price: float) -> pd.DataFrame | None:
    """Build a price-grid P&L DataFrame for a basket of options.

    Parameters
    ----------
    option_data:
        List of dicts with keys option_type (SC|SP|LC|LP), strike, quantity, premium.
    current_price:
        Current underlying price used to center the price grid [0.7×, 1.3×].

    Returns
    -------
    DataFrame indexed by price with a single column "PnL" (per-share).
    """
    if not option_data or current_price is None or current_price <= 0:
        return None
    try:
        price_range = np.linspace(current_price * 0.7, current_price * 1.3, 301)
        matrix_df = pd.DataFrame(index=price_range)
        matrix_df["PnL"] = 0.0
        for option in option_data:
            pnl = single_option_pnl(
                price_range,
                option["option_type"],
                option["strike"],
                option["quantity"],
                option["premium"],
            )
            matrix_df["PnL"] += pnl
        return matrix_df
    except Exception as e:
        logger.error("Error calculating option matrix: %s", e)
        return None


def single_option_pnl(prices: np.ndarray, option_type: str, strike: float, quantity: float, premium: float) -> np.ndarray:
    """Per-share P&L for a single option leg."""
    if option_type == "SC":
        return np.where(prices > strike, (premium - (prices - strike)) * quantity, premium * quantity)
    elif option_type == "SP":
        return np.where(prices < strike, (premium - (strike - prices)) * quantity, premium * quantity)
    elif option_type == "LC":
        return np.where(prices > strike, (prices - strike - premium) * quantity, -premium * quantity)
    elif option_type == "LP":
        return np.where(prices < strike, (strike - prices - premium) * quantity, -premium * quantity)
    else:
        return np.zeros_like(prices)


def find_breakeven_points(matrix_df: pd.DataFrame) -> list[float]:
    """Return all prices where P&L crosses zero (linear interpolation)."""
    try:
        pnl_values = matrix_df["PnL"].values
        prices = matrix_df.index.values
        breakeven_points = []
        for i in range(len(pnl_values) - 1):
            if (pnl_values[i] <= 0 <= pnl_values[i + 1]) or (pnl_values[i] >= 0 >= pnl_values[i + 1]):
                if pnl_values[i + 1] != pnl_values[i]:
                    breakeven_price = prices[i] - pnl_values[i] * (prices[i + 1] - prices[i]) / (
                        pnl_values[i + 1] - pnl_values[i]
                    )
                    breakeven_points.append(breakeven_price)
        return breakeven_points
    except Exception as e:
        logger.error("Error finding breakeven points: %s", e)
        return []

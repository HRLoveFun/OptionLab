"""Volatility feature computation.

Domain:    Market Analysis — Volatility
Context:
  - Rolling historical volatility and multi-window HV context.
Contracts:
  - calculate_volatility(daily_close, frequency, window=None) -> pd.Series
  - hv_context(daily_close) -> dict | None
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.market.charts, services.analysis_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core._shared.types import Frequency

logger = logging.getLogger(__name__)

VOLATILITY_WINDOWS: dict[Frequency, int] = {
    "D": 5,
    "W": 5,
    "ME": 21,
    "QE": 63,
}

# DOMAIN: US equity market convention for annualizing daily volatility.
TRADING_DAYS_PER_YEAR = 252


def calculate_volatility(
    daily_close: pd.Series,
    frequency: Frequency = "W",
    window: int | None = None,
) -> pd.Series | None:
    """Annualised rolling HV (%)."""
    if daily_close is None or daily_close.empty:
        return None
    try:
        if window is None:
            window = VOLATILITY_WINDOWS.get(frequency, 21)

        logger.debug(
            "calculate_volatility input: len=%d, first=%s, last=%s, min=%.4f, max=%.4f, "
            "freq=%s, window=%d",
            len(daily_close),
            daily_close.index[0],
            daily_close.index[-1],
            daily_close.min(),
            daily_close.max(),
            frequency,
            window,
        )

        daily_returns = daily_close.pct_change().dropna()
        logger.debug(
            "daily_returns stats: len=%d, min=%.6f, max=%.6f, mean=%.6f, std=%.6f",
            len(daily_returns),
            daily_returns.min(),
            daily_returns.max(),
            daily_returns.mean(),
            daily_returns.std(),
        )

        # Guard against extreme single-day moves that usually indicate bad data.
        extreme_mask = daily_returns.abs() > 0.5
        if extreme_mask.any():
            extreme_days = daily_returns[extreme_mask]
            logger.warning(
                "Extreme daily returns detected (>50%%): %s",
                ", ".join(f"{idx.date()}: {v:.2%}" for idx, v in extreme_days.items()),
            )

        rolling_std = daily_returns.rolling(window=window).std()
        rolling_vol = rolling_std * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
        rolling_vol.name = "Volatility"
        result = rolling_vol.dropna()
        if not result.empty:
            logger.debug(
                "rolling_vol output: len=%d, first=%.4f%%, last=%.4f%%, min=%.4f%%, max=%.4f%%",
                len(result),
                result.iloc[0],
                result.iloc[-1],
                result.min(),
                result.max(),
            )
        return result
    except Exception as e:
        logger.error("Error calculating volatility: %s", e)
        return None


def hv_context(daily_close: pd.Series) -> dict | None:
    """Multi-window HV and percentile rank.

    Returns dict with keys: hv_10d, hv_20d, hv_60d, hv_252d, hv_rank,
    hv_252d_min, hv_252d_max, hv_term_slope.
    """
    if daily_close is None or len(daily_close) < 30:
        return None
    try:
        adj = pd.to_numeric(daily_close, errors="coerce")
        log_ret = np.log(adj / adj.shift(1)).dropna()

        windows = [10, 20, 60, 252]
        ann_factor = np.sqrt(TRADING_DAYS_PER_YEAR) * 100

        hv_dict: dict[str, float | None] = {
            f"hv_{w}d": float(log_ret.rolling(w, min_periods=max(5, w // 2)).std().iloc[-1] * ann_factor)
            for w in windows
        }

        hv_20_series = log_ret.rolling(20, min_periods=10).std().dropna() * ann_factor
        if len(hv_20_series) >= 60:
            recent_252 = hv_20_series.iloc[-252:]
            current_hv20 = hv_dict["hv_20d"]
            hv_dict["hv_rank"] = float((recent_252 <= current_hv20).sum() / len(recent_252))
            hv_dict["hv_252d_min"] = float(recent_252.min())
            hv_dict["hv_252d_max"] = float(recent_252.max())
        else:
            hv_dict["hv_rank"] = None

        hv_dict["hv_term_slope"] = round(hv_dict["hv_10d"] - hv_dict["hv_60d"], 2)
        return hv_dict
    except Exception as e:
        logger.warning("HV context calculation failed: %s", e)
        return None

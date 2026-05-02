"""Oscillation projection computation.

Domain:    Market Assessment — Oscillation Projection
Context:
  - Walk-forward method with out-of-sample validation.
  - Returns ProjectionResult + DataFrame (no matplotlib).
Contracts:
  - compute_oscillation_projection(bars, daily_bars, percentile, target_bias) -> tuple[ProjectionResult, pd.DataFrame]
  - build_projection_dataframe(...) -> pd.DataFrame
Dependencies UPWARD:
  - core.market.models (ProjectionResult, Band)
  - pandas, numpy
Dependencies DOWNWARD:
  - core.market.charts.projection
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

from core._shared.types import Frequency
from core.market.models import Band, ProjectionResult

logger = logging.getLogger(__name__)


def compute_oscillation_projection(
    bars: pd.DataFrame,
    daily_bars: pd.DataFrame | None,
    percentile: float = 0.90,
    target_bias: float | None = None,
    frequency: Frequency = "W",
) -> tuple[ProjectionResult | None, pd.DataFrame]:
    """Compute oscillation projection with walk-forward validation.

    Args:
        bars: Resampled bars (must contain High, Low, LastClose, Close, Oscillation).
        daily_bars: Daily bars for filling historical values in projection table.
        percentile: Percentile threshold for oscillation width.
        target_bias: If None, use natural bias; else optimize for this bias.
        frequency: Resampling frequency for period-length calculation.

    Returns:
        (ProjectionResult, projection DataFrame) or (None, empty DataFrame).
    """
    try:
        if bars is None or bars.empty or "Oscillation" not in bars.columns:
            return None, pd.DataFrame()

        proj_volatility = float(bars["Oscillation"].quantile(percentile))
        if target_bias is None:
            proj_high_weight = _calculate_natural_bias_weight(bars, proj_volatility)
            bias_text = "Natural"
        else:
            proj_high_weight = _optimize_projection_weight(bars, proj_volatility, target_bias)
            bias_text = f"Neutral ({target_bias})"

        px_last_close = float(bars["LastClose"].iloc[-1])
        px_last = float(bars["Close"].iloc[-1])
        proj_high_cur = px_last_close + px_last_close * proj_volatility / 100 * proj_high_weight
        proj_low_cur = px_last_close - px_last_close * proj_volatility / 100 * (1 - proj_high_weight)
        proj_high_next = px_last + px_last * proj_volatility / 100 * proj_high_weight
        proj_low_next = px_last - px_last * proj_volatility / 100 * (1 - proj_high_weight)

        proj_df = _build_projection_dataframe(
            bars, daily_bars, proj_high_cur, proj_low_cur, proj_high_next, proj_low_next, frequency
        )

        result = ProjectionResult(
            ticker="",
            percentile=percentile,
            proj_volatility=proj_volatility,
            bias_text=bias_text,
            current_band=Band(high=proj_high_cur, low=proj_low_cur, weight=proj_high_weight),
            next_band=Band(high=proj_high_next, low=proj_low_next, weight=proj_high_weight),
            oos_accuracy=getattr(_calculate_natural_bias_weight, "_oos_accuracy", None),
            train_size=getattr(_calculate_natural_bias_weight, "_train_size", 0),
            valid_size=getattr(_calculate_natural_bias_weight, "_valid_size", 0),
        )
        return result, proj_df
    except Exception as e:
        logger.error("Error computing oscillation projection: %s", e)
        return None, pd.DataFrame()


def _calculate_natural_bias_weight(data: pd.DataFrame, proj_volatility: float) -> float:
    """Walk-forward optimal high weight on out-of-sample data."""
    try:
        n = len(data) - 1
        if n < 20:
            return 0.5
        split = max(int(n * 0.7), 15)
        if n - split < 5:
            split = max(n - 5, 10)
        valid = data.iloc[split:n]
        lc_arr = valid["LastClose"].values
        cl_arr = valid["Close"].values
        weights = np.linspace(0.3, 0.7, 21)
        proj_high = lc_arr[np.newaxis, :] * (1 + proj_volatility / 100 * weights[:, np.newaxis])
        proj_low = lc_arr[np.newaxis, :] * (1 - proj_volatility / 100 * (1 - weights[:, np.newaxis]))
        hit_matrix = (cl_arr[np.newaxis, :] >= proj_low) & (cl_arr[np.newaxis, :] <= proj_high)
        accuracy_arr = hit_matrix.mean(axis=1)
        best_idx = int(np.argmax(accuracy_arr))
        _calculate_natural_bias_weight._oos_accuracy = float(accuracy_arr[best_idx])
        _calculate_natural_bias_weight._train_size = split
        _calculate_natural_bias_weight._valid_size = len(valid)
        return float(weights[best_idx])
    except Exception as e:
        logger.error("Error calculating natural bias weight: %s", e)
        return 0.5


def _optimize_projection_weight(data: pd.DataFrame, proj_volatility: float, target_bias: float) -> float:
    """Grid-search weight to match target realized bias."""
    try:
        weights = np.linspace(0.4, 0.6, 21)
        best_weight = 0.5
        min_error = float("inf")
        for weight in weights:
            bias = _calculate_realized_bias(data, proj_volatility, weight)
            error = abs(bias - target_bias)
            if error < min_error:
                min_error = error
                best_weight = weight
        return best_weight
    except Exception as e:
        logger.error("Error optimizing projection weight: %s", e)
        return 0.5


def _calculate_realized_bias(data: pd.DataFrame, proj_volatility: float, weight: float) -> float:
    """Realized directional bias for a given weight."""
    try:
        df = data.iloc[:-1].copy()
        df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * weight
        df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - weight)
        df["Status"] = np.where(df["Close"] > df["ProjHigh"], 1, np.where(df["Close"] < df["ProjLow"], -1, 0))
        if len(df) == 0:
            return 0.0
        return float(((df["Status"] == 1).sum() - (df["Status"] == -1).sum()) / len(df))
    except Exception as e:
        logger.error("Error calculating realized bias: %s", e)
        return 0.0


def _build_projection_dataframe(
    bars: pd.DataFrame,
    daily_bars: pd.DataFrame | None,
    proj_high_cur: float,
    proj_low_cur: float,
    proj_high_next: float,
    proj_low_next: float,
    frequency: Frequency,
) -> pd.DataFrame:
    """Build projection DataFrame with historical and projected values."""
    try:
        if daily_bars is None or daily_bars.empty:
            logger.warning("No daily data available for projection DataFrame")
            return pd.DataFrame()

        close_dates = bars.get("CloseDate")
        if isinstance(close_dates, pd.Series) and len(close_dates) >= 2:
            date_last_close = close_dates.iloc[-2]
            date_last = close_dates.iloc[-1]
        else:
            date_last_close = bars.index[-2] if len(bars) >= 2 else bars.index[-1]
            date_last = bars.index[-1]

        if hasattr(daily_bars.index, "tz") and daily_bars.index.tz is not None:
            tz = daily_bars.index.tz
            if not hasattr(date_last_close, "tz") or date_last_close.tz is None:
                date_last_close = pd.Timestamp(date_last_close).tz_localize(tz)
            if not hasattr(date_last, "tz") or date_last.tz is None:
                date_last = pd.Timestamp(date_last).tz_localize(tz)

        end_date = date_last + pd.DateOffset(months=2)
        all_weekdays = pd.date_range(start=date_last_close, end=end_date, freq="B")
        if hasattr(daily_bars.index, "tz") and daily_bars.index.tz is not None:
            if all_weekdays.tz is None:
                all_weekdays = all_weekdays.tz_localize(daily_bars.index.tz)

        proj_df = pd.DataFrame(
            index=all_weekdays, columns=["Close", "High", "Low", "iHigh", "iLow", "iHigh1", "iLow1"]
        )

        historical_period = daily_bars.loc[date_last_close:date_last]
        for date in historical_period.index:
            if date in proj_df.index:
                proj_df.loc[date, "Close"] = historical_period.loc[date, "Close"]
                proj_df.loc[date, "High"] = historical_period.loc[date, "High"]
                proj_df.loc[date, "Low"] = historical_period.loc[date, "Low"]

        period_days = 5 if frequency == "W" else 22 if frequency == "ME" else 65 if frequency == "QE" else 21
        current_end = date_last_close + period_days * BDay()
        next_end = date_last + period_days * BDay()
        _fill_projection_band(proj_df, date_last_close, current_end, proj_high_cur, proj_low_cur, "iHigh", "iLow")
        _fill_projection_band(proj_df, date_last, next_end, proj_high_next, proj_low_next, "iHigh1", "iLow1")
        return proj_df
    except Exception as e:
        logger.error("Error building projection DataFrame: %s", e)
        return pd.DataFrame()


def _fill_projection_band(
    proj_df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp, proj_high: float, proj_low: float, high_col: str, low_col: str
) -> None:
    """Fill projection band columns with sqrt-interpolated values."""
    try:
        weekdays = pd.date_range(start=start_date, end=end_date, freq="B")[1:]
        start_price = proj_df.loc[start_date, "Close"]
        for i, date in enumerate(weekdays):
            if date in proj_df.index:
                progress = np.sqrt((i + 1) / len(weekdays))
                proj_df.loc[date, high_col] = start_price + (proj_high - start_price) * progress
                proj_df.loc[date, low_col] = start_price + (proj_low - start_price) * progress
    except Exception as e:
        logger.error("Error filling projection band: %s", e)

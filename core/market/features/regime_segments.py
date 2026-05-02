"""Bull/bear regime segmentation.

Domain:    Market Analysis — Regime Segments
Context:
  - Splits a price series into bull (>80% cummax) and bear segments.
Contracts:
  - bull_bear_segments(price_series) -> dict[str, list[pd.Series]]
Dependencies UPWARD:
  - pandas
Dependencies DOWNWARD:
  - core.market.charts.volatility
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def bull_bear_segments(price_series: pd.Series | None) -> dict[str, list[pd.Series]]:
    """Return bull and bear segments based on 80% cummax rule."""
    if price_series is None or price_series.empty:
        return {"bull_segments": [], "bear_segments": []}
    try:
        df = pd.DataFrame(price_series, columns=["Close"])
        df["CumMax"] = df["Close"].cummax()
        df["IsBull"] = df["Close"] >= 0.8 * df["CumMax"]

        if df["IsBull"].nunique() == 1:
            if df["IsBull"].iloc[0]:
                return {"bull_segments": [price_series], "bear_segments": []}
            else:
                return {"bull_segments": [], "bear_segments": [price_series]}

        trend_changes = df["IsBull"] != df["IsBull"].shift(1)
        trend_changes.iloc[0] = True
        segments: dict[str, list[pd.Series]] = {"bull_segments": [], "bear_segments": []}
        current_trend = None
        segment_start = None

        for i, (date, row) in enumerate(df.iterrows()):
            is_trend_change = trend_changes.loc[date]
            if is_trend_change or i == len(df) - 1:
                if segment_start is not None and current_trend is not None:
                    segment_data = price_series.loc[segment_start:date]
                    if len(segment_data) > 1:
                        key = "bull_segments" if current_trend else "bear_segments"
                        segments[key].append(segment_data)
                if i < len(df) - 1:
                    segment_start = date
                    current_trend = row["IsBull"]

        if not segments["bull_segments"] and not segments["bear_segments"]:
            if len(price_series) > 1:
                overall_trend = price_series.iloc[-1] > price_series.iloc[0]
                key = "bull_segments" if overall_trend else "bear_segments"
                segments[key] = [price_series]
        return segments
    except Exception as e:
        logger.error("Error in bull_bear_segments: %s", e)
        return {"bull_segments": [], "bear_segments": []}

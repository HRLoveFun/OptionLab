import numpy as np
import pandas as pd

def calculate_recent_extreme_change(series):
    """
    Calculate the percentage change between latest value and recent extreme value
    Parameters:
    series (pd.Series): Time series data with datetime index
    Returns:
    tuple: (pct_change, extreme_value, extreme_date)
    """
    if len(series) < 2:
        return np.nan, np.nan, np.nan
    series = series.sort_index()
    latest = series.iloc[-1]
    rolling_max = series.expanding(min_periods=1).max()
    rolling_min = series.expanding(min_periods=1).min()
    trend = "up" if latest > series.iloc[-2] else "down"
    if trend == "up":
        mask = (series == rolling_min)
        recent_lows = series[mask]
        if not recent_lows.empty:
            extreme_value = recent_lows.iloc[-1]
            extreme_date = recent_lows.index[-1]
        else:
            extreme_value = series.min()
            extreme_date = series.idxmin()
    else:
        mask = (series == rolling_max)
        recent_highs = series[mask]
        if not recent_highs.empty:
            extreme_value = recent_highs.iloc[-1]
            extreme_date = recent_highs.index[-1]
        else:
            extreme_value = series.max()
            extreme_date = series.idxmax()
    pct_change = ((latest - extreme_value) / extreme_value) * 100
    return pct_change, extreme_value, extreme_date

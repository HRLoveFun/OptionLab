"""Market review computation and formatting.

Domain:    Market Review — Compute & Format
Contracts:
  - market_review(instrument, start_date, end_date) -> pd.DataFrame
Dependencies UPWARD:
  - core.market_review.fetch
Dependencies DOWNWARD:
  - services.market_service
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from core.market_review.fetch import _canonicalize_instrument, fetch_market_data
from utils.data_utils import calculate_recent_extreme_change


def market_review(instrument, start_date: dt.date | None = None, end_date: dt.date | None = None):
    data, returns, display_names = fetch_market_data(instrument, start_date, end_date)
    instrument = _canonicalize_instrument(instrument)
    today = data.index[-1]
    periods = {
        "1M": today - dt.timedelta(days=30),
        "1Q": today - dt.timedelta(days=90),
        "YTD": dt.datetime(today.year, 1, 1),
        "ETD": data.index[0],
    }
    results = pd.DataFrame(index=display_names)
    results["Last Close"] = data.iloc[-1]
    for period, p_start in periods.items():
        period_data = data[data.index >= p_start]
        period_returns = returns[returns.index >= p_start]
        volatility = period_returns.std() * np.sqrt(252) * 100
        results[f"Return ({period})"] = ((period_data.iloc[-1] / period_data.iloc[0]) - 1) * 100
        results[f"Volatility ({period})"] = volatility
    etd_values = []
    etd_dates = []
    for asset in display_names:
        pct_change, _, extreme_date = calculate_recent_extreme_change(data[asset])
        etd_values.append(pct_change)
        etd_dates.append(extreme_date)
    results["Return (ETD)"] = etd_values
    for period, p_start in periods.items():
        period_returns = returns[returns.index >= p_start]
        corr_period = period_returns.corr()
        for asset in display_names:
            if asset == instrument:
                results.loc[asset, f"Correlation ({period})"] = 1.0
            else:
                results.loc[asset, f"Correlation ({period})"] = corr_period.loc[instrument, asset]
    for col in results.columns:
        if "Return" in col or "Volatility" in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        elif "Correlation" in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        elif "Last Close" in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    etd_label = etd_dates[0]
    etd_label_str = pd.to_datetime(etd_label).strftime("%y%b%d").upper() if pd.notna(etd_label) else "ETD"
    arrays = [
        ["Last Close"] + ["Return"] * 4 + ["Volatility"] * 4 + ["Correlation"] * 4,
        [""] + ["1M", "1Q", "YTD", etd_label_str] * 3,
    ]
    tuples = list(zip(*arrays, strict=False))
    multi_index = pd.MultiIndex.from_tuples(tuples, names=["Metric", "Period"])
    col_map = {
        ("Return", "1M"): "Return (1M)", ("Return", "1Q"): "Return (1Q)",
        ("Return", "YTD"): "Return (YTD)", ("Return", etd_label_str): "Return (ETD)",
        ("Volatility", "1M"): "Volatility (1M)", ("Volatility", "1Q"): "Volatility (1Q)",
        ("Volatility", "YTD"): "Volatility (YTD)", ("Volatility", etd_label_str): "Volatility (ETD)",
        ("Correlation", "1M"): "Correlation (1M)", ("Correlation", "1Q"): "Correlation (1Q)",
        ("Correlation", "YTD"): "Correlation (YTD)", ("Correlation", etd_label_str): "Correlation (ETD)",
        ("Last Close", ""): "Last Close",
    }
    ordered_cols = [col_map.get(t, None) for t in tuples if col_map.get(t, None) in results.columns]
    results = results[ordered_cols]
    results.columns = multi_index[: len(results.columns)]
    return results

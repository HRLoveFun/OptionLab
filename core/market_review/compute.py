"""Market review computation (pure).

Turns an already-fetched close-price panel into the returns / volatility /
correlation summary table. No I/O — the panel is supplied by
``services.market_review`` (ADR 0003 / architecture review §2 `core-purity`).

Contracts:
  - build_review(instrument, data, returns, display_names) -> pd.DataFrame
Dependencies:
  - core.market_review.constants (BENCHMARKS, _canonicalize_instrument)
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from core.market_review.constants import _canonicalize_instrument


def build_review(instrument, data, returns, display_names):
    """Build the market-review summary table from a pre-fetched panel.

    Parameters
    ----------
    instrument : str
        The primary instrument (ticker or benchmark display name).
    data : pd.DataFrame
        Wide close-price panel, date-indexed, columns == ``display_names``.
    returns : pd.DataFrame
        Period-over-period returns of ``data`` (same shape).
    display_names : list[str]
        Display names aligned with ``data.columns``.
    """
    instrument = _canonicalize_instrument(instrument)
    today = data.index[-1]
    periods = {
        "1M": today - dt.timedelta(days=30),
        "1Q": today - dt.timedelta(days=90),
        "YTD": dt.datetime(today.year, 1, 1),
    }
    results = pd.DataFrame(index=display_names)
    results["Last Close"] = data.iloc[-1]
    for period, p_start in periods.items():
        period_data = data[data.index >= p_start]
        period_returns = returns[returns.index >= p_start]
        volatility = period_returns.std() * np.sqrt(252) * 100
        results[f"Return ({period})"] = ((period_data.iloc[-1] / period_data.iloc[0]) - 1) * 100
        results[f"Volatility ({period})"] = volatility
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
    arrays = [
        ["Last Close"] + ["Return"] * 3 + ["Volatility"] * 3 + ["Correlation"] * 3,
        [""] + ["1M", "1Q", "YTD"] * 3,
    ]
    tuples = list(zip(*arrays, strict=False))
    multi_index = pd.MultiIndex.from_tuples(tuples, names=["Metric", "Period"])
    col_map = {
        ("Return", "1M"): "Return (1M)",
        ("Return", "1Q"): "Return (1Q)",
        ("Return", "YTD"): "Return (YTD)",
        ("Volatility", "1M"): "Volatility (1M)",
        ("Volatility", "1Q"): "Volatility (1Q)",
        ("Volatility", "YTD"): "Volatility (YTD)",
        ("Correlation", "1M"): "Correlation (1M)",
        ("Correlation", "1Q"): "Correlation (1Q)",
        ("Correlation", "YTD"): "Correlation (YTD)",
        ("Last Close", ""): "Last Close",
    }
    ordered_cols = [col_map.get(t, None) for t in tuples if col_map.get(t, None) in results.columns]
    results = results[ordered_cols]
    results.columns = multi_index[: len(results.columns)]
    return results

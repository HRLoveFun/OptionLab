import numpy as np
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf

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

def market_review(instrument):
    """
    Generate market review for a given financial instrument
    Parameters:
    instrument (str): Yahoo Finance ticker symbol
    Returns:
    tuple: (results_table, fig_correlation)
    """
    benchmarks = {
        'USD': 'DX-Y.NYB',
        'US10Y': '^TNX',
        'Gold': 'GC=F',
        'SPX': '^GSPC',
        'CSI300': '000300.SS',
        'HSI': '^HSI',
        'NKY': '^N225',
        'STOXX': '^STOXX',
    }
    all_tickers = [instrument] + list(benchmarks.values())
    display_names = [instrument] + list(benchmarks.keys())
    data = yf.download(all_tickers, period="400d")['Adj Close']
    data = data.ffill().dropna()
    if data.empty:
        raise ValueError("No data downloaded - check ticker symbols")
    data = data[all_tickers]
    data.columns = display_names
    returns = data.pct_change().dropna()
    today = data.index[-1]
    periods = {
        '1M': today - dt.timedelta(days=30),
        '1Q': today - dt.timedelta(days=90),
        'YTD': dt.datetime(today.year, 1, 1),
        'ETD': data.index[0]
    }
    results = pd.DataFrame(index=display_names)
    results['Last Close'] = data.iloc[-1]
    for period, start_date in periods.items():
        period_data = data[data.index >= start_date]
        period_returns = returns[returns.index >= start_date]
        volatility = period_returns.std() * np.sqrt(252)
        results[f'Volatility ({period})'] = volatility
        period_returns = (period_data.iloc[-1] / period_data.iloc[0]) - 1
        results[f'Return ({period})'] = period_returns
    etd_values = []
    for asset in display_names:
        pct_change, _, _ = calculate_recent_extreme_change(data[asset])
        etd_values.append(pct_change / 100)
    results['Return (ETD)'] = etd_values
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    for i, (period, start_date) in enumerate(periods.items()):
        corr_data = returns[returns.index >= start_date]
        corr_matrix = corr_data.corr()
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(
            corr_matrix,
            mask=mask,
            annot=True,
            fmt=".2f",
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            ax=axes[i],
            linewidths=0.5
        )
        axes[i].set_title(f'Correlation Matrix ({period})', fontsize=14)
        axes[i].tick_params(axis='both', which='major', labelsize=10)
    plt.tight_layout(pad=3.0)
    return results, fig

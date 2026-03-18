import numpy as np
import pandas as pd
import datetime as dt
import yfinance as yf
from utils.data_utils import calculate_recent_extreme_change

def market_review(instrument, start_date: dt.date | None = None, end_date: dt.date | None = None):
    """
    Generate market review for a given financial instrument.
    Parameters:
    instrument (str): Yahoo Finance ticker symbol
    Returns:
    pd.DataFrame: formatted results table
    """
    benchmarks = {
        'USD': 'DX=F',
        'US10Y': '^TNX',
        'Gold': 'GC=F',
        'SPX': '^SPX',
        'CSI300': '000300.SS',
        'HSI': '^HSI',
        'NKY': '^N225',
        'STOXX': '^STOXX',
    }
    all_tickers = [instrument] + list(benchmarks.values())
    display_names = [instrument] + list(benchmarks.keys())
    # Download data within explicit horizon if provided; else fallback to recent period
    if start_date is not None or end_date is not None:
        data = yf.download(all_tickers, start=start_date, end=end_date, auto_adjust=False, progress=False)["Close"]
    else:
        data = yf.download(all_tickers, period="300d", auto_adjust=False, progress=False)["Close"]
    data = data.ffill()
    # Drop benchmark columns that failed entirely (all NaN); raise only if instrument itself has no data
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    valid_tickers = [t for t in all_tickers if t in data.columns and data[t].notna().any()]
    if instrument not in valid_tickers:
        raise ValueError("No data downloaded - check ticker symbols")
    data = data[valid_tickers].dropna()
    if data.empty:
        raise ValueError("No data downloaded - check ticker symbols")
    # Build aligned display name list for available tickers
    ticker_to_display = dict(zip(all_tickers, display_names))
    display_names = [ticker_to_display[t] for t in valid_tickers]
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
    # 计算各周期 return 和 volatility
    for period, start_date in periods.items():
        period_data = data[data.index >= start_date]
        period_returns = returns[returns.index >= start_date]
        volatility = period_returns.std() * np.sqrt(252) * 100
        results[f'Return ({period})'] = ((period_data.iloc[-1] / period_data.iloc[0]) - 1) * 100
        results[f'Volatility ({period})'] = volatility
    # ETD return 用极值法，记录极值点日期
    etd_values = []
    etd_dates = []
    for asset in display_names:
        pct_change, _, extreme_date = calculate_recent_extreme_change(data[asset])
        etd_values.append(pct_change)
        etd_dates.append(extreme_date)
    results['Return (ETD)'] = etd_values
    # 相关性矩阵
    corr = returns.corr()
    for period, start_date in periods.items():
        period_returns = returns[returns.index >= start_date]
        corr_period = period_returns.corr()
        for asset in display_names:
            if asset == instrument:
                results.loc[asset, f'Correlation ({period})'] = 1.0
            else:
                results.loc[asset, f'Correlation ({period})'] = corr_period.loc[instrument, asset]
    # 格式化所有 return/volatility/correlation 列
    for col in results.columns:
        if 'Return' in col or 'Volatility' in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
        elif 'Correlation' in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
        elif 'Last Close' in col:
            results[col] = results[col].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    # 列顺序调整：multiindex，ETD列名用极值点日期
    etd_label = etd_dates[0]
    if pd.notna(etd_label):
        etd_label_str = pd.to_datetime(etd_label).strftime('%y%b%d').upper()
    else:
        etd_label_str = 'ETD'
    arrays = [
        ['Last Close'] + ['Return']*4 + ['Volatility']*4 + ['Correlation']*4,
        [''] + ['1M', '1Q', 'YTD', etd_label_str]*3
    ]
    tuples = list(zip(*arrays))
    multi_index = pd.MultiIndex.from_tuples(tuples, names=["Metric", "Period"])
    col_map = {
        ('Return', '1M'): 'Return (1M)',
        ('Return', '1Q'): 'Return (1Q)',
        ('Return', 'YTD'): 'Return (YTD)',
        ('Return', etd_label_str): 'Return (ETD)',
        ('Volatility', '1M'): 'Volatility (1M)',
        ('Volatility', '1Q'): 'Volatility (1Q)',
        ('Volatility', 'YTD'): 'Volatility (YTD)',
        ('Volatility', etd_label_str): 'Volatility (ETD)',
        ('Correlation', '1M'): 'Correlation (1M)',
        ('Correlation', '1Q'): 'Correlation (1Q)',
        ('Correlation', 'YTD'): 'Correlation (YTD)',
        ('Correlation', etd_label_str): 'Correlation (ETD)',
        ('Last Close', ''): 'Last Close'
    }
    ordered_cols = [col_map.get(t, None) for t in tuples if col_map.get(t, None) in results.columns]
    results = results[ordered_cols]
    results.columns = multi_index[:len(results.columns)]
    return results


def market_review_timeseries(instrument: str, start_date=None, end_date=None) -> dict:
    """Return time-series data for interactive Chart.js rendering.

    Returns dict with dates, per-asset prices/cum_returns/rolling_vol/rolling_corr,
    period markers, and the original summary table HTML as fallback.
    """
    benchmarks = {
        'USD': 'DX=F', 'US10Y': '^TNX', 'Gold': 'GC=F',
        'SPX': '^SPX', 'CSI300': '000300.SS',
        'HSI': '^HSI', 'NKY': '^N225', 'STOXX': '^STOXX',
    }
    all_tickers = [instrument] + list(benchmarks.values())
    display_names = [instrument] + list(benchmarks.keys())

    kw = dict(auto_adjust=False, progress=False)
    if start_date:
        data = yf.download(all_tickers, start=start_date, end=end_date, **kw)["Close"]
    else:
        data = yf.download(all_tickers, period="400d", **kw)["Close"]

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    valid_tickers = [t for t in all_tickers if t in data.columns and data[t].notna().any()]
    if instrument not in valid_tickers:
        raise ValueError("No data for instrument")
    data = data[valid_tickers].ffill().dropna()
    ticker_to_display = dict(zip(all_tickers, display_names))
    valid_display = [ticker_to_display[t] for t in valid_tickers]
    data.columns = valid_display

    returns = data.pct_change().dropna()
    dates = data.index.strftime('%Y-%m-%d').tolist()

    def _safe(series):
        return [round(float(x), 4) if pd.notna(x) else None for x in series]

    assets_out = {}
    for asset in valid_display:
        cum_ret = ((data[asset] / data[asset].iloc[0]) - 1) * 100
        roll_vol = returns[asset].rolling(20).std() * np.sqrt(252) * 100
        if asset != instrument:
            roll_corr = returns[instrument].rolling(20).corr(returns[asset])
        else:
            roll_corr = pd.Series(1.0, index=returns.index)

        # Align all series to same length as dates (data.index)
        assets_out[asset] = {
            "prices": _safe(data[asset]),
            "cum_returns": _safe(cum_ret),
            "rolling_vol": _safe(roll_vol.reindex(data.index)),
            "rolling_corr": _safe(roll_corr.reindex(data.index)),
        }

    today = data.index[-1]
    periods = {
        "1M": (today - pd.Timedelta(days=30)).strftime('%Y-%m-%d'),
        "1Q": (today - pd.Timedelta(days=90)).strftime('%Y-%m-%d'),
        "YTD": f"{today.year}-01-01",
        "ETD": data.index[0].strftime('%Y-%m-%d'),
    }

    # Generate fallback summary table
    try:
        summary_html = market_review(instrument, start_date, end_date).to_html(
            classes='table table-striped', index=True, escape=False)
    except Exception:
        summary_html = ""

    return {
        "dates": dates,
        "assets": assets_out,
        "instrument": instrument,
        "periods": periods,
        "summary_table": summary_html,
    }

import numpy as np
import pandas as pd
import datetime as dt
import time
import threading
import logging
import yfinance as yf
from utils.data_utils import calculate_recent_extreme_change
from utils.utils import yf_throttle

logger = logging.getLogger(__name__)

_YF_MAX_RETRIES = 2
_YF_RETRY_BASE_DELAY = 3  # seconds

# ---------------------------------------------------------------------------
# In-memory cache for market review data (5-min TTL)
# ---------------------------------------------------------------------------
_mr_cache: dict = {}          # key: (instrument, start_str, end_str) → (monotonic_ts, data, returns, valid_display)
_mr_cache_lock = threading.Lock()
_MR_CACHE_TTL = 300  # seconds

BENCHMARKS = {
    'USD': 'DX-Y.NYB',
    'US10Y': '^TNX',
    'Gold': 'GC=F',
    'SPX': '^SPX',
    'CSI300': '000300.SS',
    'HSI': '^HSI',
    'NKY': '^N225',
    'STOXX': '^STOXX',
}


def _yf_download_with_retry(tickers, **kwargs) -> pd.DataFrame:
    """Wrapper around yf.download with retry on rate limit errors."""
    for attempt in range(_YF_MAX_RETRIES):
        try:
            yf_throttle()
            data = yf.download(tickers, **kwargs)
            if data is not None and not data.empty:
                return data
            if attempt < _YF_MAX_RETRIES - 1:
                delay = _YF_RETRY_BASE_DELAY * (attempt + 1)
                logger.warning(f"yfinance returned empty data, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
        except Exception as e:
            is_rate_limit = 'rate' in str(e).lower() or 'too many' in str(e).lower()
            if is_rate_limit and attempt < _YF_MAX_RETRIES - 1:
                delay = _YF_RETRY_BASE_DELAY * (attempt + 1)
                logger.warning(f"yfinance rate limited, retrying in {delay}s (attempt {attempt + 1})")
                time.sleep(delay)
            else:
                raise
    return pd.DataFrame()


def _fetch_market_data(instrument: str, start_date=None, end_date=None):
    """Download and clean benchmark data with DB persistence + in-memory caching.

    Strategy:
      1. L1: in-memory cache (5-min TTL)
      2. L2: SQLite ``market_review_prices`` table
      3. L3: yfinance download for missing days only → upsert to DB

    Returns (data, returns, valid_display).
    """
    cache_key = (instrument, str(start_date), str(end_date))

    # ── L1: in-memory cache ──
    with _mr_cache_lock:
        if cache_key in _mr_cache:
            ts, cached_data, cached_returns, cached_display = _mr_cache[cache_key]
            if time.monotonic() - ts < _MR_CACHE_TTL:
                logger.info("Market review cache hit for %s", instrument)
                return cached_data.copy(), cached_returns.copy(), list(cached_display)
            else:
                del _mr_cache[cache_key]

    all_tickers = [instrument] + list(BENCHMARKS.values())
    display_names = [instrument] + list(BENCHMARKS.keys())
    ticker_to_display = dict(zip(all_tickers, display_names))

    # ── L2/L3: DB-first with incremental yfinance download ──
    from data_pipeline.db import get_conn, DB_PATH, init_db
    init_db()  # ensure table exists

    today_str = dt.date.today().isoformat()

    # Determine date range for query
    if start_date is not None:
        range_start = start_date.isoformat() if isinstance(start_date, dt.date) else str(start_date)
    else:
        range_start = (dt.date.today() - dt.timedelta(days=400)).isoformat()

    # Check which tickers need fresh data
    tickers_needing_download = []
    with get_conn() as conn:
        for t in all_tickers:
            row = conn.execute(
                "SELECT MAX(date) FROM market_review_prices WHERE ticker = ?", (t,)
            ).fetchone()
            latest = row[0] if row and row[0] else None
            if latest is None or latest < today_str:
                tickers_needing_download.append(t)

    # Download missing data from yfinance (only tickers that need it)
    if tickers_needing_download:
        try:
            # Find the earliest latest-date across all tickers to minimize download range
            download_start = range_start
            with get_conn() as conn:
                for t in tickers_needing_download:
                    row = conn.execute(
                        "SELECT MAX(date) FROM market_review_prices WHERE ticker = ?", (t,)
                    ).fetchone()
                    latest = row[0] if row and row[0] else None
                    if latest is None:
                        download_start = range_start
                        break
                    elif latest < download_start:
                        download_start = latest

            kw = dict(auto_adjust=False, progress=False)
            yf_data = _yf_download_with_retry(
                tickers_needing_download, start=download_start, end=today_str, **kw
            )
            if yf_data is not None and not yf_data.empty:
                close_data = yf_data["Close"]
                if isinstance(close_data, pd.Series):
                    close_data = close_data.to_frame(name=tickers_needing_download[0])
                if isinstance(close_data.columns, pd.MultiIndex):
                    close_data.columns = close_data.columns.droplevel(1)

                # Upsert to DB
                rows = []
                for t in tickers_needing_download:
                    if t in close_data.columns:
                        series = close_data[t].dropna()
                        for date_idx, val in series.items():
                            rows.append((t, date_idx.strftime('%Y-%m-%d'), float(val)))
                if rows:
                    with get_conn() as conn:
                        conn.executemany(
                            "INSERT INTO market_review_prices (ticker, date, close) "
                            "VALUES (?, ?, ?) ON CONFLICT(ticker, date) DO UPDATE SET close=excluded.close",
                            rows,
                        )
                        conn.commit()
                    logger.info("Upserted %d market review rows for %s", len(rows),
                                [t for t in tickers_needing_download])
        except Exception as e:
            logger.warning("Market review yfinance download failed: %s", e)

    # Read all data from DB
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT ticker, date, close FROM market_review_prices "
            "WHERE date >= ? ORDER BY date",
            conn, params=(range_start,), parse_dates=["date"],
        )

    if df.empty:
        # Fallback: direct yfinance download (no DB)
        logger.warning("No market review data in DB, falling back to yfinance")
        kw = dict(auto_adjust=False, progress=False)
        if start_date is not None or end_date is not None:
            raw = _yf_download_with_retry(all_tickers, start=start_date, end=end_date, **kw)["Close"]
        else:
            raw = _yf_download_with_retry(all_tickers, period="400d", **kw)["Close"]
        data = raw.ffill()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
    else:
        # Pivot from long-format to wide-format
        data = df.pivot(index='date', columns='ticker', values='close').sort_index().ffill()

    valid_tickers = [t for t in all_tickers if t in data.columns and data[t].notna().any()]
    if instrument not in valid_tickers:
        raise ValueError("No data downloaded - check ticker symbols")
    data = data[valid_tickers].dropna()
    if data.empty:
        raise ValueError("No data downloaded - check ticker symbols")

    valid_display = [ticker_to_display[t] for t in valid_tickers]
    data.columns = valid_display

    returns = data.pct_change(fill_method=None).dropna()

    with _mr_cache_lock:
        _mr_cache[cache_key] = (time.monotonic(), data.copy(), returns.copy(), list(valid_display))

    return data, returns, valid_display


def market_review(instrument, start_date: dt.date | None = None, end_date: dt.date | None = None):
    """
    Generate market review for a given financial instrument.
    Parameters:
    instrument (str): Yahoo Finance ticker symbol
    Returns:
    pd.DataFrame: formatted results table
    """
    data, returns, display_names = _fetch_market_data(instrument, start_date, end_date)
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
    data, returns, valid_display = _fetch_market_data(instrument, start_date, end_date)

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

    # Generate fallback summary table (reuses cached data — no extra download)
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

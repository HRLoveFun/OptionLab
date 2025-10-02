import logging
from typing import Optional
import datetime as dt

import numpy as np
import pandas as pd

from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)


def _get_business_days(start: dt.date, end: dt.date) -> pd.DatetimeIndex:
    """Return business days (Mon-Fri) index for [start, end).

    """
    # Use pandas 'B' frequency which excludes weekends. Holidays are not removed here.
    # pd.date_range with start and end includes the end if it matches the frequency.
    return pd.date_range(start, end, freq="B")


def _flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Price jumps: difference in Close vs previous Close
    ret = np.log(out["close"]).diff()
    thr = 5 * ret.std(skipna=True)
    out["price_jump_flag"] = ((ret.abs() > thr).astype(int)).values
    # Vol anomaly: log delta volume
    lv = np.log(out["volume"]).replace([-np.inf, np.inf], np.nan)
    d_lv = lv.diff()
    thr_v = 5 * d_lv.std(skipna=True)
    out["vol_anom_flag"] = ((d_lv.abs() > thr_v).astype(int)).values
    # OHLC consistency
    out["ohlc_inconsistent"] = (~((out["low"] <= out["open"]).fillna(True) & (out["close"] <= out["high"]).fillna(True))).astype(int)
    return out


def clean_range(ticker: str, start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> int:
    """
    Clean data for [start, end). Align to business days, mark missing days as NA
    (no interpolation for full missing days), flag anomalies, and upsert to clean_prices.
    Returns number of rows written.
    """
    # Treat end as inclusive date
    end = end or dt.date.today()
    start = start or (end - dt.timedelta(days=30))

    # Inclusive end date query
    df = fetch_df(
        "SELECT * FROM raw_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    # Align to business days
    idx = _get_business_days(start, end)
    if df.empty:
        # Create an empty aligned frame with expected columns so subsequent
        # column-based operations work without KeyError.
        aligned = pd.DataFrame(index=idx, columns=[
            "ticker", "open", "high", "low", "close", "adj_close", "volume", "provider"
        ])
    else:
        df = df.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "adj_close": "adj_close",
            "volume": "volume",
        })
        df.index = pd.to_datetime(df.index).tz_localize(None)
        aligned = df.reindex(idx)

    aligned["is_trading_day"] = aligned[["open", "high", "low", "close", "adj_close", "volume"]].notna().any(axis=1).astype(int)
    aligned["missing_any"] = aligned[["open", "high", "low", "close", "adj_close", "volume"]].isna().any(axis=1).astype(int)

    # Interpolate missing field values within trading days: forward fill for volume only (policy)
    aligned["volume"] = aligned["volume"].ffill()

    # Anomalies
    aligned = _flag_anomalies(aligned)

    rows = []
    for d, r in aligned.iterrows():
        date_str = d.date().isoformat()
        rows.append(
            (
                ticker,
                date_str,
                None if pd.isna(r.get("open")) else float(r["open"]),
                None if pd.isna(r.get("high")) else float(r["high"]),
                None if pd.isna(r.get("low")) else float(r["low"]),
                None if pd.isna(r.get("close")) else float(r["close"]),
                None if pd.isna(r.get("adj_close")) else float(r["adj_close"]),
                None if pd.isna(r.get("volume")) else float(r["volume"]),
                int(r.get("is_trading_day", 0)),
                int(r.get("missing_any", 0)),
                int(r.get("price_jump_flag", 0)),
                int(r.get("vol_anom_flag", 0)),
                int(r.get("ohlc_inconsistent", 0)),
            )
        )
    if rows:
        upsert_many(
            "clean_prices",
            [
                "ticker",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "is_trading_day",
                "missing_any",
                "price_jump_flag",
                "vol_anom_flag",
                "ohlc_inconsistent",
            ],
            rows,
        )
    return len(rows)

import datetime as dt
import logging
from typing import Optional

import numpy as np
import pandas as pd

from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)


def _agg_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    return (
        df.resample(rule).agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            adj_close=("adj_close", "last"),
            volume=("volume", "sum"),
        )
    )


def _features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["last_close"] = out["close"].shift(1)
    # 1. Returns
    out["log_return"] = np.log(out["close"]) - np.log(out["close"].shift(1))
    out["amplitude"] = (np.maximum(out["high"], out["close"].shift(1)) - np.minimum(out["low"], out["close"].shift(1))) / out["close"].shift(1)
    out["log_hl_spread"] = np.log(out["high"]) - np.log(out["low"])
    # 2. Volatility proxies
    out["parkinson_var"] = (1.0 / (4.0 * np.log(2.0))) * (np.log(out["high"] / out["low"]) ** 2)
    out["gk_var"] = 0.5 * (np.log(out["high"] / out["low"]) ** 2) - (2 * np.log(2) - 1) * (np.log(out["close"] / out["open"]) ** 2)
    # 3. Volume
    out["log_vol_delta"] = np.log(out["volume"]) - np.log(out["volume"].shift(1))
    out["vol_zscore"] = out["volume"] / out["volume"].rolling(20, min_periods=5).mean()
    # 4. MA and Momentum
    for k in [5, 10, 20, 60, 120, 250]:
        out[f"ma_{k}"] = out["close"].rolling(k, min_periods=max(2, int(k/2))).mean()
    for k in [10, 20, 60]:
        out[f"mom_{k}"] = out["close"] / out["close"].shift(k) - 1.0
    # 5. Oscillation metrics
    out["osc_high"] = (out["high"] / out["last_close"] - 1) * 100
    out["osc_low"] = (out["low"] / out["last_close"] - 1) * 100
    out["osc"] = out["osc_high"] - out["osc_low"]
    return out


def process_frequencies(ticker: str, start: Optional[dt.date] = None, end: Optional[dt.date] = None) -> int:
    """
    Build processed tables for D/W/M using cleaned daily data. Only data within [start, end)
    will be recomputed and upserted.
    """
    # Treat end as inclusive
    end = end or dt.date.today()
    start = start or (end - dt.timedelta(days=90))

    daily = fetch_df(
        "SELECT date, open, high, low, close, adj_close, volume FROM clean_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    if daily.empty:
        logger.info(f"No cleaned data to process for {ticker}")
        return 0
    daily = daily.sort_index()
    # Ensure datetime index without tz
    daily.index = pd.to_datetime(daily.index).tz_localize(None)

    total_rows = 0
    for freq, rule in ("D", "D"), ("W", "W-FRI"), ("M", "ME"):
        if freq == "D":
            agg = daily.copy()
        else:
            agg = _agg_ohlcv(daily, rule)
        feat = _features(agg)
        feat = feat.dropna(how="all")
        rows = []
        for d, r in feat.iterrows():
            rows.append(
                (
                    ticker,
                    d.date().isoformat(),
                    freq,
                    None if pd.isna(r.get("open")) else float(r["open"]),
                    None if pd.isna(r.get("high")) else float(r["high"]),
                    None if pd.isna(r.get("low")) else float(r["low"]),
                    None if pd.isna(r.get("close")) else float(r["close"]),
                    None if pd.isna(r.get("adj_close")) else float(r["adj_close"]),
                    None if pd.isna(r.get("volume")) else float(r["volume"]),
                    None if pd.isna(r.get("last_close")) else float(r["last_close"]),
                    None if pd.isna(r.get("log_return")) else float(r["log_return"]),
                    None if pd.isna(r.get("amplitude")) else float(r["amplitude"]),
                    None if pd.isna(r.get("log_hl_spread")) else float(r["log_hl_spread"]),
                    None if pd.isna(r.get("parkinson_var")) else float(r["parkinson_var"]),
                    None if pd.isna(r.get("gk_var")) else float(r["gk_var"]),
                    None if pd.isna(r.get("log_vol_delta")) else float(r["log_vol_delta"]),
                    None if pd.isna(r.get("vol_zscore")) else float(r["vol_zscore"]),
                    None if pd.isna(r.get("ma_5")) else float(r["ma_5"]),
                    None if pd.isna(r.get("ma_10")) else float(r["ma_10"]),
                    None if pd.isna(r.get("ma_20")) else float(r["ma_20"]),
                    None if pd.isna(r.get("ma_60")) else float(r["ma_60"]),
                    None if pd.isna(r.get("ma_120")) else float(r["ma_120"]),
                    None if pd.isna(r.get("ma_250")) else float(r["ma_250"]),
                    None if pd.isna(r.get("mom_10")) else float(r["mom_10"]),
                    None if pd.isna(r.get("mom_20")) else float(r["mom_20"]),
                    None if pd.isna(r.get("mom_60")) else float(r["mom_60"]),
                    None if pd.isna(r.get("osc_high")) else float(r["osc_high"]),
                    None if pd.isna(r.get("osc_low")) else float(r["osc_low"]),
                    None if pd.isna(r.get("osc")) else float(r["osc"]),
                )
            )
        if rows:
            upsert_many(
                "processed_prices",
                [
                    "ticker",
                    "date",
                    "frequency",
                    "open",
                    "high",
                    "low",
                    "close",
                    "adj_close",
                    "volume",
                    "last_close",
                    "log_return",
                    "amplitude",
                    "log_hl_spread",
                    "parkinson_var",
                    "gk_var",
                    "log_vol_delta",
                    "vol_zscore",
                    "ma_5",
                    "ma_10",
                    "ma_20",
                    "ma_60",
                    "ma_120",
                    "ma_250",
                    "mom_10",
                    "mom_20",
                    "mom_60",
                    "osc_high",
                    "osc_low",
                    "osc",
                ],
                rows,
            )
            total_rows += len(rows)
    return total_rows

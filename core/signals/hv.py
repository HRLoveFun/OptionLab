"""Historical volatility signals.

Domain:    Market Signals — HV
Contracts:
  - hv_pct(close, n) -> float | None
  - hv_percentile(close, n, lookback) -> float | None
  - hv_vs_iv(close, iv_pct, n) -> dict | None
  - hv_context(close) -> dict | None
Dependencies UPWARD:
  - numpy, pandas
Dependencies DOWNWARD:
  - core.signals.bundle
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# DOMAIN: US equity market convention for annualizing daily volatility.
TRADING_DAYS_PER_YEAR = 252


def hv_pct(close: pd.Series, n: int = 20) -> float | None:
    if close is None or len(close) < n + 1:
        return None
    ret = np.log(close).diff().dropna()
    if len(ret) < n:
        return None
    sigma = ret.tail(n).std(ddof=1)
    if not np.isfinite(sigma):
        return None
    return float(sigma * np.sqrt(TRADING_DAYS_PER_YEAR) * 100)


def hv_percentile(close: pd.Series, n: int = 20, lookback: int = 252) -> float | None:
    if close is None or len(close) < n + lookback + 1:
        return None
    ret = np.log(close).diff()
    rolling = ret.rolling(n).std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
    rolling = rolling.dropna().tail(lookback)
    if rolling.empty:
        return None
    current = rolling.iloc[-1]
    if not np.isfinite(current):
        return None
    rank = (rolling < current).sum() / len(rolling) * 100
    return float(round(rank, 1))


def hv_vs_iv(close: pd.Series, iv_pct: float, n: int = 20) -> dict | None:
    hv = hv_pct(close, n=n)
    if hv is None or hv <= 0 or iv_pct is None or iv_pct <= 0:
        return None
    premium = round(iv_pct - hv, 2)
    ratio = round(iv_pct / hv, 3)
    if ratio > 1.20:
        label = "rich"
    elif ratio < 0.80:
        label = "cheap"
    else:
        label = "fair"
    return {"hv": round(hv, 2), "iv": round(iv_pct, 2), "premium": premium, "ratio": ratio, "label": label}


def hv_context(close: pd.Series) -> dict | None:
    """Multi-window HV dict compatible with PriceDynamic output."""
    if close is None or len(close) < 30:
        return None
    try:
        adj = pd.to_numeric(close, errors="coerce")
        log_ret = np.log(adj / adj.shift(1)).dropna()
        windows = [10, 20, 60, 252]
        ann_factor = np.sqrt(TRADING_DAYS_PER_YEAR) * 100
        hv_dict = {
            f"hv_{w}d": float(log_ret.rolling(w, min_periods=max(5, w // 2)).std().iloc[-1] * ann_factor)
            for w in windows
        }
        hv_20_series = log_ret.rolling(20, min_periods=10).std().dropna() * ann_factor
        if len(hv_20_series) >= 60:
            recent_252 = hv_20_series.iloc[-252:]
            current_hv20 = hv_dict["hv_20d"]
            hv_dict["hv_rank"] = float((recent_252 <= current_hv20).sum() / len(recent_252))
            hv_dict["hv_252d_min"] = float(recent_252.min())
            hv_dict["hv_252d_max"] = float(recent_252.max())
        else:
            hv_dict["hv_rank"] = None
        hv_dict["hv_term_slope"] = round(hv_dict["hv_10d"] - hv_dict["hv_60d"], 2)
        return hv_dict
    except Exception as e:
        logger.warning("HV context failed: %s", e)
        return None


def vol_premium_context(close: pd.Series, atm_iv: float | None) -> dict | None:
    """Compare current IV snapshot with historical HV to produce an actionable signal.

    Output format matches the legacy PriceDynamic.build_vol_premium_context().
    """
    hv_ctx = hv_context(close)
    if hv_ctx is None or atm_iv is None:
        return None

    hv_20 = hv_ctx.get("hv_20d")
    hv_rank = hv_ctx.get("hv_rank")

    vol_premium = None
    if hv_20 and hv_20 > 1.0:
        vol_premium = round(atm_iv / hv_20, 3)

    signal = "Insufficient data"
    if vol_premium is not None and hv_rank is not None:
        high_vp = vol_premium > 1.2
        high_hvr = hv_rank > 0.5
        low_vp = vol_premium < 0.85
        low_hvr = hv_rank < 0.4

        if high_vp and high_hvr:
            signal = "Seller environment (IV premium over HV, HV rank mid-high)"
        elif low_vp and low_hvr:
            signal = "Buyer environment (IV discount to HV, HV rank mid-low)"
        elif high_vp and not high_hvr:
            signal = "IV premium but HV low — watch for mean reversion"
        else:
            signal = "Neutral (no clear directional edge)"

    return {
        "atm_iv": round(atm_iv, 2),
        "hv_10d": round(hv_ctx.get("hv_10d", 0), 2),
        "hv_20d": round(hv_20, 2) if hv_20 else None,
        "hv_60d": round(hv_ctx.get("hv_60d", 0), 2),
        "vol_premium": vol_premium,
        "hv_rank_252d": round(hv_rank * 100, 1) if hv_rank else "N/A (insufficient sample)",
        "hv_term_slope": hv_ctx.get("hv_term_slope"),
        "signal": signal,
    }

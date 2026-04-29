"""
Pure-OHLCV market signals (no option-history dependency).

These signals supplement the subjective EV inputs in
``core/option_decision.py`` with objective, calibrated indicators that can be
computed solely from yfinance daily OHLCV data already in the DB.

Functions take a daily-bar DataFrame indexed by Date with columns
``Close``, ``High``, ``Low`` (case-insensitive) and return scalar dicts
suitable for JSON serialisation.

Signals provided:
- ``hv_pct(close, n)``                 — annualised HV over the last n days
- ``hv_percentile(close, n, lookback)`` — current HV vs its 1y/2y distribution
- ``hv_vs_iv(close, n, iv)``            — vol premium = IV - HV (and ratio)
- ``rsi(close, n)``                    — relative strength index
- ``bollinger_position(close, n, k)``   — z-score of current price vs band
- ``mean_reversion_score(close)``       — composite [-1, +1] reversion strength

All functions tolerate NaN-filled DataFrames and missing columns by returning
``None`` rather than raising — callers can branch on missing data.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252


def _close(df: pd.DataFrame) -> pd.Series | None:
    """Return the Close column case-insensitively, or None if missing."""
    if df is None or df.empty:
        return None
    for col in ("Close", "close", "adj_close", "Adj Close"):
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            return s.dropna()
    return None


def hv_pct(close: pd.Series, n: int = 20) -> float | None:
    """Annualised historical volatility (%) over the last n days.

    Uses log-returns and ``sqrt(252)`` annualisation. Returns None if there
    aren't enough data points.
    """
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
    """Where does today's HV sit within the last ``lookback`` rolling-HV values?

    Returns a percentile in [0, 100] or None if data is insufficient.
    """
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
    """Compare current HV (n-day) to a quoted ATM IV (in %).

    Returns a dict with ``hv``, ``iv``, ``premium`` (= iv - hv), ``ratio``
    (= iv / hv) and a label (``cheap`` / ``rich`` / ``fair``).
    Threshold is ±20% on the ratio — calibrated for typical equity index IVs.
    """
    hv = hv_pct(close, n=n)
    if hv is None or hv <= 0 or iv_pct is None or iv_pct <= 0:
        return None
    premium = round(iv_pct - hv, 2)
    ratio = round(iv_pct / hv, 3)
    if ratio > 1.20:
        label = "rich"  # IV elevated → favour selling premium
    elif ratio < 0.80:
        label = "cheap"  # IV depressed → favour buying premium
    else:
        label = "fair"
    return {"hv": round(hv, 2), "iv": round(iv_pct, 2), "premium": premium, "ratio": ratio, "label": label}


def rsi(close: pd.Series, n: int = 14) -> float | None:
    """Wilder-smoothed RSI(n). Returns None on insufficient data."""
    if close is None or len(close) < n + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    val = rsi_series.iloc[-1]
    if not np.isfinite(val):
        return None
    return float(round(val, 2))


def bollinger_position(close: pd.Series, n: int = 20, k: float = 2.0) -> dict | None:
    """Position of current price within Bollinger bands.

    Returns ``{ma, upper, lower, zscore, position}`` where ``position`` is
    one of ``below`` / ``lower_band`` / ``inside`` / ``upper_band`` / ``above``.
    """
    if close is None or len(close) < n:
        return None
    window = close.tail(n)
    ma = window.mean()
    sd = window.std(ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return None
    last = float(close.iloc[-1])
    z = (last - ma) / sd
    upper = ma + k * sd
    lower = ma - k * sd
    if last < lower:
        position = "below"
    elif last < ma - 0.5 * sd:
        position = "lower_band"
    elif last <= ma + 0.5 * sd:
        position = "inside"
    elif last <= upper:
        position = "upper_band"
    else:
        position = "above"
    return {
        "ma": float(round(ma, 4)),
        "upper": float(round(upper, 4)),
        "lower": float(round(lower, 4)),
        "zscore": float(round(z, 3)),
        "position": position,
    }


def mean_reversion_score(close: pd.Series) -> dict | None:
    """Composite mean-reversion score in [-1, +1].

    Combines RSI(14) and 20-day Bollinger z-score:
    -  RSI < 30 contributes a long bias; > 70 contributes short.
    -  z < -2 contributes long; z > +2 contributes short.

    Negative score → market looks oversold (favour bullish);
    positive score → overbought (favour bearish);
    near zero → no edge.
    """
    r = rsi(close, n=14)
    band = bollinger_position(close, n=20, k=2.0)
    if r is None or band is None:
        return None
    rsi_component = 0.0
    if r < 30:
        rsi_component = -(30 - r) / 30  # toward -1 at RSI=0
    elif r > 70:
        rsi_component = (r - 70) / 30  # toward +1 at RSI=100
    z = band["zscore"]
    z_component = 0.0
    if z < -1.5:
        z_component = max(-1.0, z / 2.0)
    elif z > 1.5:
        z_component = min(1.0, z / 2.0)
    score = round(0.5 * rsi_component + 0.5 * z_component, 3)
    label = "neutral"
    if score <= -0.4:
        label = "oversold"
    elif score >= 0.4:
        label = "overbought"
    # WHY: Without an explicit RSI override, mild oversold readings (e.g. RSI=28
    # with z near zero) produce a tiny composite score (~-0.03) and a
    # counter-intuitive "neutral" label. Anchor the label to the canonical
    # RSI thresholds so the UI never contradicts the textbook reading.
    if r <= 30 and label != "oversold":
        label = "oversold"
    elif r >= 70 and label != "overbought":
        label = "overbought"
    return {"score": score, "label": label, "rsi": r, "zscore": z}


def build_signals(df: pd.DataFrame, *, current_iv_pct: float | None = None) -> dict:
    """One-shot bundle: every signal at once.

    Convenience for the ``/api/signals`` endpoint and the front-end card.
    Missing/insufficient data → key set to ``None``.
    """
    close = _close(df)
    return {
        "hv_20": hv_pct(close, n=20),
        "hv_60": hv_pct(close, n=60),
        "hv_20_percentile_1y": hv_percentile(close, n=20, lookback=252),
        "rsi_14": rsi(close, n=14),
        "bollinger_20": bollinger_position(close, n=20, k=2.0),
        "mean_reversion": mean_reversion_score(close),
        "vol_premium": hv_vs_iv(close, current_iv_pct, n=20) if current_iv_pct else None,
    }

"""Signal bundle aggregator.

Domain:    Market Signals — Bundle
Contracts:
  - build_signals(df, current_iv_pct) -> dict
Dependencies UPWARD:
  - core.signals.hv, core.signals.rsi, core.signals.bollinger
Dependencies DOWNWARD:
  - services.signals_service
"""

from __future__ import annotations

import pandas as pd

from core.signals.bollinger import bollinger_position
from core.signals.hv import hv_context, hv_pct, hv_percentile, hv_vs_iv
from core.signals.rsi import rsi


def _close(df: pd.DataFrame) -> pd.Series | None:
    if df is None or df.empty:
        return None
    for col in ("Close", "close", "adj_close", "Adj Close"):
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce")
            return s.dropna()
    return None


def build_signals(df: pd.DataFrame, *, current_iv_pct: float | None = None) -> dict:
    close = _close(df)
    return {
        "hv_20": hv_pct(close, n=20),
        "hv_60": hv_pct(close, n=60),
        "hv_20_percentile_1y": hv_percentile(close, n=20, lookback=252),
        "rsi_14": rsi(close, n=14),
        "bollinger_20": bollinger_position(close, n=20, k=2.0),
        "mean_reversion": mean_reversion_score(close),
        "vol_premium": hv_vs_iv(close, current_iv_pct, n=20) if current_iv_pct else None,
        "hv_context": hv_context(close),
    }


def mean_reversion_score(close: pd.Series) -> dict | None:
    r = rsi(close, n=14)
    band = bollinger_position(close, n=20, k=2.0)
    if r is None or band is None:
        return None
    rsi_component = 0.0
    if r < 30:
        rsi_component = -(30 - r) / 30
    elif r > 70:
        rsi_component = (r - 70) / 30
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
    if r <= 30 and label != "oversold":
        label = "oversold"
    elif r >= 70 and label != "overbought":
        label = "overbought"
    return {"score": score, "label": label, "rsi": r, "zscore": z}

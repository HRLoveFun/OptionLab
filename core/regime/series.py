"""Series-level regime labeling.

Domain:    Market Regime — Series
Contracts:
  - label_regime(as_of, vix_series, spy_close) -> RegimeLabel
  - label_series(vix_series, spy_close) -> pd.DataFrame
  - regime_transitions(df) -> list[dict]
  - coverage_report(df) -> dict
Dependencies UPWARD:
  - pandas, numpy
  - core.regime.classify, core.regime.models
Dependencies DOWNWARD:
  - services.regime_service
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from core.regime.classify import classify_direction, classify_vol
from core.regime.models import RegimeLabel

logger = logging.getLogger(__name__)

# DOMAIN: SMA window used for trend-direction calculations.
SMA_WINDOW = 20

# DOMAIN: lookback distance for computing SMA slope.
SLOPE_LOOKBACK = 5


def label_regime(
    as_of: dt.date, vix_series: pd.Series | None, spy_close: pd.Series | None
) -> RegimeLabel:
    notes: list[str] = []
    vix_val: float | None = None
    if vix_series is not None and not vix_series.empty:
        try:
            s = pd.to_numeric(vix_series, errors="coerce").dropna()
            s = s[s.index <= pd.Timestamp(as_of)]
            if not s.empty:
                vix_val = float(s.iloc[-1])
        except Exception as e:
            logger.warning("VIX parse failed: %s", e)
            notes.append(f"vix_parse_error:{e}")
    vol_regime = classify_vol(vix_val)
    if vol_regime.value.startswith("UNKNOWN"):
        notes.append("vix_missing")

    sma_today = sma_ref = close_today = None
    if spy_close is not None and not spy_close.empty:
        try:
            c = pd.to_numeric(spy_close, errors="coerce").dropna()
            c = c[c.index <= pd.Timestamp(as_of)]
            if len(c) >= SMA_WINDOW + SLOPE_LOOKBACK:
                sma = c.rolling(SMA_WINDOW).mean()
                sma_today = float(sma.iloc[-1])
                sma_ref = float(sma.iloc[-1 - SLOPE_LOOKBACK])
                close_today = float(c.iloc[-1])
            else:
                notes.append(f"spy_insufficient_history:{len(c)}")
        except Exception as e:
            logger.warning("SPY parse failed: %s", e)
            notes.append(f"spy_parse_error:{e}")
    else:
        notes.append("spy_missing")

    dir_regime, slope, close_vs_sma = classify_direction(close_today, sma_today, sma_ref)
    return RegimeLabel(
        date=as_of, vol_regime=vol_regime, dir_regime=dir_regime,
        vix_value=vix_val, sma_20=sma_today, sma_slope_5d=slope,
        close_vs_sma_pct=close_vs_sma, notes=";".join(notes),
    )


def label_series(vix_series: pd.Series, spy_close: pd.Series) -> pd.DataFrame:
    expected_cols = [
        "vol_regime", "dir_regime", "vix_value", "sma_20",
        "sma_slope_5d", "close_vs_sma_pct",
    ]
    empty = pd.DataFrame(columns=expected_cols)
    empty.index.name = "date"
    if spy_close is None or spy_close.empty:
        return empty
    c = pd.to_numeric(spy_close, errors="coerce")
    sma = c.rolling(SMA_WINDOW).mean()
    sma_ref = sma.shift(SLOPE_LOOKBACK)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = (sma - sma_ref) / sma_ref
        close_vs = (c - sma) / sma
    if vix_series is not None and not vix_series.empty:
        v = pd.to_numeric(vix_series, errors="coerce").reindex(c.index).ffill(limit=1)
    else:
        v = pd.Series(np.nan, index=c.index)
    rows = []
    for ts in c.index:
        vol = classify_vol(v.loc[ts] if ts in v.index else None)
        direction, _, _ = classify_direction(c.loc[ts], sma.loc[ts], sma_ref.loc[ts])
        rows.append({
            "date": ts,
            "vol_regime": vol.value,
            "dir_regime": direction.value,
            "vix_value": float(v.loc[ts]) if ts in v.index else None,
            "sma_20": float(sma.loc[ts]) if pd.notna(sma.loc[ts]) else None,
            "sma_slope_5d": float(slope.loc[ts]) if pd.notna(slope.loc[ts]) else None,
            "close_vs_sma_pct": float(close_vs.loc[ts]) if pd.notna(close_vs.loc[ts]) else None,
        })
    df = pd.DataFrame(rows).set_index("date")
    return df


def regime_transitions(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    out: list[dict] = []
    prev_vol = prev_dir = None
    for ts, row in df.iterrows():
        vol = row.get("vol_regime")
        direction = row.get("dir_regime")
        if prev_vol is not None and (vol != prev_vol or direction != prev_dir):
            out.append({
                "date": pd.Timestamp(ts).date().isoformat(),
                "from": f"{prev_vol}|{prev_dir}",
                "to": f"{vol}|{direction}",
            })
        prev_vol, prev_dir = vol, direction
    return out


def coverage_report(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {
            "vol_regimes_observed": [], "dir_regimes_observed": [],
            "unique_composite_regimes": 0, "regime_transitions": [],
            "days_with_unknown": 0, "charter_exit_condition_met": False,
        }
    vols = sorted(set(df["vol_regime"].dropna().astype(str)))
    dirs = sorted(set(df["dir_regime"].dropna().astype(str)))
    composites = set(zip(df["vol_regime"].astype(str), df["dir_regime"].astype(str)))
    unknown_mask = (
        df["vol_regime"].astype(str).str.startswith("UNKNOWN")
        | df["dir_regime"].astype(str).str.startswith("UNKNOWN")
    )
    return {
        "vol_regimes_observed": vols,
        "dir_regimes_observed": dirs,
        "unique_composite_regimes": len(composites),
        "regime_transitions": regime_transitions(df),
        "days_with_unknown": int(unknown_mask.sum()),
        "charter_exit_condition_met": len(composites) >= 2,
    }

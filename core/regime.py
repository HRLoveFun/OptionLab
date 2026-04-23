"""Market regime labeling — pure computation.

Given a volatility series (^VIX close) and a direction series (SPY close),
produce a composite regime label: (VolRegime, DirRegime).

This module is deliberately scope-limited:
  - No trading signals
  - No regime prediction
  - No I/O (fetching / persistence live in services/regime_service.py)
  - Deterministic: same inputs → same outputs
  - Fail-safe: returns UNKNOWN labels rather than raising on missing data
"""

from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import asdict, dataclass
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Regime enums ─────────────────────────────────────────────────
class VolRegime(str, Enum):
    LOW = "LOW_VOL"
    MID = "MID_VOL"
    HIGH = "HIGH_VOL"
    STRESS = "STRESS_VOL"
    UNKNOWN = "UNKNOWN_VOL"


class DirRegime(str, Enum):
    UP = "UP_TREND"
    DOWN = "DOWN_TREND"
    CHOP = "CHOP"
    UNKNOWN = "UNKNOWN_DIR"


# ── Thresholds (centralized) ──────────────────────────────────────
VIX_LOW_MID = 15.0
VIX_MID_HIGH = 20.0
VIX_HIGH_STRESS = 30.0

SMA_WINDOW = 20
SLOPE_LOOKBACK = 5
SLOPE_THRESHOLD = 0.005  # 0.5% 5-day rate of change


@dataclass
class RegimeLabel:
    date: dt.date
    vol_regime: VolRegime
    dir_regime: DirRegime
    vix_value: float | None
    sma_20: float | None
    sma_slope_5d: float | None
    close_vs_sma_pct: float | None
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["vol_regime"] = self.vol_regime.value
        d["dir_regime"] = self.dir_regime.value
        # Replace NaN with None for JSON serialization safety
        for k in ("vix_value", "sma_20", "sma_slope_5d", "close_vs_sma_pct"):
            v = d.get(k)
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                d[k] = None
        return d


# ── Helpers ───────────────────────────────────────────────────────
def _safe_float(x) -> float | None:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def classify_vol(vix_close: float | None) -> VolRegime:
    """Classify volatility regime from a single VIX close value."""
    v = _safe_float(vix_close)
    if v is None:
        return VolRegime.UNKNOWN
    if v < VIX_LOW_MID:
        return VolRegime.LOW
    if v < VIX_MID_HIGH:
        return VolRegime.MID
    if v < VIX_HIGH_STRESS:
        return VolRegime.HIGH
    return VolRegime.STRESS


def classify_direction(
    close_today: float | None,
    sma_today: float | None,
    sma_ref: float | None,
) -> tuple[DirRegime, float | None, float | None]:
    """Classify direction regime.

    Returns (regime, sma_slope_5d, close_vs_sma_pct).
    """
    c = _safe_float(close_today)
    s = _safe_float(sma_today)
    s0 = _safe_float(sma_ref)
    if c is None or s is None or s0 is None or s0 == 0 or s == 0:
        return DirRegime.UNKNOWN, None, None

    slope = (s - s0) / s0
    close_vs_sma = (c - s) / s

    if slope > SLOPE_THRESHOLD and close_vs_sma > 0:
        return DirRegime.UP, slope, close_vs_sma
    if slope < -SLOPE_THRESHOLD and close_vs_sma < 0:
        return DirRegime.DOWN, slope, close_vs_sma
    return DirRegime.CHOP, slope, close_vs_sma


def label_regime(
    as_of: dt.date,
    vix_series: pd.Series | None,
    spy_close: pd.Series | None,
) -> RegimeLabel:
    """Produce a composite regime label for ``as_of``.

    Both series are indexed by date (ascending); only data up to ``as_of`` is used.
    Missing data → UNKNOWN components (never raises).
    """
    notes: list[str] = []

    # --- Volatility component ---
    vix_val: float | None = None
    if vix_series is not None and not vix_series.empty:
        try:
            s = pd.to_numeric(vix_series, errors="coerce").dropna()
            s = s[s.index <= pd.Timestamp(as_of)]
            if not s.empty:
                vix_val = _safe_float(s.iloc[-1])
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("VIX parse failed: %s", e)
            notes.append(f"vix_parse_error:{e}")
    vol_regime = classify_vol(vix_val)
    if vol_regime is VolRegime.UNKNOWN:
        notes.append("vix_missing")

    # --- Direction component ---
    sma_today: float | None = None
    sma_ref: float | None = None
    close_today: float | None = None

    if spy_close is not None and not spy_close.empty:
        try:
            c = pd.to_numeric(spy_close, errors="coerce").dropna()
            c = c[c.index <= pd.Timestamp(as_of)]
            if len(c) >= SMA_WINDOW + SLOPE_LOOKBACK:
                sma = c.rolling(SMA_WINDOW).mean()
                sma_today = _safe_float(sma.iloc[-1])
                sma_ref = _safe_float(sma.iloc[-1 - SLOPE_LOOKBACK])
                close_today = _safe_float(c.iloc[-1])
            else:
                notes.append(f"spy_insufficient_history:{len(c)}")
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("SPY parse failed: %s", e)
            notes.append(f"spy_parse_error:{e}")
    else:
        notes.append("spy_missing")

    dir_regime, slope, close_vs_sma = classify_direction(close_today, sma_today, sma_ref)

    return RegimeLabel(
        date=as_of,
        vol_regime=vol_regime,
        dir_regime=dir_regime,
        vix_value=vix_val,
        sma_20=sma_today,
        sma_slope_5d=slope,
        close_vs_sma_pct=close_vs_sma,
        notes=";".join(notes),
    )


# ── Series-level labeling (for history/backfill) ──────────────────
def label_series(
    vix_series: pd.Series,
    spy_close: pd.Series,
) -> pd.DataFrame:
    """Label every date on which both SMA and slope are computable.

    Returns DataFrame indexed by date with columns:
      vol_regime, dir_regime, vix_value, sma_20, sma_slope_5d, close_vs_sma_pct
    Always returns a DataFrame with these columns (possibly empty) so downstream
    ``.dropna(subset=[...])`` calls are safe.
    """
    expected_cols = [
        "vol_regime",
        "dir_regime",
        "vix_value",
        "sma_20",
        "sma_slope_5d",
        "close_vs_sma_pct",
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

    # Align VIX onto the same index (forward-fill within 1 day only to avoid stale carry)
    if vix_series is not None and not vix_series.empty:
        v = pd.to_numeric(vix_series, errors="coerce").reindex(c.index).ffill(limit=1)
    else:
        v = pd.Series(np.nan, index=c.index)

    rows = []
    for ts in c.index:
        vol = classify_vol(v.loc[ts] if ts in v.index else None)
        direction, _, _ = classify_direction(c.loc[ts], sma.loc[ts], sma_ref.loc[ts])
        rows.append(
            {
                "date": ts,
                "vol_regime": vol.value,
                "dir_regime": direction.value,
                "vix_value": _safe_float(v.loc[ts]) if ts in v.index else None,
                "sma_20": _safe_float(sma.loc[ts]),
                "sma_slope_5d": _safe_float(slope.loc[ts]),
                "close_vs_sma_pct": _safe_float(close_vs.loc[ts]),
            }
        )
    df = pd.DataFrame(rows).set_index("date")
    return df


# ── Regime transitions & coverage (Charter §6 support) ────────────
def regime_transitions(df: pd.DataFrame) -> list[dict]:
    """Given a history DataFrame (output of label_series), list regime changes.

    A transition is recorded when either component (vol or dir) differs
    from the previous row. UNKNOWN_* components participate in transitions.
    """
    if df is None or df.empty:
        return []

    out: list[dict] = []
    prev_vol: str | None = None
    prev_dir: str | None = None
    for ts, row in df.iterrows():
        vol = row.get("vol_regime")
        direction = row.get("dir_regime")
        if prev_vol is not None and (vol != prev_vol or direction != prev_dir):
            out.append(
                {
                    "date": pd.Timestamp(ts).date().isoformat(),
                    "from": f"{prev_vol}|{prev_dir}",
                    "to": f"{vol}|{direction}",
                }
            )
        prev_vol, prev_dir = vol, direction
    return out


def coverage_report(df: pd.DataFrame) -> dict:
    """Summarize regime coverage across the window.

    Supports Learning Period Charter §6 exit condition: ≥2 distinct composite regimes.
    """
    if df is None or df.empty:
        return {
            "vol_regimes_observed": [],
            "dir_regimes_observed": [],
            "unique_composite_regimes": 0,
            "regime_transitions": [],
            "days_with_unknown": 0,
            "charter_exit_condition_met": False,
        }

    vols = sorted(set(df["vol_regime"].dropna().astype(str)))
    dirs = sorted(set(df["dir_regime"].dropna().astype(str)))
    composites = set(zip(df["vol_regime"].astype(str), df["dir_regime"].astype(str)))
    unknown_mask = df["vol_regime"].astype(str).str.startswith("UNKNOWN") | df["dir_regime"].astype(
        str
    ).str.startswith("UNKNOWN")
    return {
        "vol_regimes_observed": vols,
        "dir_regimes_observed": dirs,
        "unique_composite_regimes": len(composites),
        "regime_transitions": regime_transitions(df),
        "days_with_unknown": int(unknown_mask.sum()),
        "charter_exit_condition_met": len(composites) >= 2,
    }

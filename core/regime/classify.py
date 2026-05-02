"""Regime classification helpers.

Domain:    Market Regime — Classification
Contracts:
  - classify_vol(vix_close) -> VolRegime
  - classify_direction(close_today, sma_today, sma_ref) -> tuple[DirRegime, float | None, float | None]
Dependencies UPWARD:
  - core.regime.models
Dependencies DOWNWARD:
  - core.regime.series
"""

from __future__ import annotations

import logging
import math

from core.regime.models import DirRegime, VolRegime

logger = logging.getLogger(__name__)

# DOMAIN: boundary between low and mid volatility regimes.
VIX_LOW_MID = 15.0

# DOMAIN: boundary between mid and high volatility regimes.
VIX_MID_HIGH = 20.0

# DOMAIN: boundary between high and stress volatility regimes.
VIX_HIGH_STRESS = 30.0

# DOMAIN: minimum SMA slope magnitude required to classify a directional trend versus chop.
SLOPE_THRESHOLD = 0.005


def _safe_float(x) -> float | None:
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def classify_vol(vix_close: float | None) -> VolRegime:
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
    close_today: float | None, sma_today: float | None, sma_ref: float | None
) -> tuple[DirRegime, float | None, float | None]:
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

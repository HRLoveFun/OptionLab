"""IV term-structure helpers.

Domain:    Options Analysis — Term Structure
Contracts:
  - atm_iv_for_expiry(puts, spot) -> float | None
  - iv_rank(term_structure) -> float | None
  - iv_percentile(term_structure) -> float | None
  - calc_implied_realized_vol(move_pct, dte) -> float
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.options.charts, services.options_chain_service
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def atm_iv_for_expiry(puts: pd.DataFrame, spot: float) -> float | None:
    """Return ATM implied volatility (as %) for a puts DataFrame."""
    valid = puts.dropna(subset=["impliedVolatility"])
    if valid.empty:
        return None
    idx = (valid["strike"] - spot).abs().idxmin()
    return float(valid.loc[idx, "impliedVolatility"]) * 100


def iv_rank(term_structure: dict[int, float]) -> float | None:
    """IV rank (0–100) from term structure ATM IVs."""
    ivs = list(term_structure.values())
    if len(ivs) < 2:
        return None
    lo, hi = min(ivs), max(ivs)
    if hi == lo:
        return 50.0
    current = ivs[0]
    return round((current - lo) / (hi - lo) * 100, 1)


def iv_percentile(term_structure: dict[int, float]) -> float | None:
    """IV percentile (0–100): % of expiries whose ATM IV < current."""
    ivs = list(term_structure.values())
    if len(ivs) < 2:
        return None
    current = ivs[0]
    below = sum(1 for v in ivs if v < current)
    return round(below / len(ivs) * 100, 1)


def calc_implied_realized_vol(move_pct: float, dte: int) -> float:
    """Annualized realized vol implied by a move over *dte* days."""
    if dte <= 0:
        return 0.0
    T = dte / 365.0
    return abs(move_pct) / np.sqrt(T)

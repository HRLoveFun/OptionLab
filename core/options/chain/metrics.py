"""Option-chain metrics (pure computation).

Domain:    Options Analysis — Chain Metrics
Contracts:
  - max_pain(calls, puts) -> float
  - expected_move(calls, puts, spot) -> float | None
  - skew_25d(puts, calls, spot) -> float | None
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.options.charts, services.options_chain_service
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    """Calculate max pain strike."""
    strikes = sorted(set(calls["strike"]) | set(puts["strike"]))
    losses = []
    for s in strikes:
        call_loss = ((calls["strike"] - s).clip(lower=0) * calls["openInterest"]).sum()
        put_loss = ((s - puts["strike"]).clip(lower=0) * puts["openInterest"]).sum()
        losses.append(call_loss + put_loss)
    return strikes[losses.index(min(losses))]


def expected_move(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> float | None:
    """ATM straddle price as expected move proxy."""
    atm = min(calls["strike"].tolist(), key=lambda x: abs(x - spot))
    c_ask = calls.loc[calls["strike"] == atm, "ask"].values
    p_ask = puts.loc[puts["strike"] == atm, "ask"].values
    if len(c_ask) > 0 and len(p_ask) > 0:
        return float(c_ask[0]) + float(p_ask[0])
    return None


def skew_25d(puts: pd.DataFrame, calls: pd.DataFrame, spot: float) -> float | None:
    """25-delta skew: put IV near 0.97 spot minus call IV near 1.03 spot."""
    try:
        put_iv = puts.loc[(puts["strike"] / spot - 0.97).abs().idxmin(), "impliedVolatility"]
        call_iv = calls.loc[(calls["strike"] / spot - 1.03).abs().idxmin(), "impliedVolatility"]
        return float(put_iv - call_iv)
    except Exception:
        return None

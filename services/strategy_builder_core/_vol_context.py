"""Volatility context builder for strategy entries."""

import logging
from typing import Any

import pandas as pd

from core import signals as signals_mod
from data_pipeline.data_service import DataService

logger = logging.getLogger(__name__)


def _vol_context(ticker: str, current_iv_pct: float | None) -> dict[str, Any]:
    """Build the HV-percentile-based vol context.

    Returns a structured block whose ``label`` is ``cheap`` / ``fair`` /
    ``rich`` based on HV percentile (not IV percentile — see module docstring).
    """
    try:
        from datetime import date, timedelta

        start = date.today() - timedelta(days=400)
        df = DataService.get_cleaned_daily(ticker, start=start)
    except Exception:  # noqa: BLE001
        df = None
    if df is None or df.empty or "close" not in df.columns:
        return {
            "available": False,
            "reason": "no_history",
            "note": "Need ≥60 daily closes; try after running a daily update.",
        }
    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    hv = signals_mod.hv_pct(close, n=20)
    hv_pctile = signals_mod.hv_percentile(close, n=20, lookback=252)
    label = "fair"
    if hv_pctile is not None:
        if hv_pctile <= 25:
            label = "cheap"
        elif hv_pctile >= 75:
            label = "rich"
    return {
        "available": True,
        "hv_20_pct": hv,
        "hv_20_percentile": hv_pctile,
        "current_atm_iv_pct": current_iv_pct,
        "label": label,
        "method": "hv_percentile",
        "disclaimer": (
            "Vol cheap/rich is judged from HV percentile (realized), "
            "not IV percentile — yfinance has no option-chain history."
        ),
    }

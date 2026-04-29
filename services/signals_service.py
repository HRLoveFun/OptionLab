"""Signals service — wraps core/signals over DB-cached daily data."""

from __future__ import annotations

import datetime as dt
import logging

from core import signals as sig
from data_pipeline.data_service import DataService

logger = logging.getLogger(__name__)


def get_signals(ticker: str, *, lookback_days: int = 400, current_iv_pct: float | None = None) -> dict:
    """Compute the full signal bundle for ``ticker`` from DB-cached OHLCV.

    No yfinance call is made directly here — relies on whatever data is
    already cleaned & cached by ``DataService``.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)
    try:
        df = DataService.get_cleaned_daily(ticker, start, end)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_signals: DB fetch failed for %s: %s", ticker, exc)
        return {"status": "error", "message": f"data unavailable: {exc}"}
    if df is None or df.empty:
        return {"status": "error", "message": f"no DB data for {ticker}"}
    bundle = sig.build_signals(df, current_iv_pct=current_iv_pct)
    # Surface the HV-percentile-based vol verdict as a top-level field so
    # the frontend doesn't need to dig into bundle["vol_premium"]. NOTE: this
    # is HV-based, not IV percentile (yfinance has no IV history).
    hv_pctile = bundle.get("hv_20_percentile_1y")
    label = "fair"
    if hv_pctile is not None:
        if hv_pctile <= 25:
            label = "cheap"
        elif hv_pctile >= 75:
            label = "rich"
    return {
        "status": "ok",
        "ticker": ticker,
        "as_of": end.isoformat(),
        "vol_verdict": {
            "label": label,
            "hv_20_percentile": hv_pctile,
            "method": "hv_percentile",
            "disclaimer": "HV-based — yfinance has no IV history.",
        },
        **bundle,
    }

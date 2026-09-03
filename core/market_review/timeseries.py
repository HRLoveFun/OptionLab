"""Market review Chart.js time-series payload (pure).

Builds the per-asset time-series dict consumed by the frontend from an
already-fetched close-price panel. No I/O — the panel is supplied by
``services.market_review`` (ADR 0003 / architecture review §2 `core-purity`).

Contracts:
  - build_timeseries(instrument, data, returns, display_names) -> dict
Dependencies:
  - core.market_review.compute (build_review)
  - core.market_review.constants (_canonicalize_instrument)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.market_review.compute import build_review
from core.market_review.constants import _canonicalize_instrument


def build_timeseries(instrument, data, returns, display_names) -> dict:
    """Build the Chart.js time-series payload from a pre-fetched panel."""
    instrument = _canonicalize_instrument(instrument)
    dates = data.index.strftime("%Y-%m-%d").tolist()

    def _safe(series):
        return [round(float(x), 4) if pd.notna(x) else None for x in series]

    assets_out = {}
    for asset in display_names:
        cum_ret = ((data[asset] / data[asset].iloc[0]) - 1) * 100
        roll_vol = returns[asset].rolling(20).std() * np.sqrt(252) * 100
        roll_corr = (
            returns[instrument].rolling(20).corr(returns[asset])
            if asset != instrument
            else pd.Series(1.0, index=returns.index)
        )
        assets_out[asset] = {
            "prices": _safe(data[asset]),
            "cum_returns": _safe(cum_ret),
            "rolling_vol": _safe(roll_vol.reindex(data.index)),
            "rolling_corr": _safe(roll_corr.reindex(data.index)),
        }

    today = data.index[-1]
    periods = {
        "1M": (today - pd.Timedelta(days=30)).strftime("%Y-%m-%d"),
        "1Q": (today - pd.Timedelta(days=90)).strftime("%Y-%m-%d"),
        "YTD": f"{today.year}-01-01",
    }
    try:
        summary_html = build_review(instrument, data, returns, display_names).to_html(
            classes="table table-striped", index=True, escape=False
        )
    except Exception:
        summary_html = ""
    return {
        "dates": dates,
        "assets": assets_out,
        "instrument": instrument,
        "periods": periods,
        "summary_table": summary_html,
    }

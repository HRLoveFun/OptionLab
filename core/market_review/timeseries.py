"""Market review time-series payload for Chart.js.

Domain:    Market Review — Time Series
Contracts:
  - market_review_timeseries(instrument, start_date, end_date) -> dict
Dependencies UPWARD:
  - core.market_review.fetch, core.market_review.compute
Dependencies DOWNWARD:
  - services.market_service
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.market_review.compute import market_review
from core.market_review.fetch import _canonicalize_instrument, fetch_market_data


def market_review_timeseries(instrument: str, start_date=None, end_date=None) -> dict:
    data, returns, valid_display = fetch_market_data(instrument, start_date, end_date)
    instrument = _canonicalize_instrument(instrument)
    dates = data.index.strftime("%Y-%m-%d").tolist()

    def _safe(series):
        return [round(float(x), 4) if pd.notna(x) else None for x in series]

    assets_out = {}
    for asset in valid_display:
        cum_ret = ((data[asset] / data[asset].iloc[0]) - 1) * 100
        roll_vol = returns[asset].rolling(20).std() * np.sqrt(252) * 100
        roll_corr = returns[instrument].rolling(20).corr(returns[asset]) if asset != instrument else pd.Series(1.0, index=returns.index)
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
        summary_html = market_review(instrument, start_date, end_date).to_html(
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

"""Cross-ticker summary generation for the 综合 tab.

PARKED (2026-09-08 review): ``generate_summary_analysis`` has no runtime
caller — the streaming refactor moved every per-ticker slice through
``services/market/dispatch.py::_RENDER_KIND_SLICES``, but the multi-ticker
Summary tab was never migrated, so ``routes/core.py`` stopped passing
``summary_data`` and the tab button is gated off in ``templates/index.html``.
Kept as the intended implementation for that tab; tracked on the
``docs/architecture_review.md`` §2 watch list with the
``arch_baseline.json`` ``dead_code_candidates`` count at 1. Exit condition:
either wire a summary slice into the dispatch funnel or delete this module
together with ``tab_summary.html`` and the vestigial ``summary_pending`` flag
in ``routes/core.py``.
"""

import logging

logger = logging.getLogger(__name__)


def generate_summary_analysis(tickers: list, results_by_ticker: dict) -> dict:
    """Generate cross-ticker summary data for the 综合 tab (Module 5)."""
    summary = {}

    # Per-ticker info cards
    summary["summaries"] = {}
    for ticker in tickers:
        res = results_by_ticker.get(ticker, {})
        vp = res.get("oc_vol_premium") or {}
        summary["summaries"][ticker] = {
            "price": res.get("oc_snapshot", {}).get("spot") if res.get("oc_snapshot") else None,
            "atm_iv": vp.get("atm_iv"),
            "hv_20d": vp.get("hv_20d"),
            "vol_premium": vp.get("vol_premium"),
            "signal": vp.get("signal"),
        }

    # Correlation matrix
    try:
        from data_pipeline.yf_client import fetch_close_panel

        data = fetch_close_panel(tickers, period="90d")
        if data is None or data.empty:
            raise RuntimeError("empty close panel")
        data = data.ffill().dropna()
        corr = data.pct_change(fill_method=None).dropna().corr().round(3)
        summary["correlation_matrix"] = {
            "labels": list(corr.columns),
            "values": corr.values.tolist(),
        }
    except Exception as e:
        logger.warning(f"Correlation matrix failed: {e}")
        summary["correlation_matrix"] = None

    # Vol comparison table
    summary["vol_comparison"] = [
        {
            "ticker": t,
            "atm_iv": results_by_ticker.get(t, {}).get("oc_vol_premium", {}).get("atm_iv")
            if results_by_ticker.get(t, {}).get("oc_vol_premium")
            else None,
            "hv_20d": results_by_ticker.get(t, {}).get("oc_vol_premium", {}).get("hv_20d")
            if results_by_ticker.get(t, {}).get("oc_vol_premium")
            else None,
            "vol_premium": results_by_ticker.get(t, {}).get("oc_vol_premium", {}).get("vol_premium")
            if results_by_ticker.get(t, {}).get("oc_vol_premium")
            else None,
            "signal": results_by_ticker.get(t, {}).get("oc_vol_premium", {}).get("signal")
            if results_by_ticker.get(t, {}).get("oc_vol_premium")
            else None,
        }
        for t in tickers
    ]

    return summary

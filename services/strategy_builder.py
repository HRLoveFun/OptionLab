"""Auto-build option strategies from the live chain.

Bridges the gap between abstract strategy templates (``core.strategies``) and
the real bid/ask quotes available in the current option chain.

NOTE: This module now delegates helpers to ``services.strategy_builder_core``.
The public entry-point ``build_from_chain`` remains here so that test
monkey-patches on ``sb.fetch_option_chain`` and ``sb.DataService`` continue
to work during the transition.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core import strategies as strategies_mod
from data_pipeline.yf_client import fetch_option_chain
from services.strategy_builder_core import TEMPLATES, _mid, _row_for_strike, _vol_context
from utils.api_errors import ApiError

logger = logging.getLogger(__name__)


def build_from_chain(
    ticker: str,
    template: str,
    expiry: str,
    strikes: dict[str, float],
    qty: int = 1,
) -> dict[str, Any]:
    """Materialise a strategy from the live chain and analyse it.

    Parameters
    ----------
    ticker
        Underlying symbol.
    template
        Key of :data:`TEMPLATES`.
    expiry
        ISO ``YYYY-MM-DD`` expiry that exists in the chain.
    strikes
        Mapping of strike keys (per template) to numeric strike prices.
    qty
        Contracts per leg (positive integer).

    Returns
    -------
    dict
        ``{ "ticker", "template", "expiry", "spot", "legs", "analytics",
            "vol_context", "slippage" }``.

    Raises
    ------
    ApiError
        On bad template, missing expiry, or missing strikes in the chain.
    """
    spec = TEMPLATES.get(template)
    if spec is None:
        raise ApiError(f"unknown strategy template: {template}", code="bad_template")

    missing = [k for k in spec["strikes"] if k not in strikes]
    if missing:
        raise ApiError(
            f"missing strikes for template {template}: {missing}",
            code="missing_strikes",
            details={"required": spec["strikes"]},
        )

    snap = fetch_option_chain(ticker)
    spot = snap.get("spot")
    if not snap["chain"]:
        raise ApiError(
            f"no option chain available for {ticker}",
            code="chain_unavailable",
            status=502,
        )
    if expiry not in snap["chain"]:
        raise ApiError(
            f"expiry {expiry} not available for {ticker}",
            code="expiry_unavailable",
            details={"available": list(snap["chain"].keys())[:10]},
        )

    chain = snap["chain"][expiry]
    legs: list[strategies_mod.Leg] = []
    leg_diagnostics: list[dict[str, Any]] = []
    total_mid_cost = 0.0
    total_ask_cost = 0.0

    try:
        dte = max((pd.Timestamp(expiry) - pd.Timestamp.utcnow().normalize()).days, 1)
    except Exception:  # noqa: BLE001
        dte = 30

    for opt_type, side, strike_key in spec["legs"]:
        strike = float(strikes[strike_key])
        df = chain["calls"] if opt_type == "call" else chain["puts"]
        row = _row_for_strike(df, strike)
        if row is None:
            raise ApiError(
                f"strike {strike} ({opt_type}) not found in chain",
                code="strike_unavailable",
            )
        bid = row.get("bid")
        ask = row.get("ask")
        last = row.get("lastPrice")
        mid = _mid(bid, ask, last)
        if mid is None or mid <= 0:
            raise ApiError(
                f"no usable price for {opt_type} {strike}",
                code="no_price",
                details={"bid": float(bid or 0), "ask": float(ask or 0)},
            )
        iv = float(row.get("impliedVolatility") or 0.0) or 0.25
        leg = strategies_mod.Leg(
            side=side,  # type: ignore[arg-type]
            option_type=opt_type,  # type: ignore[arg-type]
            strike=strike,
            premium=float(mid),
            qty=int(qty),
            dte=dte,
            iv=iv,
        )
        legs.append(leg)
        from core.options.chain.liquidity import liquidity_score

        liq_label, liq_reason = liquidity_score(
            strike,
            float(bid or 0),
            float(ask or 0),
            float(last or 0),
            float(row.get("openInterest") or 0),
            float(row.get("volume") or 0),
            float(spot or strike),
        )
        spread = float(ask or 0) - float(bid or 0)
        leg_diagnostics.append(
            {
                "side": side,
                "option_type": opt_type,
                "strike": strike,
                "bid": float(bid or 0),
                "ask": float(ask or 0),
                "mid": mid,
                "last": float(last or 0),
                "iv_pct": iv * 100,
                "open_interest": float(row.get("openInterest") or 0),
                "volume": float(row.get("volume") or 0),
                "spread": spread,
                "liquidity": liq_label,
                "liquidity_reason": liq_reason,
            }
        )
        sign = 1 if side == "long" else -1
        total_mid_cost += sign * mid * qty * 100
        worst = float(ask) if side == "long" else float(bid)
        total_ask_cost += sign * worst * qty * 100

    analytics = strategies_mod.analyze_strategy(legs, float(spot or legs[0].strike))

    avg_iv_pct = (
        sum(d["iv_pct"] for d in leg_diagnostics) / len(leg_diagnostics)
        if leg_diagnostics
        else None
    )

    return {
        "status": "ok",
        "ticker": ticker,
        "template": template,
        "expiry": expiry,
        "dte": dte,
        "spot": spot,
        "legs": leg_diagnostics,
        "analytics": analytics,
        "vol_context": _vol_context(ticker, current_iv_pct=avg_iv_pct),
        "slippage": {
            "mid_cost_usd": total_mid_cost,
            "worst_cost_usd": total_ask_cost,
            "slippage_usd": total_ask_cost - total_mid_cost,
        },
    }

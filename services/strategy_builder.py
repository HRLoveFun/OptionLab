"""Auto-build option strategies from the live chain.

Bridges the gap between abstract strategy templates (``core.strategies``) and
the real bid/ask quotes available in the current option chain. Given a
template name, an expiry, and a strikes spec, returns:

* the populated ``Leg`` list (with mid premium and chain IV),
* the full ``analyze_strategy`` result (P&L curve, breakevens, Greeks, PoP),
* per-leg liquidity scores and a slippage estimate (mid→ask cost),
* a vol-context block (HV percentile, current ATM IV, plain-language
  cheap/fair/rich label) to answer *"is this strategy entered into cheap or
  rich vol?"* WITHOUT relying on IV history we don't have.

Why no IV rank: yfinance does not expose option-chain history, so we cannot
compute IV percentile against past IV. HV percentile (computed from daily
closes, which DO have history) is the closest legitimate proxy. The vol
context block makes that explicit.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core import signals as signals_mod
from core import strategies as strategies_mod
from core.options.chain.liquidity import liquidity_score
from data_pipeline.data_service import DataService
from data_pipeline.yf_client import fetch_option_chain
from utils.api_errors import ApiError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
# Each template is described as a list of (option_type, side, strike_key) tuples.
# The strike_key references which entry of the user-supplied ``strikes`` dict
# to use for that leg. ``factory`` names the matching builder in core.strategies.
TEMPLATES: dict[str, dict[str, Any]] = {
    "long_call": {
        "factory": "long_call",
        "legs": [("call", "long", "k")],
        "strikes": ["k"],
    },
    "long_put": {
        "factory": "long_put",
        "legs": [("put", "long", "k")],
        "strikes": ["k"],
    },
    "short_call": {
        "factory": "short_call",
        "legs": [("call", "short", "k")],
        "strikes": ["k"],
    },
    "short_put": {
        "factory": "short_put",
        "legs": [("put", "short", "k")],
        "strikes": ["k"],
    },
    "bull_call_spread": {
        "factory": "bull_call_spread",
        "legs": [("call", "long", "k_long"), ("call", "short", "k_short")],
        "strikes": ["k_long", "k_short"],
    },
    "bear_put_spread": {
        "factory": "bear_put_spread",
        "legs": [("put", "long", "k_long"), ("put", "short", "k_short")],
        "strikes": ["k_long", "k_short"],
    },
    "iron_condor": {
        "factory": "iron_condor",
        "legs": [
            ("put", "long", "k_put_long"),
            ("put", "short", "k_put_short"),
            ("call", "short", "k_call_short"),
            ("call", "long", "k_call_long"),
        ],
        "strikes": ["k_put_long", "k_put_short", "k_call_short", "k_call_long"],
    },
    "long_straddle": {
        "factory": "long_straddle",
        "legs": [("call", "long", "k"), ("put", "long", "k")],
        "strikes": ["k"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _row_for_strike(df: pd.DataFrame, strike: float) -> pd.Series | None:
    """Return the chain row whose strike is closest to ``strike`` (within $1)."""
    if df is None or df.empty or "strike" not in df.columns:
        return None
    diffs = (df["strike"] - strike).abs()
    idx = diffs.idxmin()
    if diffs.loc[idx] > 1.0:
        return None
    return df.loc[idx]


def _mid(bid: float | None, ask: float | None, last: float | None) -> float | None:
    """Mid of bid/ask; fall back to ``last`` only if both sides missing."""
    b = float(bid) if bid is not None and not pd.isna(bid) else None
    a = float(ask) if ask is not None and not pd.isna(ask) else None
    if b is not None and a is not None and b > 0 and a > 0:
        return (b + a) / 2.0
    if last is not None and not pd.isna(last) and float(last) > 0:
        return float(last)
    return None


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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
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

    # Convert expiry to DTE so Greeks / PoP work even before user enters DTE.
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
        # When opening, longs pay ask, shorts get bid: worst-case is mid→ask gap.
        worst = float(ask) if side == "long" else float(bid)
        total_ask_cost += sign * worst * qty * 100

    analytics = strategies_mod.analyze_strategy(legs, float(spot or legs[0].strike))

    # Average ATM IV across long-call/long-put legs (sentiment proxy).
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

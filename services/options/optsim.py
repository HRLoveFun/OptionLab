"""Option portfolio simulator service for the Position Simulator tab.

Domain:    Option Simulation — service layer
Context:
  - Validates the JSON payload of ``POST /api/optsim`` — a hypothetical
    multi-leg position (legs, spot, rates, IV smile, exercise style, margin
    class) — and hands the maths to :mod:`core.optsim`. No market data is read.
  - Bounds each request so one call stays interactive: at most 6 legs,
    DTE <= 730, at most ~9 date slices, IV shifts revalued at entry only.
  - Strikes may be given directly or picked by absolute delta (0.16 = 16Δ);
    delta-picked strikes are rounded to a tick of about 0.1% of spot.
Contracts:
  - run_optsim(payload) -> dict
  - strike_tick(spot) -> float
Dependencies UPWARD:
  - numpy, core.optsim, utils.api_errors
Dependencies DOWNWARD:
  - routes.strategies, tests
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from core.optsim import (
    PRODUCTS,
    Market,
    Position,
    Smile,
    breakevens,
    default_days,
    make_leg,
    option_greeks,
    scenario_grid,
    strike_for_delta,
    time_profile,
)
from core.optsim.charts import chart_days
from core.optsim.engine import GREEKS
from utils.api_errors import ApiError

# CONSTRAINT: six legs cover condors, butterflies and broken wings; each leg adds a tree on the American path.
MAX_LEGS = 6
# CONSTRAINT: two years of DTE bounds the tree depth per American leg on the web path.
MAX_DTE = 730
# CONSTRAINT: contracts per leg — the same cap as POST /api/simulate_expiry.
MAX_QTY = 1000
# CONSTRAINT: odd, so the entry spot sits on the grid; the CLI default resolution.
N_SPOTS = 61
# TRADEOFF: the web grid keeps at most ~8 evenly spaced date slices (plus every
# expiry) and revalues IV shifts at entry only — the full CLI grid takes 6-50 s
# for an American iron condor, this one about one second.
MAX_SLICES = 8
# TRADEOFF: 100 tree steps for American legs on the web path. Worst-case price
# error is about 0.02 per $100 of strike (0.007 at the CLI's 200 steps), for a
# third of the time per request.
WEB_TREE_STEPS = 100

_TICKS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0)


def strike_tick(spot: float) -> float:
    """Coarsest listed-style strike tick no wider than 0.1% of spot."""
    budget = spot * 0.001
    return max((t for t in _TICKS if t <= budget), default=_TICKS[0])


def _number(raw: Any, name: str, lo: float, hi: float, code: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ApiError(f"{name} must be a number", code=code) from None
    if not math.isfinite(value) or not lo <= value <= hi:
        raise ApiError(f"{name} must be between {lo:g} and {hi:g}", code=code, details={"value": raw})
    return value


def _field(payload: dict, key: str, default: float, lo: float, hi: float, code: str) -> float:
    raw = payload.get(key)
    return _number(default if raw in (None, "") else raw, key, lo, hi, code)


def _integer(raw: Any, name: str, lo: int, hi: int, code: str) -> int:
    value = _number(raw, name, lo, hi, code)
    if value != int(value):
        raise ApiError(f"{name} must be a whole number", code=code, details={"value": raw})
    return int(value)


def _choice(raw: Any, name: str, options: tuple[str, ...], code: str) -> str:
    value = str(raw or "").strip().lower()
    if value not in options:
        raise ApiError(f"{name} must be one of: {', '.join(options)}", code=code)
    return value


def _leg(spec: Any, n: int, market: Market, smile: Smile, style: str):
    if not isinstance(spec, dict):
        raise ApiError(f"leg {n} must be an object", code="invalid_leg")
    kind = _choice(spec.get("type"), f"leg {n} type", ("call", "put"), "invalid_leg")
    side = _choice(spec.get("side") or "long", f"leg {n} side", ("long", "short"), "invalid_leg")
    qty = _integer(spec.get("qty", 1), f"leg {n} qty", 1, MAX_QTY, "invalid_qty")
    dte = _integer(spec.get("dte"), f"leg {n} dte", 1, MAX_DTE, "invalid_dte")
    has_strike = spec.get("strike") not in (None, "")
    if has_strike == (spec.get("delta") not in (None, "")):
        raise ApiError(f"leg {n}: give either a strike or a delta", code="invalid_leg")
    if has_strike:
        # Same window strike_for_delta searches: 20%-300% of spot.
        strike = _number(spec["strike"], f"leg {n} strike", 0.2 * market.spot, 3.0 * market.spot, "invalid_strike")
    else:
        delta = abs(_number(spec["delta"], f"leg {n} delta", -0.99, 0.99, "invalid_delta"))
        if delta < 0.01:
            raise ApiError(f"leg {n} delta must be between 0.01 and 0.99 in absolute value", code="invalid_delta")
        signed = delta if kind == "call" else -delta
        strike = strike_for_delta(kind, signed, dte, market, smile, strike_tick(market.spot))
    return make_leg(kind, side, strike, dte, market, smile=smile, qty=qty, style=style, steps=WEB_TREE_STEPS)


def _rounded(values, digits: int) -> list:
    return np.round(np.asarray(values, dtype=float), digits).tolist()


def run_optsim(payload: dict | None) -> dict:
    """Validate ``payload`` and revalue the position on spot × date (× IV at entry).

    Percent inputs: ``rate``, ``div_yield``, ``atm_iv``, ``spot_range``;
    ``iv_shift`` is in vol points. Returns ``{"status": "ok", ...}`` with the
    resolved legs, P&L and Greeks by date, P&L at entry under IV shifts and a
    per-date profile (value, Greeks, Reg-T and PM) at the entry spot.
    """
    payload = payload or {}
    if payload.get("spot") in (None, ""):
        raise ApiError("spot is required", code="spot_required")
    spot = _field(payload, "spot", None, 0.01, 1e7, "invalid_spot")
    market = Market(
        spot=spot,
        rate=_field(payload, "rate", 4.5, -5, 50, "invalid_rate") / 100,
        div_yield=_field(payload, "div_yield", 0.0, 0, 20, "invalid_div_yield") / 100,
    )
    smile = Smile(
        atm_iv=_field(payload, "atm_iv", 20.0, 1, 300, "invalid_iv") / 100,
        skew=_field(payload, "skew", 0.0, -5, 5, "invalid_smile"),
        curvature=_field(payload, "curvature", 0.0, -20, 50, "invalid_smile"),
    )
    style = _choice(payload.get("style") or "european", "style", ("european", "american"), "invalid_style")
    product = _choice(payload.get("product") or "index", "product", tuple(PRODUCTS), "invalid_product")
    multiplier = _integer(payload.get("multiplier", 100), "multiplier", 1, 10_000, "invalid_multiplier")
    spot_range = _field(payload, "spot_range", 15.0, 5, 50, "invalid_spot_range") / 100
    iv_shift = _field(payload, "iv_shift", 5.0, 0, 20, "invalid_iv_shift") / 100

    specs = payload.get("legs")
    if not isinstance(specs, list) or not specs:
        raise ApiError("legs must be a non-empty list", code="legs_required")
    if len(specs) > MAX_LEGS:
        raise ApiError(f"too many legs (max {MAX_LEGS})", code="too_many_legs", details={"count": len(specs)})
    legs = [_leg(spec, i + 1, market, smile, style) for i, spec in enumerate(specs)]
    position = Position(legs, style=style, multiplier=multiplier, product=product)

    last = max(leg.dte for leg in legs)
    days = default_days(position, step=max(7, math.ceil(last / MAX_SLICES)))
    grid_args = {"spot_range": spot_range, "n_spots": N_SPOTS, "steps": WEB_TREE_STEPS}
    main = scenario_grid(position, market, days=days, iv_shifts=(0.0,), **grid_args)
    shifts = (-iv_shift, 0.0, iv_shift) if iv_shift > 0 else (0.0,)
    entry = scenario_grid(position, market, days=[0.0], iv_shifts=shifts, **grid_args) if iv_shift > 0 else main

    leg_rows = []
    for leg in legs:
        greeks = option_greeks(
            leg.option_type,
            spot,
            leg.strike,
            leg.dte / 365.0,
            market.rate,
            market.div_yield,
            leg.iv,
            style,
            WEB_TREE_STEPS,
        )
        leg_rows.append(
            {
                "type": leg.option_type,
                "side": leg.side,
                "qty": leg.qty,
                "dte": leg.dte,
                "strike": round(leg.strike, 4),
                "iv": round(leg.iv, 6),
                "premium": round(leg.premium, 4),
                "delta": round(float(greeks["delta"]), 4),
            }
        )

    profile = [{k: (v if isinstance(v, str) else round(v, 4)) for k, v in row.items()} for row in time_profile(main)]
    return {
        "status": "ok",
        "style": style,
        "product": product,
        "multiplier": multiplier,
        "spot": spot,
        "tree_steps": WEB_TREE_STEPS if style == "american" else None,
        "legs": leg_rows,
        "entry_value": round(main.entry_value, 2),
        "spots": _rounded(main.spots, 4),
        "days": _rounded(main.days, 0),
        "chart_days": chart_days(main.days),
        "pnl_by_day": _rounded(main.pnl[0], 2),
        "greeks_by_day": {k: _rounded(getattr(main, k)[0], 4) for k in GREEKS},
        "iv_shifts": _rounded(entry.iv_shifts, 4),
        "pnl_by_iv_at_entry": _rounded(entry.pnl[:, 0, :], 2),
        "breakevens": [round(b, 2) for b in breakevens(main.spots, main.pnl[0, -1])],
        "profile": profile,
    }

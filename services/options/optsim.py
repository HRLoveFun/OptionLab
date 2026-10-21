"""Option portfolio simulator service for the Position Simulator tab.

Domain:    Option Simulation — service layer
Context:
  - Validates the JSON payload of ``POST /api/optsim`` — a multi-leg position
    (legs, rates, exercise style, margin class, grid) and the market it is
    priced in — and hands the maths to :mod:`core.optsim`.
  - Two markets (``market``). ``hypothetical`` (default) takes spot and an IV
    smile from the payload and reads no market data. ``ticker`` takes spot,
    listed expiries and strikes and each leg's IV from the option chain of
    ``ticker``, through the option-chain preload cache (15-minute TTL, fetched
    on a miss). Rate, dividend yield and margin class come from the payload in
    both, so the two modes differ only in what the chain can tell.
  - Bounds each request so one call stays interactive: at most 6 legs,
    DTE <= 730, at most 8 evenly spaced date slices plus every expiry, IV shifts
    revalued at entry only, break-even IV on the chart dates only.
  - Strikes may be given directly, as "atm", or by absolute delta (0.16 = 16Δ).
    Hypothetical: delta-picked and ATM strikes round to ``strike_tick(spot)``.
    Ticker: every strike snaps to the nearest listed one, and the DTE to the
    nearest listed expiry.
Contracts:
  - run_optsim(payload) -> dict
  - strike_tick(spot) -> float
Dependencies UPWARD:
  - numpy, core.optsim, services.options.preload, utils.api_errors, utils.ticker_utils
Dependencies DOWNWARD:
  - routes.strategies, tests
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from core.optsim import (
    PRODUCTS,
    Market,
    Position,
    Smile,
    breakeven_iv,
    breakevens,
    default_days,
    iv_curve,
    leg_iv,
    listed_market,
    make_leg,
    nearest_expiry,
    nearest_quote,
    option_greeks,
    scenario_grid,
    strike_for_delta,
    time_profile,
)
from core.optsim.charts import chart_days
from core.optsim.engine import GREEKS
from core.optsim.market import IvCurve, ListedMarket
from services.options import preload
from utils.api_errors import ApiError
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

MARKETS = ("hypothetical", "ticker")

# CONSTRAINT: six legs cover condors, butterflies and broken wings; each leg adds a tree on the American path.
MAX_LEGS = 6
# CONSTRAINT: two years of DTE bounds the tree depth per American leg on the web path.
MAX_DTE = 730
# CONSTRAINT: contracts per leg — the same cap as POST /api/simulate_expiry.
MAX_QTY = 1000
# CONSTRAINT: odd, so the entry spot sits on the grid; the CLI default resolution.
N_SPOTS = 61
# TRADEOFF: the web grid keeps at most 8 evenly spaced date slices (plus every
# expiry) and revalues IV shifts at entry only — the full CLI grid takes 6-50 s
# for an American iron condor, this one about one second.
MAX_SLICES = 8
# TRADEOFF: 100 tree steps for American legs on the web path. Worst-case price
# error is about 0.02 per $100 of strike (0.007 at the CLI's 200 steps), for a
# third of the time per request.
WEB_TREE_STEPS = 100
# CONSTRAINT: longer than any Yahoo or futu symbol; keeps junk out of the chain cache keys.
MAX_TICKER_LEN = 20

_TICKS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0)


def strike_tick(spot: float) -> float:
    """Coarsest tick of a fixed ladder ($0.01-$50) no wider than 0.1% of spot; $0.01 below a $10 spot."""
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


def _listed(raw: Any) -> ListedMarket:
    """The ticker's listed market, from the option-chain preload cache (fetched on a miss)."""
    ticker = str(raw or "").strip().upper()
    if not ticker:
        raise ApiError("ticker mode needs a ticker", code="ticker_required")
    if len(ticker) > MAX_TICKER_LEN or any(c.isspace() for c in ticker):
        raise ApiError("ticker is not a valid symbol", code="invalid_ticker", details={"value": raw})
    try:
        ticker, _ = normalize_ticker(ticker)
    except ValueError:
        pass
    snap = preload.get_cached(ticker)
    if snap is None:
        try:
            snap = preload.build_preload_payload(ticker)
        except Exception as exc:  # noqa: BLE001 — the provider fails in many ways; all mean "no chain"
            logger.warning("optsim: option chain for %s unavailable: %s", ticker, exc)
            raise ApiError(
                f"could not load the option chain for {ticker}", code="chain_unavailable", status=502
            ) from None
        # WHY: an empty chain is usually a transient Yahoo failure; caching it would pin the miss for 15 minutes.
        if snap.get("chain"):
            preload.set_cached(ticker, snap)
    try:
        listed = listed_market(ticker, snap.get("spot"), snap.get("chain") or {}, as_of=snap.get("fetched_at"))
    except ValueError:
        raise ApiError(f"no spot price for {ticker}", code="chain_unavailable", status=502) from None
    if not listed.expiries:
        raise ApiError(f"{ticker} has no listed options a day or more out", code="chain_unavailable", status=502)
    return listed


def _hypothetical_extras() -> dict:
    return {"expiry": None, "iv_source": "smile", "bid": None, "ask": None, "mid": None}


def _leg_spec(spec: Any, n: int) -> dict:
    """Validate the parts of one leg spec that do not depend on spot (checked before any chain fetch)."""
    if not isinstance(spec, dict):
        raise ApiError(f"leg {n} must be an object", code="invalid_leg")
    kind = _choice(spec.get("type"), f"leg {n} type", ("call", "put"), "invalid_leg")
    parsed = {
        "kind": kind,
        "side": _choice(spec.get("side") or "long", f"leg {n} side", ("long", "short"), "invalid_leg"),
        "qty": _integer(spec.get("qty", 1), f"leg {n} qty", 1, MAX_QTY, "invalid_qty"),
        "dte": _integer(spec.get("dte"), f"leg {n} dte", 1, MAX_DTE, "invalid_dte"),
        "atm": False,
        "signed": None,
        "strike": None,
    }
    raw_strike = spec.get("strike")
    has_strike = raw_strike not in (None, "")
    if has_strike == (spec.get("delta") not in (None, "")):
        raise ApiError(f"leg {n}: give either a strike or a delta", code="invalid_leg")
    if not has_strike:
        delta = abs(_number(spec["delta"], f"leg {n} delta", -0.99, 0.99, "invalid_delta"))
        if delta < 0.01:
            raise ApiError(f"leg {n} delta must be between 0.01 and 0.99 in absolute value", code="invalid_delta")
        parsed["signed"] = delta if kind == "call" else -delta
    elif str(raw_strike).strip().lower() == "atm":
        parsed["atm"] = True
    else:
        parsed["strike"] = raw_strike
    return parsed


def _leg(spec: dict, n: int, market: Market, smile: Smile | None, listed: ListedMarket | None, style: str, curves):
    """Build one validated leg spec; returns ``(Leg, extras)`` (extras: expiry, IV source, quote)."""
    kind, side, qty, dte = spec["kind"], spec["side"], spec["qty"], spec["dte"]
    atm, signed, strike = spec["atm"], spec["signed"], None
    if spec["strike"] is not None:
        # Same window strike_for_delta searches: 20%-300% of spot.
        strike = _number(spec["strike"], f"leg {n} strike", 0.2 * market.spot, 3.0 * market.spot, "invalid_strike")

    if listed is None:
        tick = strike_tick(market.spot)
        if atm:
            strike = round(round(market.spot / tick) * tick, 10)
        elif signed is not None:
            strike = strike_for_delta(kind, signed, dte, market, smile, tick)
        leg = make_leg(kind, side, strike, dte, market, smile=smile, qty=qty, style=style, steps=WEB_TREE_STEPS)
        return leg, _hypothetical_extras()

    expiry = nearest_expiry(listed, dte)
    quotes = expiry.quotes(kind)
    if not quotes:
        raise ApiError(
            f"leg {n}: {listed.ticker} lists no {kind}s on {expiry.expiry}", code="strike_unavailable", status=502
        )
    if expiry.expiry not in curves:
        try:
            curves[expiry.expiry] = iv_curve(expiry, market)
        except ValueError:
            raise ApiError(
                f"no usable implied volatility for {listed.ticker} on {expiry.expiry}",
                code="iv_unavailable",
                status=502,
            ) from None
    curve: IvCurve = curves[expiry.expiry]
    if atm:
        strike = market.spot
    elif signed is not None:
        strike = strike_for_delta(kind, signed, expiry.dte, market, curve)
    quote = nearest_quote(quotes, strike)
    iv, source = leg_iv(kind, quote, expiry, market, curve, style, WEB_TREE_STEPS)
    leg = make_leg(kind, side, quote.strike, expiry.dte, market, iv=iv, qty=qty, style=style, steps=WEB_TREE_STEPS)
    return leg, {"expiry": expiry.expiry, "iv_source": source, "bid": quote.bid, "ask": quote.ask, "mid": quote.mid}


def _rounded(values, digits: int) -> list:
    return np.round(np.asarray(values, dtype=float), digits).tolist()


def _nullable(values, digits: int) -> list:
    """Like ``_rounded`` but NaN becomes ``None`` (JSON has no NaN)."""
    arr = np.round(np.asarray(values, dtype=float), digits)
    return np.where(np.isfinite(arr), arr, None).tolist()


def _quote_value(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def run_optsim(payload: dict | None) -> dict:
    """Validate ``payload`` and revalue the position on spot × date (× IV at entry).

    Percent inputs: ``rate``, ``div_yield``, ``atm_iv``, ``spot_range``;
    ``iv_shift`` is in vol points. ``market`` picks the hypothetical inputs or the
    listed market of ``ticker``. Returns ``{"status": "ok", ...}`` with the
    market used, the resolved legs, P&L and Greeks by date, P&L at entry under IV
    shifts, a per-date profile (value, Greeks, Reg-T and PM) at the entry spot
    and each leg's break-even IV on the chart dates.
    """
    payload = payload or {}
    source = _choice(payload.get("market") or "hypothetical", "market", MARKETS, "invalid_market")
    ticker_mode = source == "ticker"
    spot = None
    if not ticker_mode:
        if payload.get("spot") in (None, ""):
            raise ApiError("spot is required", code="spot_required")
        spot = _field(payload, "spot", None, 0.01, 1e7, "invalid_spot")
    rate = _field(payload, "rate", 4.5, -5, 50, "invalid_rate") / 100
    div_yield = _field(payload, "div_yield", 0.0, 0, 20, "invalid_div_yield") / 100
    smile = None
    if not ticker_mode:
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
    parsed = [_leg_spec(spec, i + 1) for i, spec in enumerate(specs)]
    # The chain is fetched last, so a malformed request never costs a provider call
    # (only the strike window waits for the chain's spot).
    listed = _listed(payload.get("ticker")) if ticker_mode else None
    if listed is not None:
        spot = listed.spot
    market = Market(spot=spot, rate=rate, div_yield=div_yield)
    curves: dict[str, IvCurve] = {}
    resolved = [_leg(spec, i + 1, market, smile, listed, style, curves) for i, spec in enumerate(parsed)]
    legs = [leg for leg, _ in resolved]
    position = Position(legs, style=style, multiplier=multiplier, product=product)

    last = max(leg.dte for leg in legs)
    days = default_days(position, step=max(7, math.ceil(last / MAX_SLICES)))
    grid_args = {"spot_range": spot_range, "n_spots": N_SPOTS, "steps": WEB_TREE_STEPS}
    main = scenario_grid(position, market, days=days, iv_shifts=(0.0,), **grid_args)
    shifts = (-iv_shift, 0.0, iv_shift) if iv_shift > 0 else (0.0,)
    entry = scenario_grid(position, market, days=[0.0], iv_shifts=shifts, **grid_args) if iv_shift > 0 else main
    picks = chart_days(main.days)
    be_days = [float(main.days[i]) for i in picks if main.days[i] > 0]
    be = breakeven_iv(position, market, main.spots, be_days, steps=WEB_TREE_STEPS)

    leg_rows = []
    for leg, extras in resolved:
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
                "expiry": extras["expiry"],
                "iv_source": extras["iv_source"],
                "bid": _quote_value(extras["bid"]),
                "ask": _quote_value(extras["ask"]),
                "mid": _quote_value(extras["mid"]),
            }
        )

    market_row: dict[str, Any] = {"source": source}
    if listed is not None:
        first = resolved[0][1]["expiry"]
        market_row.update(
            ticker=listed.ticker,
            spot=round(spot, 4),
            as_of=listed.as_of,
            atm_expiry=first,
            atm_iv=round(float(curves[first].iv(spot)), 6),
        )

    profile = [{k: (v if isinstance(v, str) else round(v, 4)) for k, v in row.items()} for row in time_profile(main)]
    return {
        "status": "ok",
        "market": market_row,
        "style": style,
        "product": product,
        "multiplier": multiplier,
        "spot": spot,
        "tree_steps": WEB_TREE_STEPS if style == "american" else None,
        "legs": leg_rows,
        "entry_value": round(main.entry_value, 2),
        "spots": _rounded(main.spots, 4),
        "days": _rounded(main.days, 0),
        "chart_days": picks,
        "pnl_by_day": _rounded(main.pnl[0], 2),
        "greeks_by_day": {k: _rounded(getattr(main, k)[0], 4) for k in GREEKS},
        "iv_shifts": _rounded(entry.iv_shifts, 4),
        "pnl_by_iv_at_entry": _rounded(entry.pnl[:, 0, :], 2),
        "breakevens": [round(b, 2) for b in breakevens(main.spots, main.pnl[0, -1])],
        "profile": profile,
        "breakeven_iv": {
            "days": _rounded(be_days, 0),
            "legs": [
                {
                    "iv": _nullable(b["iv"], 4),
                    "at_spot": _nullable(b["iv"][:, main.base_index], 4),
                    "expiry_breakeven": round(b["expiry_breakeven"], 2),
                }
                for b in be
            ],
        },
    }

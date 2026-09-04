"""Options expiry simulation service.

Domain:    Options Analysis — Expiry Simulation (service layer)
Context:
  - Validates the JSON payload of ``POST /api/simulate_expiry``, resolves the
    spot price (explicit override wins, otherwise Yahoo Finance), and hands
    the pure maths to :mod:`core.options.simulation`.
  - Bounds the strike × (maturity × vol) grid so a single request cannot ask
    the server to serialise an unbounded number of payoff curves.
Contracts:
  - run_simulation(payload) -> dict
Dependencies UPWARD:
  - utils.api_errors, utils.ticker_utils, data_pipeline.yf_client
  - core.options.simulation
Dependencies DOWNWARD:
  - routes.options, tests
"""

from __future__ import annotations

import datetime as dt
import logging
import math
import re
from typing import Any

from core.options.simulation import (
    generate_expiry_calendar,
    parse_expiries,
    simulate_expiry,
)
from utils.api_errors import ApiError

logger = logging.getLogger(__name__)

MAX_STRIKES = 15
MAX_EXPIRIES = 6
MAX_IVS = 5
MAX_CELLS = 300
MAX_POINTS = 201

DEFAULT_EXPIRIES = "7, 30, 60, 90"
DEFAULT_IVS = "20, 30, 45"
DEFAULT_RANGE_PCT = 0.35
DEFAULT_POINTS = 101

# Moneyness ladder used when the caller does not name explicit strikes.
_DEFAULT_MONEYNESS = (-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15)

_SPLIT = re.compile(r"[,\s;]+")


def _tokens(value: Any) -> list[str]:
    """Split a comma/space separated string or list into non-empty tokens."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        raw = [str(v) for v in value]
    else:
        raw = [str(value)]
    out: list[str] = []
    for item in raw:
        out.extend(t for t in _SPLIT.split(item) if t)
    return out


def _numbers(value: Any) -> list[float]:
    """Parse tokens into floats, skipping anything non-numeric."""
    nums: list[float] = []
    for tok in _tokens(value):
        try:
            nums.append(float(tok))
        except ValueError:
            continue
    return nums


# Candidate strike ticks. The auto-ladder picks the coarsest tick that still
# keeps neighbouring rungs (5% of spot apart) distinct — a $3 stock needs
# 5-cent rungs, a $680 index needs 10-point rungs.
_TICKS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0)


def _strike_step(spot: float) -> float:
    """Coarsest standard tick that still separates 5% moneyness rungs."""
    budget = spot * 0.02
    step = _TICKS[0]
    for tick in _TICKS:
        if tick <= budget:
            step = tick
        else:
            break
    return step


def default_strikes(spot: float) -> list[float]:
    """Build a ±15% strike ladder around ``spot`` snapped to a sane tick."""
    step = _strike_step(spot)
    strikes: list[float] = []
    for offset in _DEFAULT_MONEYNESS:
        k = round(round(spot * (1 + offset) / step) * step, 2)
        if k > 0 and k not in strikes:
            strikes.append(k)
    return strikes


def resolve_spot(ticker: str, override: Any) -> float:
    """Return the spot price: explicit ``override`` first, else live quote."""
    if override not in (None, ""):
        try:
            spot = float(override)
        except (TypeError, ValueError):
            raise ApiError("spot must be a number", code="invalid_spot")
        if not math.isfinite(spot) or spot <= 0:
            raise ApiError("spot must be a positive number", code="invalid_spot")
        return spot

    if not ticker:
        raise ApiError("ticker (or an explicit spot) is required", code="ticker_required")

    from data_pipeline.yf_client import fetch_spot

    spot = fetch_spot(ticker)
    if spot is None or not math.isfinite(spot) or spot <= 0:
        raise ApiError(
            f"could not resolve a spot price for {ticker}",
            code="spot_unavailable",
            status=502,
        )
    return float(spot)


def run_simulation(payload: dict | None) -> dict:
    """Validate ``payload`` and run the expiry-payoff simulation.

    See :func:`core.options.simulation.simulate_expiry` for the maths; this
    layer only normalises inputs and returns ``{"status": "ok", ...}``.
    """
    payload = payload or {}

    raw_ticker = str(payload.get("ticker") or "").strip().upper()
    ticker = raw_ticker
    if ticker:
        try:
            from utils.ticker_utils import normalize_ticker

            ticker, _futu = normalize_ticker(ticker)
        except ValueError:
            pass

    spot = resolve_spot(ticker, payload.get("spot"))

    option_type = str(payload.get("option_type") or "call").strip().lower()
    if option_type not in ("call", "put"):
        raise ApiError("option_type must be 'call' or 'put'", code="invalid_option_type")

    side = str(payload.get("side") or "long").strip().lower()
    if side not in ("long", "short"):
        raise ApiError("side must be 'long' or 'short'", code="invalid_side")

    strikes = _numbers(payload.get("strikes")) or default_strikes(spot)
    strikes = sorted({round(k, 4) for k in strikes if k > 0})
    if not strikes:
        raise ApiError("no positive strikes to simulate", code="invalid_strikes")
    if len(strikes) > MAX_STRIKES:
        raise ApiError(
            f"too many strikes (max {MAX_STRIKES})",
            code="too_many_strikes",
            details={"count": len(strikes)},
        )

    expiries = parse_expiries(_tokens(payload.get("expiries")) or _tokens(DEFAULT_EXPIRIES))
    if not expiries:
        raise ApiError(
            "no usable expiries — provide DTE days (e.g. 30) or dates (e.g. 2026-12-18)",
            code="invalid_expiries",
        )
    if len(expiries) > MAX_EXPIRIES:
        raise ApiError(
            f"too many expiries (max {MAX_EXPIRIES})",
            code="too_many_expiries",
            details={"count": len(expiries)},
        )

    iv_pcts = _numbers(payload.get("ivs")) or _numbers(DEFAULT_IVS)
    ivs = sorted({round(v / 100.0, 6) for v in iv_pcts if 0.1 <= v <= 500})
    if not ivs:
        raise ApiError(
            "implied vols must be percentages between 0.1 and 500",
            code="invalid_ivs",
        )
    if len(ivs) > MAX_IVS:
        raise ApiError(
            f"too many implied vols (max {MAX_IVS})",
            code="too_many_ivs",
            details={"count": len(ivs)},
        )

    if len(strikes) * len(expiries) * len(ivs) > MAX_CELLS:
        raise ApiError(
            f"grid too large — {len(strikes)} strikes × {len(expiries)} expiries "
            f"× {len(ivs)} vols exceeds {MAX_CELLS} scenarios",
            code="grid_too_large",
        )

    try:
        r = float(payload.get("r", 5.0))
    except (TypeError, ValueError):
        raise ApiError("r must be a number (percent)", code="invalid_rate")
    if not math.isfinite(r) or not -5 <= r <= 50:
        raise ApiError("r must be a percent between -5 and 50", code="invalid_rate")

    try:
        qty = int(float(payload.get("qty", 1)))
    except (TypeError, ValueError):
        raise ApiError("qty must be an integer", code="invalid_qty")
    if qty < 1 or qty > 1000:
        raise ApiError("qty must be between 1 and 1000", code="invalid_qty")

    try:
        multiplier = float(payload.get("multiplier", 100))
    except (TypeError, ValueError):
        raise ApiError("multiplier must be a number", code="invalid_multiplier")
    if not math.isfinite(multiplier) or multiplier <= 0:
        raise ApiError("multiplier must be positive", code="invalid_multiplier")

    try:
        n_points = int(float(payload.get("n_points", DEFAULT_POINTS)))
    except (TypeError, ValueError):
        raise ApiError("n_points must be an integer", code="invalid_n_points")
    n_points = max(21, min(n_points, MAX_POINTS))

    try:
        range_pct = float(payload.get("range_pct", DEFAULT_RANGE_PCT))
    except (TypeError, ValueError):
        raise ApiError("range_pct must be a number", code="invalid_range_pct")
    range_pct = min(max(range_pct, 0.05), 2.0)

    result = simulate_expiry(
        spot=spot,
        strikes=strikes,
        expiries=expiries,
        ivs=ivs,
        option_type=option_type,
        side=side,
        r=r / 100.0,
        qty=qty,
        multiplier=multiplier,
        n_points=n_points,
        range_pct=range_pct,
    )

    return {
        "status": "ok",
        "ticker": ticker,
        "strike_source": "manual" if _numbers(payload.get("strikes")) else "auto",
        **result,
    }


def generate_expiry_calendar_service(
    ref,
    n_standard: int = 12,
    n_daily: int = 10,
    holidays=None,
) -> dict:
    """Validate inputs and build the expiry calendar for the Premium Matrix.

    Delegates the pure maths to
    :func:`core.options.simulation.generate_expiry_calendar`.
    """
    if isinstance(ref, str):
        try:
            ref = dt.datetime.strptime(ref, "%Y-%m-%d").date()
        except ValueError:
            raise ApiError("ref must be 'YYYY-MM-DD'", code="invalid_ref")
    elif not isinstance(ref, dt.date):
        raise ApiError("ref must be a date or 'YYYY-MM-DD'", code="invalid_ref")

    try:
        n_standard = int(n_standard)
        n_daily = int(n_daily)
    except (TypeError, ValueError):
        raise ApiError("standard and daily counts must be integers", code="invalid_counts")

    if not (0 <= n_standard <= 60 and 0 <= n_daily <= 60):
        raise ApiError("standard and daily counts must be between 0 and 60", code="counts_out_of_range")

    if holidays is not None:
        try:
            holidays = {dt.date.fromisoformat(h) if isinstance(h, str) else h for h in holidays}
        except (ValueError, TypeError):
            raise ApiError("holidays must be ISO date strings or date objects", code="invalid_holidays")

    try:
        expirations = generate_expiry_calendar(ref, n_standard, n_daily, holidays)
    except (ValueError, TypeError) as e:
        raise ApiError(str(e), code="invalid_calendar")

    return {
        "status": "ok",
        "reference_date": ref.isoformat(),
        "expirations": expirations,
    }

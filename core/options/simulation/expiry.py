"""Expiry-payoff simulation across strike / maturity / implied-vol dimensions.

Domain:    Options Analysis — Expiry Simulation
Context:
  - Pure, deterministic computation — no network access. The caller supplies
    spot; this module only prices entry and projects expiration value.
  - Entry premium comes from Black-Scholes (European exercise, no dividends).
  - Terminal P&L is ``sign × qty × multiplier × (intrinsic(S_T) − premium)``.
  - Feeds the dashboard "Simulation" tab: given a set of implied vols and a
    set of maturities, show what every strike pays at expiration.
Contracts:
  - parse_expiries(values, today=None) -> list[dict]
  - simulate_expiry(...) -> dict
Dependencies UPWARD:
  - numpy, scipy.stats
  - core.options.greeks.black_scholes
Dependencies DOWNWARD:
  - services.options_simulation_service, routes.options, tests
"""

from __future__ import annotations

import datetime as dt
import math
import re

import numpy as np
from scipy.stats import norm

from core.options.greeks.black_scholes import greeks_vectorized

# CONSTRAINT: Black-Scholes degenerates at T→0 (division by sqrt(T)); one
# calendar day is the smallest maturity the simulator is willing to price.
_MIN_DTE = 1

# CONSTRAINT: chain data can carry IV=999; clamp so exponent terms stay finite.
_MAX_DTE = 3650
_MIN_IV = 0.001
_MAX_IV = 5.0

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _prob_above(spot: float, level: float, T: float, r: float, sigma: float) -> float:
    """Risk-neutral ``P(S_T > level)`` under GBM with volatility ``sigma``."""
    if level <= 0:
        return 1.0
    d2 = (math.log(spot / level) + (r - 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return float(norm.cdf(d2))


def parse_expiries(values, today: dt.date | None = None) -> list[dict]:
    """Normalise expiry tokens into ``[{"dte", "date", "label"}]``.

    A token is either a DTE in calendar days (``"30"``) or an ISO date
    (``"2026-12-18"``). Tokens that cannot be parsed, or that resolve to a
    date in the past, are dropped. Result is sorted by date and de-duplicated.
    """
    today = today or dt.date.today()
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()

    for raw in values or []:
        token = str(raw).strip()
        if not token:
            continue

        if _ISO_DATE.match(token):
            try:
                date = dt.datetime.strptime(token, "%Y-%m-%d").date()
            except ValueError:
                continue
        else:
            try:
                days = int(float(token))
            except (TypeError, ValueError):
                continue
            if days < _MIN_DTE or days > _MAX_DTE:
                continue
            date = today + dt.timedelta(days=days)

        dte = (date - today).days
        if dte < _MIN_DTE or dte > _MAX_DTE:
            continue

        key = (dte, date.isoformat())
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "dte": dte,
                "date": date.isoformat(),
                "label": f"{date.isoformat()} ({dte}D)",
            }
        )

    out.sort(key=lambda e: (e["date"], e["dte"]))
    return out


def _price_grid(spot: float, strikes: np.ndarray, range_pct: float, n_points: int) -> np.ndarray:
    """Terminal-price axis: centred on spot but always covering every strike."""
    span = max(float(range_pct), 0.05)
    lo = min(spot * (1 - span), float(strikes.min()) * 0.97)
    hi = max(spot * (1 + span), float(strikes.max()) * 1.03)
    lo = max(lo, 0.01)
    if hi <= lo:
        hi = lo * 1.5
    return np.linspace(lo, hi, max(int(n_points), 21))


def simulate_expiry(
    spot: float,
    strikes: list[float],
    expiries: list[dict],
    ivs: list[float],
    option_type: str = "call",
    side: str = "long",
    r: float = 0.05,
    qty: int = 1,
    multiplier: float = 100.0,
    n_points: int = 101,
    range_pct: float = 0.35,
) -> dict:
    """Simulate expiration P&L for every strike × maturity × implied vol.

    Parameters
    ----------
    spot
        Current underlying price (entry reference).
    strikes
        Strike prices to simulate.
    expiries
        Output of :func:`parse_expiries` — ``[{"dte", "date", "label"}]``.
    ivs
        Implied volatilities as **decimals** (``0.30`` = 30%).
    option_type
        ``"call"`` or ``"put"``.
    side
        ``"long"`` (buy the option) or ``"short"`` (sell it).
    r
        Annual risk-free rate as a decimal.
    qty
        Number of contracts.
    multiplier
        Contract multiplier (100 for US equity options).
    n_points
        Resolution of the terminal-price axis.
    range_pct
        Half-width of the terminal-price axis around spot.

    Returns
    -------
    dict
        ``{"spot", "option_type", "side", "r_pct", "qty", "multiplier",
        "prices", "strikes", "combos", "results"}`` where ``results[i]`` holds
        one entry per strike, each with a ``cells`` list parallel to
        ``combos``.
    """
    S = float(spot)
    if not math.isfinite(S) or S <= 0:
        raise ValueError("spot must be a positive finite number")
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type!r}")
    if side not in ("long", "short"):
        raise ValueError(f"side must be 'long' or 'short', got {side!r}")

    KS = np.asarray(sorted(float(k) for k in strikes if float(k) > 0), dtype=float)
    if KS.size == 0:
        raise ValueError("at least one positive strike is required")
    if not expiries:
        raise ValueError("at least one expiry is required")

    clean_ivs = [float(v) for v in ivs if _MIN_IV <= float(v) <= _MAX_IV]
    if not clean_ivs:
        raise ValueError(f"implied vols must be decimals between {_MIN_IV} and {_MAX_IV}")

    r = float(r)
    qty = float(qty)
    multiplier = float(multiplier)
    sign = 1.0 if side == "long" else -1.0
    is_call = option_type == "call"
    unit = qty * multiplier

    prices = _price_grid(S, KS, range_pct, n_points)

    # Column metadata — one entry per (maturity × vol) scenario.
    combos: list[dict] = []
    for exp in expiries:
        for iv in clean_ivs:
            combos.append(
                {
                    "dte": int(exp["dte"]),
                    "expiry": exp["date"],
                    "iv_pct": round(iv * 100, 4),
                    "label": f"{int(exp['dte'])}D · {iv * 100:g}% IV",
                }
            )

    # Premiums and entry deltas, one row per combo, one column per strike.
    premium_rows: list[np.ndarray] = []
    delta_rows: list[np.ndarray] = []
    for combo in combos:
        T = combo["dte"] / 365.0
        g = greeks_vectorized(
            np.full(KS.shape, S),
            KS,
            np.full(KS.shape, T),
            r,
            np.full(KS.shape, combo["iv_pct"] / 100.0),
            option_type,
        )
        premium_rows.append(np.asarray(g["bs_price"], dtype=float))
        delta_rows.append(np.asarray(g["delta"], dtype=float))

    intrinsic_at = (
        (lambda p, k: np.maximum(p - k, 0.0)) if is_call else (lambda p, k: np.maximum(k - p, 0.0))
    )

    results: list[dict] = []
    for i, K in enumerate(KS.tolist()):
        cells: list[dict] = []
        for j, combo in enumerate(combos):
            premium = float(premium_rows[j][i])
            if not math.isfinite(premium):
                premium = 0.0
            delta = float(delta_rows[j][i])
            if not math.isfinite(delta):
                delta = 0.0

            T = combo["dte"] / 365.0
            iv = combo["iv_pct"] / 100.0

            pnl = sign * unit * (intrinsic_at(prices, K) - premium)
            intrinsic_spot = max(S - K, 0.0) if is_call else max(K - S, 0.0)

            # Breakeven solves intrinsic(S_T) == premium — independent of side.
            breakeven = K + premium if is_call else K - premium

            pop_long = (
                _prob_above(S, breakeven, T, r, iv)
                if is_call
                else 1.0 - _prob_above(S, breakeven, T, r, iv)
            )
            pop = pop_long if side == "long" else 1.0 - pop_long

            if is_call:
                if side == "long":
                    unbounded_profit, unbounded_loss = True, False
                    max_profit, max_loss = math.inf, -premium * unit
                else:
                    unbounded_profit, unbounded_loss = False, True
                    max_profit, max_loss = premium * unit, -math.inf
            else:
                unbounded_profit, unbounded_loss = False, False
                if side == "long":
                    max_profit, max_loss = (K - premium) * unit, -premium * unit
                else:
                    max_profit, max_loss = premium * unit, -(K - premium) * unit

            cells.append(
                {
                    "dte": combo["dte"],
                    "expiry": combo["expiry"],
                    "iv_pct": combo["iv_pct"],
                    "label": combo["label"],
                    "premium": round(premium, 4),
                    "delta": round(delta, 4),
                    "breakeven": round(breakeven, 4),
                    "pop": round(float(pop), 4),
                    "max_profit": None if unbounded_profit else round(float(max_profit), 2),
                    "max_loss": None if unbounded_loss else round(float(max_loss), 2),
                    "unbounded_profit": unbounded_profit,
                    "unbounded_loss": unbounded_loss,
                    "pnl_at_spot": round(sign * unit * (intrinsic_spot - premium), 2),
                    "pnl": [round(float(v), 2) for v in pnl.tolist()],
                }
            )
        results.append({"strike": round(float(K), 4), "cells": cells})

    return {
        "spot": round(S, 4),
        "option_type": option_type,
        "side": side,
        "r_pct": round(r * 100, 4),
        "qty": int(qty),
        "multiplier": int(multiplier),
        "prices": [round(float(p), 4) for p in prices.tolist()],
        "strikes": [round(float(k), 4) for k in KS.tolist()],
        "combos": combos,
        "results": results,
    }

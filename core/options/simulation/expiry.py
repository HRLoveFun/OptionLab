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
  - generate_expiry_calendar(ref, n_standard=12, n_daily=10, holidays=None) -> list[dict]
  - simulate_expiry(...) -> dict
Dependencies UPWARD:
  - numpy, scipy.stats
  - core.options.greeks.black_scholes
Dependencies DOWNWARD:
  - services.options.simulation, routes.options, tests
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


# ---------------------------------------------------------------------------
# Expiration-calendar generation (Premium Matrix columns)
# ---------------------------------------------------------------------------
# US single-stock / ETF options carry a *daily* (0DTE-style, every business
# day) series for the short end, plus a *weekly* listed series on every
# Friday for the longer maturities. When a Friday is an exchange holiday the
# expiration rolls back to the previous business day (usually Thursday).
#
# The project otherwise ignores exchange holidays (see data_pipeline/cleaning
# for the "B" frequency), but the listed-expiration rules *require* them, so
# we ship a self-contained NYSE approximation here rather than depending on an
# external calendar package.


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> dt.date:
    """The ``n``-th ``weekday`` (Mon=0 … Sun=6) of ``year``/``month``.

    ``n=5`` is interpreted as "the last such weekday" (e.g. last Monday of May
    for Memorial Day).
    """
    if not 0 <= weekday <= 6:
        raise ValueError("weekday must be 0 (Mon) .. 6 (Sun)")
    if n < 1:
        raise ValueError("n must be >= 1")
    first = dt.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    target = first + dt.timedelta(days=offset) + dt.timedelta(days=7 * (n - 1))
    # If n=5 overshot into next month, step back one week to land on the last.
    while target.month != month:
        target -= dt.timedelta(days=7)
    return target


def _easter(year: int) -> dt.date:
    """Gregorian Easter Sunday (Anonymous / Meeus-Jones-Butcher algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    lp = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lp) // 451
    month = (h + lp - 7 * m + 114) // 31
    day = ((h + lp - 7 * m + 114) % 31) + 1
    return dt.date(year, month, day)


def _nyse_holiday_set(years) -> set[dt.date]:
    """NYSE holiday approximation (fixed + moving rules).

    Fixed-date holidays that fall on Saturday close on the prior Friday; those
    on Sunday close on the following Monday — the standard NYSE convention.
    """
    holidays: set[dt.date] = set()
    for year in years:
        for fixed in (dt.date(year, 1, 1), dt.date(year, 6, 19),
                      dt.date(year, 7, 4), dt.date(year, 12, 25)):
            wd = fixed.weekday()
            if wd == 5:  # Saturday -> prior Friday
                holidays.add(fixed - dt.timedelta(days=1))
            elif wd == 6:  # Sunday -> following Monday
                holidays.add(fixed + dt.timedelta(days=1))
            else:
                holidays.add(fixed)
        # Moving holidays.
        holidays.add(_nth_weekday(year, 1, 0, 3))    # MLK — 3rd Mon Jan
        holidays.add(_nth_weekday(year, 2, 0, 3))    # Presidents — 3rd Mon Feb
        holidays.add(_nth_weekday(year, 5, 0, 5))    # Memorial — last Mon May
        holidays.add(_nth_weekday(year, 9, 0, 1))    # Labor — 1st Mon Sep
        holidays.add(_nth_weekday(year, 11, 3, 4))  # Thanksgiving — 4th Thu Nov
        holidays.add(_easter(year) - dt.timedelta(days=2))  # Good Friday
    return holidays


def _adjust_to_business_day(d: dt.date, holidays: set[dt.date], forward: bool) -> dt.date:
    """Nudge ``d`` to the nearest business day, skipping weekends + holidays.

    ``forward=False`` rolls backward (used for the 3rd-Friday rule); ``True``
    rolls forward (used when walking the daily series).
    """
    step = dt.timedelta(days=1 if forward else -1)
    guard = 0
    while (d.weekday() in (5, 6) or d in holidays) and guard < 10:
        guard += 1
        d += step
    return d


def _make_entry(d: dt.date, ref: dt.date, kind: str, cycle):
    # +1: a listed expiration is a *whole* day out, so the same-day column reads
    # 1D rather than 0D. Dates themselves are untouched (Fridays stay Fridays).
    dte = (d - ref).days + 1
    return {
        "date": d.isoformat(),
        "dte": dte,
        "label": f"{d.isoformat()} ({dte}D)",
        "kind": kind,         # "standard" | "daily"
        "cycle": cycle,       # "weekly" | None
    }


def _next_friday(d: dt.date) -> dt.date:
    """First Friday (weekday 4) strictly after ``d`` (no holiday handling)."""
    friday = d + dt.timedelta(days=1)
    while friday.weekday() != 4:
        friday += dt.timedelta(days=1)
    return friday


def generate_expiry_calendar(
    reference_date,
    n_standard: int = 12,
    n_daily: int = 10,
    holidays=None,
) -> list[dict]:
    """Build upcoming option expirations for a Premium Matrix.

    Returns the next ``n_daily`` *daily* (0DTE-style, every business day)
    expirations from ``reference_date`` (inclusive when it is a business day),
    plus the next ``n_standard`` *weekly listed* expirations — every Friday
    strictly after the last daily day, each tagged ``cycle="weekly"``.

    Each entry is ``{"date", "dte", "label", "kind", "cycle"}`` and is sorted
    by date ascending with duplicate dates de-duplicated (a ``standard`` entry
    wins over a ``daily`` one on collision). ``dte`` is calendar days vs
    ``reference_date`` **plus one** (``(date - ref).days + 1``), so a same-day
    expiration reads ``1D`` rather than ``0D``.

    ``reference_date`` may be a ``date`` or an ISO ``"YYYY-MM-DD"`` string.
    ``holidays`` is an optional ``set[date]``; when omitted (or empty) no
    holiday adjustment is applied — only weekends are skipped. Pass NYSE
    holiday dates to enable the Friday roll-back behaviour.

    Pure / deterministic — no network, no external state.
    """
    if isinstance(reference_date, str):
        try:
            ref = dt.datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"reference_date must be a date or 'YYYY-MM-DD', got {reference_date!r}")
    elif isinstance(reference_date, dt.date):
        ref = reference_date
    else:
        raise TypeError("reference_date must be a date or ISO string")

    if n_standard < 0 or n_daily < 0:
        raise ValueError("n_standard and n_daily must be >= 0")

    # Default: no holiday adjustment — only weekends are skipped. Pass an
    # explicit set of dates to enable NYSE-aware rolling of the third-Friday
    # expirations.
    holidays = set(holidays) if holidays else set()

    # --- daily (0DTE-style) expirations: next n_daily business days ----------
    # Built FIRST so the weekly standard series can start strictly after the
    # last daily day — the short end stays a clean run of consecutive business
    # days with no overlap against the weekly Fridays.
    daily: list[dict] = []
    d = _adjust_to_business_day(ref, holidays, forward=True)
    guard = 0
    while len(daily) < n_daily and guard < 400:
        guard += 1
        daily.append(_make_entry(d, ref, "daily", None))
        d = _adjust_to_business_day(d + dt.timedelta(days=1), holidays, forward=True)

    # --- standard listed expirations: every Friday AFTER the last daily day --
    # Weekly expirations (cycle "weekly") only beyond the daily range, so the
    # two series never share a column. (The legacy monthly third-Friday ladder
    # has been retired in favour of a continuous weekly ladder.)
    standard: list[dict] = []
    last_daily = dt.date.fromisoformat(daily[-1]["date"]) if daily else ref
    cur = last_daily
    guard = 0
    while len(standard) < n_standard and guard < 600:
        guard += 1
        cur = _next_friday(cur)
        eff = _adjust_to_business_day(cur, holidays, forward=False)
        # A holiday Friday that rolls back into the daily range is dropped
        # (the daily entry wins the de-dupe anyway), and the ladder continues
        # with the next Friday.
        if eff > last_daily:
            standard.append(_make_entry(eff, ref, "standard", "weekly"))

    # --- merge + dedupe (standard wins on date collision) --------------------
    by_date: dict[str, dict] = {}
    for entry in standard + daily:
        by_date.setdefault(entry["date"], entry)
    return sorted(by_date.values(), key=lambda e: e["date"])

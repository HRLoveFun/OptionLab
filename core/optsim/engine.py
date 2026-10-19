"""Scenario engine: position value and risk over spot × time × IV.

Domain:    Option Simulation — Scenario Grid
Context:
  - Deterministic what-if analysis: spot is moved to each grid level on each
    future day, IVs are sticky-strike (every leg keeps its IV, optionally shifted
    in parallel), rates and dividends are constant.
  - Legs past their expiry are worth intrinsic value at the grid spot and drop
    out of the margin calculation.
  - Position-level units: value and P&L in dollars, delta in shares, gamma in
    shares per $1, theta in dollars per calendar day, vega in dollars per vol point.
Contracts:
  - default_days(position, step=7) -> np.ndarray
  - scenario_grid(position, market, *, spot_range, n_spots, days, iv_shifts, steps) -> Grid
  - time_profile(grid, iv_shift=0.0) -> list[dict]
  - breakevens(spots, pnl) -> list[float]
Dependencies UPWARD:
  - numpy, core.optsim.pricing, core.optsim.margin, core.optsim.models
Dependencies DOWNWARD:
  - core.optsim.charts, scripts/optsim.py, tests
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.optsim.margin import pm_bpr, pm_offsets, regt_bpr
from core.optsim.models import Market, Position
from core.optsim.pricing import DEFAULT_STEPS, option_greeks

GREEKS = ("delta", "gamma", "theta", "vega")

# DOMAIN: IV never drops below 1 vol point under a negative shift.
_IV_FLOOR = 0.01


@dataclass
class Grid:
    spots: np.ndarray  # (n_s,)
    days: np.ndarray  # (n_d,)
    iv_shifts: np.ndarray  # (n_v,)
    value: np.ndarray  # (n_v, n_d, n_s) dollars
    pnl: np.ndarray
    delta: np.ndarray
    gamma: np.ndarray
    theta: np.ndarray
    vega: np.ndarray
    regt: np.ndarray  # (n_v, n_d, n_s) dollars
    regt_method: list[str]  # per day
    pm: np.ndarray  # (n_v, n_d) dollars, at the entry spot
    entry_value: float
    base_index: int
    position: Position
    market: Market


def _qty(leg) -> int:
    return (1 if leg.side == "long" else -1) * leg.qty


def default_days(position: Position, step: int = 7) -> np.ndarray:
    """Weekly slices from entry to the last expiry, plus every expiry day."""
    expiries = sorted({int(leg.dte) for leg in position.legs})
    days = set(range(0, expiries[-1], step)) | set(expiries)
    return np.array(sorted(days), dtype=float)


def _leg_values(position, market, spots, days, iv_shift, steps):
    """Per-leg Greeks dicts on a (n_d, n_s) grid; spots may differ per day (2-D)."""
    S = np.broadcast_to(np.asarray(spots, dtype=float), (len(days), np.shape(spots)[-1]))
    out = []
    for leg in position.legs:
        T = (leg.dte - days[:, None]) / 365.0
        sigma = max(leg.iv + iv_shift, _IV_FLOOR)
        out.append(
            option_greeks(
                leg.option_type, S, leg.strike, T, market.rate, market.div_yield, sigma, position.style, steps
            )
        )
    return out


def scenario_grid(
    position: Position,
    market: Market,
    *,
    spot_range: float = 0.15,
    n_spots: int = 61,
    days=None,
    iv_shifts=(-0.05, 0.0, 0.05),
    steps: int = DEFAULT_STEPS,
) -> Grid:
    """Revalue the position on spot × day × IV-shift and attach Greeks and both margins."""
    if n_spots % 2 == 0:
        n_spots += 1  # keep the entry spot on the grid
    spots = market.spot * np.linspace(1.0 - spot_range, 1.0 + spot_range, n_spots)
    base_index = n_spots // 2
    # INVARIANT: entry day and the unshifted IVs are always on the grid (summaries read them).
    days = default_days(position) if days is None else np.union1d(np.asarray(days, dtype=float), [0.0])
    shifts = np.union1d(np.asarray(iv_shifts, dtype=float), [0.0])
    m = position.multiplier
    q = np.array([_qty(leg) for leg in position.legs], dtype=float)
    kinds = [leg.option_type for leg in position.legs]
    strikes = np.array([leg.strike for leg in position.legs])
    entry_value = float(m * sum(qi * leg.premium for qi, leg in zip(q, position.legs, strict=True)))

    shape = (len(shifts), len(days), n_spots)
    res = {k: np.zeros(shape) for k in ("value", *GREEKS)}
    regt = np.zeros(shape)
    methods = ["none"] * len(days)
    pm = np.zeros((len(shifts), len(days)))
    offsets = pm_offsets(position.product)
    pm_spots = market.spot * (1.0 + offsets)

    for v, shift in enumerate(shifts):
        legs = _leg_values(position, market, spots, days, shift, steps)
        prices = np.stack([g["price"] for g in legs])  # (n_legs, n_d, n_s)
        res["value"][v] = m * np.tensordot(q, prices, axes=1)
        for k in GREEKS:
            res[k][v] = m * np.tensordot(q, np.stack([g[k] for g in legs]), axes=1)
        # PM is revalued at the entry spot only: 11 points per day keeps American runs cheap.
        pm_prices = np.stack([g["price"] for g in _leg_values(position, market, pm_spots, days, shift, steps)])
        for d, day in enumerate(days):
            live = np.array([leg.dte > day for leg in position.legs])
            if not live.any():
                continue
            kinds_live = [k for k, keep in zip(kinds, live, strict=True) if keep]
            regt[v, d], methods[d] = regt_bpr(
                kinds_live, strikes[live], q[live], prices[live, d, :], spots, m, position.product
            )
            pm_live = m * np.tensordot(q[live], pm_prices[live, d], axes=1)  # (11,)
            pm[v, d] = pm_bpr(pm_live, float(np.abs(q[live]).sum()), m, all_long=bool((q[live] > 0).all()))

    return Grid(
        spots=spots,
        days=days,
        iv_shifts=shifts,
        value=res["value"],
        pnl=res["value"] - entry_value,
        delta=res["delta"],
        gamma=res["gamma"],
        theta=res["theta"],
        vega=res["vega"],
        regt=regt,
        regt_method=methods,
        pm=pm,
        entry_value=entry_value,
        base_index=base_index,
        position=position,
        market=market,
    )


def _shift_index(grid: Grid, iv_shift: float) -> int:
    hits = np.flatnonzero(np.isclose(grid.iv_shifts, iv_shift))
    if hits.size == 0:
        raise ValueError(f"iv_shift {iv_shift} not on the grid {grid.iv_shifts.tolist()}")
    return int(hits[0])


def time_profile(grid: Grid, iv_shift: float = 0.0) -> list[dict]:
    """One row per day at the entry spot: value, P&L, Greeks and both margins."""
    v, i = _shift_index(grid, iv_shift), grid.base_index
    rows = []
    for d, day in enumerate(grid.days):
        row = {"day": float(day)}
        for k in ("value", "pnl", *GREEKS):
            row[k] = float(getattr(grid, k)[v, d, i])
        row.update(regt=float(grid.regt[v, d, i]), regt_method=grid.regt_method[d], pm=float(grid.pm[v, d]))
        rows.append(row)
    return rows


def breakevens(spots: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Spot levels where a P&L curve crosses zero (linear interpolation between grid points)."""
    out = []
    s = np.sign(pnl)
    for j in np.flatnonzero(s[:-1] * s[1:] < 0):
        x0, x1, y0, y1 = spots[j], spots[j + 1], pnl[j], pnl[j + 1]
        out.append(float(x0 - y0 * (x1 - x0) / (y1 - y0)))
    return out

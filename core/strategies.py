"""
Multi-leg option strategies — pure computation, no I/O.

Provides factory helpers for the most common strategies and a unified
analytics function (``analyze_strategy``) returning:
- payoff curve at expiration (price grid → P&L)
- breakeven point(s)
- max profit / max loss
- net debit/credit
- net Greeks at current spot (delta/gamma/theta/vega)
- probability of profit (BS-implied, single underlying)

Strategies implemented:
    long_call / long_put / short_call / short_put         (single leg)
    bull_call_spread / bear_put_spread                    (vertical debit)
    bear_call_spread / bull_put_spread                    (vertical credit)
    long_straddle / long_strangle                         (vol long)
    short_straddle / short_strangle                       (vol short)
    iron_condor                                           (4 legs)
    long_butterfly                                        (3 strikes)
    calendar_spread                                       (2 expiries)

All strategies are represented as a list of ``Leg`` dicts so the engine
is fully data-driven — adding a new strategy = writing a factory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.stats import norm

from core.options_greeks import greeks_vectorized

logger = logging.getLogger(__name__)

OptionType = Literal["call", "put"]
LegSide = Literal["long", "short"]


# ---------------------------------------------------------------------------
# Leg + Strategy types
# ---------------------------------------------------------------------------
@dataclass
class Leg:
    """A single option leg.

    ``premium`` is the per-share entry price (positive number).
    ``qty`` is the number of contracts (always positive — direction is in ``side``).
    ``dte`` is days-to-expiry of *this* leg (calendars use different DTEs per leg).
    ``iv`` is the implied volatility used for Greeks (decimal, e.g. 0.25).
    """

    side: LegSide
    option_type: OptionType
    strike: float
    premium: float
    qty: int = 1
    dte: int = 30
    iv: float = 0.25

    @property
    def sign(self) -> int:
        return 1 if self.side == "long" else -1


# ---------------------------------------------------------------------------
# Strategy factories
# ---------------------------------------------------------------------------
def long_call(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("long", "call", strike, premium, **kw)]


def long_put(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("long", "put", strike, premium, **kw)]


def short_call(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("short", "call", strike, premium, **kw)]


def short_put(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("short", "put", strike, premium, **kw)]


def bull_call_spread(k_long: float, k_short: float, p_long: float, p_short: float, **kw) -> list[Leg]:
    """Long lower-strike call + short higher-strike call (debit)."""
    if k_long >= k_short:
        raise ValueError("bull_call_spread: k_long must be lower than k_short")
    return [Leg("long", "call", k_long, p_long, **kw), Leg("short", "call", k_short, p_short, **kw)]


def bear_put_spread(k_long: float, k_short: float, p_long: float, p_short: float, **kw) -> list[Leg]:
    """Long higher-strike put + short lower-strike put (debit)."""
    if k_long <= k_short:
        raise ValueError("bear_put_spread: k_long must be higher than k_short")
    return [Leg("long", "put", k_long, p_long, **kw), Leg("short", "put", k_short, p_short, **kw)]


def bear_call_spread(k_short: float, k_long: float, p_short: float, p_long: float, **kw) -> list[Leg]:
    """Short lower-strike call + long higher-strike call (credit)."""
    if k_short >= k_long:
        raise ValueError("bear_call_spread: k_short must be lower than k_long")
    return [Leg("short", "call", k_short, p_short, **kw), Leg("long", "call", k_long, p_long, **kw)]


def bull_put_spread(k_short: float, k_long: float, p_short: float, p_long: float, **kw) -> list[Leg]:
    """Short higher-strike put + long lower-strike put (credit)."""
    if k_short <= k_long:
        raise ValueError("bull_put_spread: k_short must be higher than k_long")
    return [Leg("short", "put", k_short, p_short, **kw), Leg("long", "put", k_long, p_long, **kw)]


def long_straddle(strike: float, p_call: float, p_put: float, **kw) -> list[Leg]:
    return [Leg("long", "call", strike, p_call, **kw), Leg("long", "put", strike, p_put, **kw)]


def long_strangle(k_call: float, k_put: float, p_call: float, p_put: float, **kw) -> list[Leg]:
    if k_call <= k_put:
        raise ValueError("long_strangle: k_call must be higher than k_put")
    return [Leg("long", "call", k_call, p_call, **kw), Leg("long", "put", k_put, p_put, **kw)]


def short_straddle(strike: float, p_call: float, p_put: float, **kw) -> list[Leg]:
    return [Leg("short", "call", strike, p_call, **kw), Leg("short", "put", strike, p_put, **kw)]


def short_strangle(k_call: float, k_put: float, p_call: float, p_put: float, **kw) -> list[Leg]:
    if k_call <= k_put:
        raise ValueError("short_strangle: k_call must be higher than k_put")
    return [Leg("short", "call", k_call, p_call, **kw), Leg("short", "put", k_put, p_put, **kw)]


def iron_condor(
    k_put_long: float,
    k_put_short: float,
    k_call_short: float,
    k_call_long: float,
    p_put_long: float,
    p_put_short: float,
    p_call_short: float,
    p_call_long: float,
    **kw,
) -> list[Leg]:
    """Sell strangle + buy wider strangle (defined-risk credit)."""
    if not (k_put_long < k_put_short < k_call_short < k_call_long):
        raise ValueError("iron_condor: strikes must be ordered k_put_long < k_put_short < k_call_short < k_call_long")
    return [
        Leg("long", "put", k_put_long, p_put_long, **kw),
        Leg("short", "put", k_put_short, p_put_short, **kw),
        Leg("short", "call", k_call_short, p_call_short, **kw),
        Leg("long", "call", k_call_long, p_call_long, **kw),
    ]


def long_butterfly(k_low: float, k_mid: float, k_high: float, p_low: float, p_mid: float, p_high: float, **kw) -> list[Leg]:
    """Call butterfly: long 1 low, short 2 mid, long 1 high."""
    if not (k_low < k_mid < k_high):
        raise ValueError("long_butterfly: strikes must be ordered k_low < k_mid < k_high")
    return [
        Leg("long", "call", k_low, p_low, qty=1, **{k: v for k, v in kw.items() if k != "qty"}),
        Leg("short", "call", k_mid, p_mid, qty=2, **{k: v for k, v in kw.items() if k != "qty"}),
        Leg("long", "call", k_high, p_high, qty=1, **{k: v for k, v in kw.items() if k != "qty"}),
    ]


def calendar_spread(
    strike: float,
    option_type: OptionType,
    p_short: float,
    p_long: float,
    dte_short: int,
    dte_long: int,
    iv_short: float = 0.25,
    iv_long: float = 0.25,
) -> list[Leg]:
    """Sell near-term + buy longer-term at the same strike."""
    if dte_long <= dte_short:
        raise ValueError("calendar_spread: dte_long must be > dte_short")
    return [
        Leg("short", option_type, strike, p_short, dte=dte_short, iv=iv_short),
        Leg("long", option_type, strike, p_long, dte=dte_long, iv=iv_long),
    ]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
def _payoff_at_expiration(legs: list[Leg], prices: np.ndarray) -> np.ndarray:
    """Per-share P&L at expiration of the *last* leg.

    For multi-expiry strategies (calendars), legs that have not yet expired
    are valued at their intrinsic value at the terminal price — a documented
    simplification. Use the Greeks block for an accurate present-day P&L.
    """
    pnl = np.zeros_like(prices, dtype=float)
    for leg in legs:
        if leg.option_type == "call":
            intrinsic = np.maximum(prices - leg.strike, 0.0)
        else:
            intrinsic = np.maximum(leg.strike - prices, 0.0)
        pnl += leg.sign * leg.qty * (intrinsic - leg.premium)
    return pnl


def _net_premium(legs: list[Leg]) -> float:
    """Negative = debit paid; positive = credit received (per-share, qty-weighted)."""
    return float(sum(-leg.sign * leg.qty * leg.premium for leg in legs))


def _find_breakevens(prices: np.ndarray, pnl: np.ndarray) -> list[float]:
    """Return all prices where P&L crosses zero (linear interpolation)."""
    breakevens: list[float] = []
    sign = np.sign(pnl)
    sign_changes = np.where(np.diff(sign) != 0)[0]
    for i in sign_changes:
        # Skip exact zeros being immediately followed by same-sign — avoid duplicates
        x0, x1 = prices[i], prices[i + 1]
        y0, y1 = pnl[i], pnl[i + 1]
        if y1 == y0:
            continue
        be = x0 - y0 * (x1 - x0) / (y1 - y0)
        breakevens.append(round(float(be), 4))
    return breakevens


def _net_greeks(legs: list[Leg], spot: float, r: float = 0.05) -> dict[str, float]:
    """Sum Greeks across legs at current spot, scaled by side and qty.

    Returns scalar dict with keys delta/gamma/theta/vega.
    """
    totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    for leg in legs:
        T = max(leg.dte, 1) / 365.0
        g = greeks_vectorized(spot, leg.strike, T, r, leg.iv, option_type=leg.option_type)
        scale = leg.sign * leg.qty
        for k in totals:
            v = float(g[k])
            if np.isfinite(v):
                totals[k] += scale * v
    return {k: round(v, 4) for k, v in totals.items()}


def _prob_profit(prices: np.ndarray, pnl: np.ndarray, spot: float, sigma: float, dte: int, r: float = 0.05) -> float:
    """Probability that P&L > 0 at expiration under BS lognormal assumption.

    Numerically integrates the lognormal density over the price grid where
    pnl > 0. Returns a value in [0, 1]. Uses the *largest* DTE in the
    strategy and a single ``sigma`` (caller passes the dominant leg's IV).
    """
    if sigma <= 0 or dte <= 0 or spot <= 0:
        return float("nan")
    T = dte / 365.0
    # Lognormal pdf for terminal price S_T given spot S0:
    # f(S_T) = 1 / (S_T * sigma * sqrt(T) * sqrt(2pi)) * exp(-(ln(S_T/S0) - (r - sigma^2/2)*T)^2 / (2 sigma^2 T))
    mu = np.log(spot) + (r - 0.5 * sigma**2) * T
    sd = sigma * np.sqrt(T)
    # Trapezoidal integration of pdf where pnl > 0
    log_p = np.log(prices)
    pdf = norm.pdf(log_p, loc=mu, scale=sd) / prices  # density over price (Jacobian)
    mask = pnl > 0
    if not mask.any():
        return 0.0
    prob = float(np.trapz(pdf[mask], prices[mask]))
    return max(0.0, min(1.0, prob))


def analyze_strategy(
    legs: list[Leg],
    spot: float,
    *,
    price_range: tuple[float, float] | None = None,
    n_points: int = 401,
    r: float = 0.05,
) -> dict:
    """Compute payoff, breakevens, Greeks, max P&L, and probability of profit.

    Parameters
    ----------
    legs
        List of ``Leg`` objects describing the strategy.
    spot
        Current underlying price (used for Greeks and PoP).
    price_range
        ``(lo, hi)`` for the payoff x-axis. Defaults to ``[0.5*spot, 1.5*spot]``
        clamped to include all strikes ± 10%.
    n_points
        Resolution of the payoff curve.

    Returns
    -------
    dict with keys: ``prices``, ``pnl``, ``breakevens``, ``max_profit``,
    ``max_loss``, ``net_premium``, ``greeks``, ``prob_profit``.

    P&L is per share (multiply by 100 for $/contract).
    """
    if not legs:
        raise ValueError("analyze_strategy: legs must not be empty")
    if spot <= 0:
        raise ValueError("analyze_strategy: spot must be positive")

    strikes = [leg.strike for leg in legs]
    if price_range is None:
        lo = min(min(strikes), spot) * 0.85
        hi = max(max(strikes), spot) * 1.15
    else:
        lo, hi = price_range
    lo = max(lo, 0.01)
    prices = np.linspace(lo, hi, n_points)
    pnl = _payoff_at_expiration(legs, prices)

    # Inspect tail behaviour to label "infinite" max profit/loss honestly.
    # If P&L is monotonically increasing/decreasing past the grid edges and
    # crosses no zero outside, max_profit / max_loss can be unbounded.
    edge_left = pnl[1] - pnl[0]
    edge_right = pnl[-1] - pnl[-2]
    has_naked_short_call = any(leg.side == "short" and leg.option_type == "call" for leg in legs)
    has_naked_short_put = any(leg.side == "short" and leg.option_type == "put" for leg in legs)
    long_calls = sum(leg.qty for leg in legs if leg.side == "long" and leg.option_type == "call")
    short_calls = sum(leg.qty for leg in legs if leg.side == "short" and leg.option_type == "call")
    long_puts = sum(leg.qty for leg in legs if leg.side == "long" and leg.option_type == "put")
    short_puts = sum(leg.qty for leg in legs if leg.side == "short" and leg.option_type == "put")
    upside_naked = short_calls > long_calls
    downside_naked = short_puts > long_puts

    max_profit = float(np.max(pnl))
    max_loss = float(np.min(pnl))
    # Upside naked short call: P&L falls as price rises → edge_right < 0
    if upside_naked and edge_right < 0:
        max_loss = float("-inf")
    # Downside naked short put: P&L falls as price drops → edge_left > 0
    # (the slope going leftward is negative, equivalently rightward slope is positive)
    if downside_naked and edge_left > 0:
        max_loss = float("-inf")
    # Long single-leg call → unbounded profit
    if (long_calls > short_calls) and edge_right > 0:
        max_profit = float("inf")
    # Long single-leg put → bounded profit (capped at strike-premium); no inf branch.

    # PoP uses the longest DTE in the basket and the qty-weighted-avg IV.
    dte_max = max((leg.dte for leg in legs), default=30)
    iv_w_num = sum(leg.iv * leg.qty for leg in legs)
    iv_w_den = sum(leg.qty for leg in legs) or 1
    iv_avg = iv_w_num / iv_w_den

    return {
        "prices": prices.tolist(),
        "pnl": pnl.tolist(),
        "breakevens": _find_breakevens(prices, pnl),
        "max_profit": max_profit,
        "max_loss": max_loss,
        "net_premium": _net_premium(legs),
        "greeks": _net_greeks(legs, spot, r=r),
        "prob_profit": _prob_profit(prices, pnl, spot, iv_avg, dte_max, r=r),
    }

"""Strategy factory helpers.

Domain:    Strategy Analysis — Factories
Contracts:
  - long_call, long_put, short_call, short_put, bull_call_spread, ...
Dependencies UPWARD:
  - core.strategies.models
Dependencies DOWNWARD:
  - services.strategy_builder, services.strategy_service
"""

from __future__ import annotations

from core.strategies.models import Leg


def long_call(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("long", "call", strike, premium, **kw)]


def long_put(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("long", "put", strike, premium, **kw)]


def short_call(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("short", "call", strike, premium, **kw)]


def short_put(strike: float, premium: float, **kw) -> list[Leg]:
    return [Leg("short", "put", strike, premium, **kw)]


def bull_call_spread(k_long: float, k_short: float, p_long: float, p_short: float, **kw) -> list[Leg]:
    if k_long >= k_short:
        raise ValueError("bull_call_spread: k_long must be lower than k_short")
    return [Leg("long", "call", k_long, p_long, **kw), Leg("short", "call", k_short, p_short, **kw)]


def bear_put_spread(k_long: float, k_short: float, p_long: float, p_short: float, **kw) -> list[Leg]:
    if k_long <= k_short:
        raise ValueError("bear_put_spread: k_long must be higher than k_short")
    return [Leg("long", "put", k_long, p_long, **kw), Leg("short", "put", k_short, p_short, **kw)]


def bear_call_spread(k_short: float, k_long: float, p_short: float, p_long: float, **kw) -> list[Leg]:
    if k_short >= k_long:
        raise ValueError("bear_call_spread: k_short must be lower than k_long")
    return [Leg("short", "call", k_short, p_short, **kw), Leg("long", "call", k_long, p_long, **kw)]


def bull_put_spread(k_short: float, k_long: float, p_short: float, p_long: float, **kw) -> list[Leg]:
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
    k_put_long: float, k_put_short: float, k_call_short: float, k_call_long: float,
    p_put_long: float, p_put_short: float, p_call_short: float, p_call_long: float, **kw
) -> list[Leg]:
    if not (k_put_long < k_put_short < k_call_short < k_call_long):
        raise ValueError("iron_condor: strikes must be ordered k_put_long < k_put_short < k_call_short < k_call_long")
    return [
        Leg("long", "put", k_put_long, p_put_long, **kw),
        Leg("short", "put", k_put_short, p_put_short, **kw),
        Leg("short", "call", k_call_short, p_call_short, **kw),
        Leg("long", "call", k_call_long, p_call_long, **kw),
    ]


def long_butterfly(k_low: float, k_mid: float, k_high: float, p_low: float, p_mid: float, p_high: float, **kw) -> list[Leg]:
    if not (k_low < k_mid < k_high):
        raise ValueError("long_butterfly: strikes must be ordered k_low < k_mid < k_high")
    return [
        Leg("long", "call", k_low, p_low, qty=1, **{k: v for k, v in kw.items() if k != "qty"}),
        Leg("short", "call", k_mid, p_mid, qty=2, **{k: v for k, v in kw.items() if k != "qty"}),
        Leg("long", "call", k_high, p_high, qty=1, **{k: v for k, v in kw.items() if k != "qty"}),
    ]


def calendar_spread(
    strike: float, option_type: str, p_short: float, p_long: float, dte_short: int, dte_long: int,
    iv_short: float = 0.25, iv_long: float = 0.25,
) -> list[Leg]:
    if dte_long <= dte_short:
        raise ValueError("calendar_spread: dte_long must be > dte_short")
    return [
        Leg("short", option_type, strike, p_short, dte=dte_short, iv=iv_short),
        Leg("long", option_type, strike, p_long, dte=dte_long, iv=iv_long),
    ]

#!/usr/bin/env python3
"""Emit JS/Python parity fixtures for the Simulation tab.

Writes ``tests/unit/sim/golden.json`` from the REAL Python implementations
(core/strategies/analyze.py, core/options/greeks/black_scholes.py,
core/strategies/prob_profit.py). The browser code in static/sim/ is then
asserted against these values within 1e-6 — no mocked data.

Run from the repo root:

    python scripts/gen_sim_golden.py
"""
from __future__ import annotations

import datetime
import json
import math
import sys
from pathlib import Path

# Ensure the repo root is importable when run as `python scripts/gen_sim_golden.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scipy.stats import norm

from core.options.greeks.black_scholes import greeks_vectorized
from core.options.simulation.expiry import simulate_expiry
from core.strategies.analyze import analyze_strategy
from core.strategies.models import Leg
from core.strategies.prob_profit import prob_profit


def _enc(x):
    """Make floats JSON-safe: inf/-inf/nan become marker strings."""
    if isinstance(x, float):
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        if math.isnan(x):
            return "NaN"
    if isinstance(x, list):
        return [_enc(v) for v in x]
    if isinstance(x, dict):
        return {k: _enc(v) for k, v in x.items()}
    return x


def _leg(**kw) -> Leg:
    return Leg(**kw)


def _expected_pnl(prices, pnl, spot, sigma, dte, r=0.05):
    """Oracle for E[P&L] — full-grid trapezoid, mirroring static/sim/stats.js."""
    if not (sigma > 0) or not (dte > 0) or not (spot > 0):
        return float("nan")
    T = dte / 365.0
    mu = math.log(spot) + (r - 0.5 * sigma * sigma) * T
    sd = sigma * math.sqrt(T)
    total = 0.0
    for k in range(len(prices) - 1):
        S0, S1 = prices[k], prices[k + 1]
        if S0 <= 0 or S1 <= 0:
            continue
        f0 = norm.pdf((math.log(S0) - mu) / sd) / sd / S0
        f1 = norm.pdf((math.log(S1) - mu) / sd) / sd / S1
        total += (pnl[k] * f0 + pnl[k + 1] * f1) * (S1 - S0) / 2
    return total


def main() -> None:
    analyze_cases = []

    # 1. Long call
    analyze_cases.append((
        "long_call", [_leg(side="long", option_type="call", strike=100, premium=4.0, qty=1, dte=30, iv=0.30)],
        100.0, 0.05,
    ))
    # 2. Naked short call -> max_loss = -inf (boundary case for the JSON bug)
    analyze_cases.append((
        "naked_short_call", [_leg(side="short", option_type="call", strike=100, premium=4.0, qty=1, dte=30, iv=0.30)],
        100.0, 0.05,
    ))
    # 3. Bull call spread
    analyze_cases.append((
        "bull_call_spread",
        [
            _leg(side="long", option_type="call", strike=100, premium=4.0, qty=1, dte=30, iv=0.30),
            _leg(side="short", option_type="call", strike=110, premium=1.5, qty=1, dte=30, iv=0.30),
        ],
        100.0, 0.05,
    ))
    # 4. Long straddle (call + put)
    analyze_cases.append((
        "long_straddle",
        [
            _leg(side="long", option_type="call", strike=100, premium=4.0, qty=1, dte=30, iv=0.30),
            _leg(side="long", option_type="put", strike=100, premium=3.0, qty=1, dte=30, iv=0.30),
        ],
        100.0, 0.05,
    ))
    # 5. Deep OTM + tiny DTE boundary
    analyze_cases.append((
        "deep_otm_tiny_dte",
        [_leg(side="long", option_type="call", strike=200, premium=0.5, qty=1, dte=1, iv=0.001)],
        100.0, 0.05,
    ))
    # 6. sigma=0 -> prob_profit should be NaN
    analyze_cases.append((
        "zero_iv",
        [_leg(side="long", option_type="call", strike=100, premium=4.0, qty=1, dte=30, iv=0.0)],
        100.0, 0.05,
    ))

    analyze_out = []
    for name, legs, spot, r in analyze_cases:
        res = analyze_strategy(legs, spot, n_points=401, r=r)
        analyze_out.append({
            "name": name,
            "legs": [
                {
                    "side": l.side, "option_type": l.option_type, "strike": l.strike,
                    "premium": l.premium, "qty": l.qty, "dte": l.dte, "iv": l.iv,
                }
                for l in legs
            ],
            "spot": spot,
            "r": r,
            "result": _enc({
                "prices": res["prices"],
                "pnl": res["pnl"],
                "breakevens": res["breakevens"],
                "max_profit": res["max_profit"],
                "max_loss": res["max_loss"],
                "net_premium": res["net_premium"],
                "greeks": res["greeks"],
                "prob_profit": res["prob_profit"],
                "expected_pnl": _expected_pnl(
                    res["prices"], res["pnl"], spot,
                    sum(l.iv * l.qty for l in legs) / max(sum(l.qty for l in legs), 1),
                    max((l.dte for l in legs), default=30), r,
                ),
            }),
        })

    # Black–Scholes per-leg pricing (incl. clamp boundaries).
    bs_out = []
    bs_specs = [
        ("atm", 100, 100, 30 / 365, 0.05, 0.30, "call"),
        ("otm_put", 100, 110, 30 / 365, 0.05, 0.30, "put"),
        ("min_sigma", 100, 100, 1 / 365, 0.05, 0.001, "call"),
        ("max_sigma", 100, 100, 30 / 365, 0.05, 20.0, "call"),
        ("below_min_sigma", 100, 100, 1 / 365, 0.05, 0.0005, "call"),  # invalid -> clamped
        ("invalid_S", 0, 100, 30 / 365, 0.05, 0.30, "call"),            # invalid -> clamped
    ]
    for name, S, K, T, r, sigma, otype in bs_specs:
        g = greeks_vectorized(S, K, T, r, sigma, option_type=otype)
        bs_out.append({
            "name": name, "S": S, "K": K, "T": T, "r": r,
            "sigma": sigma, "option_type": otype,
            "greeks": _enc({
                "delta": float(g["delta"]),
                "gamma": float(g["gamma"]),
                "theta": float(g["theta"]),
                "vega": float(g["vega"]),
                "bs_price": float(g["bs_price"]),
                "intrinsic": float(g["intrinsic"]),
                "time_value": float(g["time_value"]),
            }),
        })

    # Client-side simulateExpiry mirror (single-option K × DTE × IV grid).
    sim_out = []
    sim_specs = [
        ("call_long_atm", 100, [95, 100, 105], [7, 30], [0.2, 0.3], "call", "long", 0.05, 1, 100),
        ("put_short_otm", 100, [95, 100], [30], [0.3], "put", "short", 0.05, 2, 100),
        ("call_long_deep", 100, [80, 90, 100], [1, 365], [0.001, 0.5], "call", "long", 0.05, 1, 100),
    ]
    for name, spot, strikes, exps, ivs, otype, side, r, qty, mult in sim_specs:
        expiries = [
            {"dte": d, "date": (datetime.date.today() + datetime.timedelta(days=d)).isoformat()}
            for d in exps
        ]
        res = simulate_expiry(
            spot=spot, strikes=strikes, expiries=expiries, ivs=ivs,
            option_type=otype, side=side, r=r, qty=qty, multiplier=mult,
        )
        sim_out.append({
            "name": name, "spot": spot, "strikes": strikes, "expiries": exps,
            "ivs": ivs, "option_type": otype, "side": side, "r": r,
            "qty": qty, "multiplier": mult, "result": _enc(res),
        })

    payload = {"meta": {"n_points": 401, "r": 0.05}, "analyze": analyze_out, "bs": bs_out, "simulate_expiry": sim_out}

    out_path = Path(__file__).resolve().parent.parent / "tests" / "unit" / "sim" / "golden.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {out_path} ({len(analyze_out)} analyze cases, {len(bs_out)} bs cases)")


if __name__ == "__main__":
    main()

"""Tests for the expiry-payoff simulation feature.

The maths under test (`core.options.simulation.expiry`) is pure and
deterministic; we validate it against independently computed closed-form
relations (Black-Scholes put-call parity, breakeven definition, risk-neutral
probability), not against fabricated data. Route tests supply an explicit
``spot`` so they never touch the network.
"""

from __future__ import annotations

import datetime as dt

import pytest

from core.options.simulation import parse_expiries, simulate_expiry
from services.options.simulation import run_simulation


# --------------------------------------------------------------------------
# parse_expiries
# --------------------------------------------------------------------------
def test_parse_expiries_accepts_dte_days_and_iso_dates():
    today = dt.date(2026, 9, 2)
    parsed = parse_expiries(["7", "30", "2026-12-18"], today=today)
    assert len(parsed) == 3
    assert parsed[0]["dte"] == 7
    assert parsed[0]["date"] == "2026-09-09"
    # ISO date resolves correctly regardless of input order.
    iso = next(p for p in parsed if p["date"] == "2026-12-18")
    assert iso["dte"] == (dt.date(2026, 12, 18) - today).days


def test_parse_expiries_drops_past_and_duplicate():
    today = dt.date(2026, 9, 2)
    parsed = parse_expiries(["2020-01-01", "30", "30", "-5"], today=today)
    # Past date and the negative dte are dropped; the duplicate 30 is unique.
    assert {p["dte"] for p in parsed} == {30}
    assert all(p["dte"] >= 1 for p in parsed)


# --------------------------------------------------------------------------
# simulate_expiry — closed-form relations
# --------------------------------------------------------------------------
SPOT = 100.0
STRIKES = [90.0, 100.0, 110.0]


def _combos():
    return parse_expiries(["30"], today=dt.date(2026, 9, 2))


def test_simulate_expiry_premium_matches_black_scholes():
    import numpy as np

    from core.options.greeks.black_scholes import greeks_vectorized

    res = simulate_expiry(SPOT, STRIKES, _combos(), [0.2], "call", "long")
    T = 30 / 365.0
    expected = greeks_vectorized(
        np.full(len(STRIKES), SPOT),
        np.array(STRIKES),
        np.full(len(STRIKES), T),
        0.05,
        np.full(len(STRIKES), 0.2),
        "call",
    )["bs_price"]
    # One result row per strike; each row holds one cell per IV (here: a single IV).
    for row, exp in zip(res["results"], expected, strict=True):
        assert len(row["cells"]) == 1
        # Premium is rounded to 4 dp in the payload; allow for that.
        assert row["cells"][0]["premium"] == pytest.approx(exp, abs=1e-3)


def test_simulate_expiry_put_call_parity():
    call = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "call", "long")
    put = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "put", "long")
    c = call["results"][0]["cells"][0]["premium"]
    p = put["results"][0]["cells"][0]["premium"]
    T = 30 / 365.0
    # C - P = S - K e^{-rT}
    assert c - p == pytest.approx(SPOT - 100.0 * __import__("math").exp(-0.05 * T), abs=1e-2)


def test_simulate_expiry_breakeven_pnl_is_zero():
    res = simulate_expiry(SPOT, [100.0], _combos(), [0.3], "call", "long")
    cell = res["results"][0]["cells"][0]
    be = cell["breakeven"]
    # Interpolate the curve at the breakeven price; P&L must be ~0 there.
    prices = res["prices"]
    pnl = cell["pnl"]
    # find bracketing indices
    for i in range(len(prices) - 1):
        if prices[i] <= be <= prices[i + 1]:
            frac = (be - prices[i]) / (prices[i + 1] - prices[i])
            interp = pnl[i] + frac * (pnl[i + 1] - pnl[i])
            assert interp == pytest.approx(0.0, abs=1.0)
            break
    else:  # breakeven outside the grid — fail loudly
        raise AssertionError("breakeven not within price grid")


def test_simulate_expiry_profit_of_profit_monotonic_in_moneyness():
    res = simulate_expiry(SPOT, STRIKES, _combos(), [0.2], "call", "long")
    pops = [r["cells"][0]["pop"] for r in res["results"]]
    # ATM/ITM calls have higher PoP than OTM calls.
    assert pops[2] < pops[1] < pops[0]


def test_simulate_expiry_short_mirrors_long():
    long = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "call", "long")
    short = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "call", "short")
    lc = long["results"][0]["cells"][0]
    sc = short["results"][0]["cells"][0]
    assert lc["premium"] == sc["premium"]
    assert lc["pop"] + sc["pop"] == pytest.approx(1.0)
    # P&L curves are exact negatives.
    for a, b in zip(lc["pnl"], sc["pnl"], strict=True):
        assert a == pytest.approx(-b, abs=1e-6)
    assert lc["max_profit"] is None  # long call: unbounded
    assert sc["max_loss"] is None  # short call: unbounded


def test_simulate_expiry_unbounded_flags_call_vs_put():
    call = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "call", "long")
    put = simulate_expiry(SPOT, [100.0], _combos(), [0.2], "put", "long")
    cc = call["results"][0]["cells"][0]
    pc = put["results"][0]["cells"][0]
    assert cc["unbounded_profit"] and not cc["unbounded_loss"]
    # Long put is bounded both ways.
    assert not pc["unbounded_profit"] and not pc["unbounded_loss"]
    assert pc["max_loss"] == pytest.approx(-pc["premium"] * 100)
    assert pc["max_profit"] == pytest.approx((100.0 - pc["premium"]) * 100, abs=1.0)


def test_simulate_expiry_rejects_bad_inputs():
    with pytest.raises(ValueError):
        simulate_expiry(0, STRIKES, _combos(), [0.2])
    with pytest.raises(ValueError):
        simulate_expiry(SPOT, STRIKES, _combos(), [0.2], option_type="bad")
    with pytest.raises(ValueError):
        simulate_expiry(SPOT, STRIKES, _combos(), [0.2], side="bad")


# --------------------------------------------------------------------------
# Service layer
# --------------------------------------------------------------------------
def test_run_simulation_builds_auto_strike_ladder():
    res = run_simulation({"spot": 100.0})
    assert res["status"] == "ok"
    assert res["strike_source"] == "auto"
    assert len(res["results"]) == 7  # ±15% ladder around 100
    assert res["combos"]  # default expiries × IVs


def test_run_simulation_binds_grid_size():
    with pytest.raises(Exception) as ei:
        run_simulation({"spot": 100, "strikes": [str(i) for i in range(1, 17)]})
    assert "too_many_strikes" in str(ei.value) or "too many strikes" in str(ei.value).lower()


# --------------------------------------------------------------------------
# Route
# --------------------------------------------------------------------------
@pytest.fixture
def client():
    import os

    os.environ.setdefault("RATE_LIMIT_DISABLED", "1")
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def test_route_simulate_expiry_ok(client):
    resp = client.post(
        "/api/simulate_expiry",
        json={"ticker": "NVDA", "spot": 123.45, "ivs": "25,45", "expiries": "14,45"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["ticker"] == "NVDA"
    assert "results" in body and "combos" in body and "prices" in body
    # 2 IVs × 2 expiries = 4 combos; each strike must carry 4 cells.
    assert len(body["combos"]) == 4
    assert len(body["results"][0]["cells"]) == 4


def test_route_simulate_expiry_requires_ticker_or_spot(client):
    resp = client.post("/api/simulate_expiry", json={})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "ticker_required"


def test_route_simulate_expiry_rejects_invalid_option_type(client):
    resp = client.post("/api/simulate_expiry", json={"spot": 100, "option_type": "bad"})
    assert resp.status_code == 400
    assert resp.get_json()["code"] == "invalid_option_type"

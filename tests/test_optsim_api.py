"""Tests for POST /api/optsim (services/options/optsim.py → core.optsim).

Every input is hypothetical and stated in the request, so these run offline.
Expected values come from rule arithmetic (Reg-T) and pricing identities, the
same oracles as tests/test_optsim.py.
"""

from __future__ import annotations

import pytest

from services.options.optsim import N_SPOTS, run_optsim, strike_tick

SMILE = {"atm_iv": 16, "skew": -0.77, "curvature": 1.0}


def _condor(**extra):
    legs = [
        {"type": "put", "side": "short", "dte": 45, "delta": 0.16},
        {"type": "put", "side": "long", "dte": 45, "delta": 0.08},
        {"type": "call", "side": "short", "dte": 45, "delta": 0.16},
        {"type": "call", "side": "long", "dte": 45, "delta": 0.08},
    ]
    return {"spot": 600, "rate": 4.5, "div_yield": 1.3, "product": "etf", "legs": legs, **SMILE, **extra}


def test_optsim_route_returns_grid_for_a_delta_picked_condor(client):
    resp = client.post("/api/optsim", json=_condor())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok" and body["tree_steps"] is None

    legs = body["legs"]
    assert [leg["strike"] % 0.5 for leg in legs] == [0.0] * 4  # rounded to the 0.5 tick at spot 600
    assert legs[0]["delta"] == pytest.approx(-0.16, abs=0.01) and legs[2]["delta"] == pytest.approx(0.16, abs=0.01)
    assert body["entry_value"] < 0  # net credit

    days, spots = body["days"], body["spots"]
    assert days[0] == 0.0 and days[-1] == 45.0 and len(spots) == N_SPOTS
    assert len(body["pnl_by_day"]) == len(days) and len(body["pnl_by_day"][0]) == N_SPOTS
    assert set(body["greeks_by_day"]) == {"delta", "gamma", "theta", "vega"}
    assert body["iv_shifts"] == [-0.05, 0.0, 0.05]
    assert body["pnl_by_iv_at_entry"][1][N_SPOTS // 2] == pytest.approx(0.0, abs=1e-6)
    assert all(0 <= i < len(days) for i in body["chart_days"])

    profile = body["profile"]
    assert [row["day"] for row in profile] == days
    assert profile[0]["pnl"] == pytest.approx(0.0, abs=1e-6)
    assert profile[0]["regt_method"] == "defined_risk" and profile[-1]["regt"] == 0.0
    assert len(body["breakevens"]) == 2


def test_optsim_short_put_margins_match_the_reg_t_rule():
    # 15% × 600 − 16 OTM = 74 per share beyond the premium (the CLI example).
    body = run_optsim(
        {"spot": 600, "rate": 4.5, "div_yield": 1.3, "product": "etf", "style": "american", **SMILE,
         "legs": [{"type": "put", "side": "short", "dte": 45, "delta": 0.30}]}
    )  # fmt: skip
    assert body["legs"][0]["strike"] == 584.0
    assert body["entry_value"] == pytest.approx(-765, abs=1)
    assert body["profile"][0]["regt"] == pytest.approx(7400.0)
    assert body["profile"][0]["regt_method"] == "naked"
    assert body["tree_steps"] == 100


def test_optsim_american_style_prices_an_itm_put_above_european():
    payload = {
        "spot": 100,
        "atm_iv": 30,
        "rate": 5,
        "legs": [{"type": "put", "side": "long", "dte": 90, "strike": 120}],
    }
    eu = run_optsim({**payload, "style": "european"})
    am = run_optsim({**payload, "style": "american"})
    assert am["legs"][0]["premium"] > eu["legs"][0]["premium"]
    assert am["profile"][0]["pnl"] == pytest.approx(0.0, abs=1e-9)


def test_optsim_zero_iv_shift_returns_one_entry_curve():
    body = run_optsim(_condor(iv_shift=0))
    assert body["iv_shifts"] == [0.0] and len(body["pnl_by_iv_at_entry"]) == 1


def test_optsim_long_dated_legs_keep_the_grid_small():
    body = run_optsim({"spot": 100, "legs": [{"type": "call", "side": "long", "dte": 730, "strike": 100}]})
    assert len(body["days"]) <= 10 and body["days"][-1] == 730.0


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, "spot_required"),
        ({"spot": 600}, "legs_required"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 45}]}, "invalid_leg"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 45, "strike": 580, "delta": 0.2}]}, "invalid_leg"),
        ({"spot": 600, "legs": [{"type": "straddle", "dte": 45, "strike": 580}]}, "invalid_leg"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 0, "strike": 580}]}, "invalid_dte"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 45, "strike": 50}]}, "invalid_strike"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 45, "delta": 1.5}]}, "invalid_delta"),
        ({"spot": 600, "style": "bermudan", "legs": [{"type": "put", "dte": 45, "strike": 580}]}, "invalid_style"),
        ({"spot": 600, "product": "crypto", "legs": [{"type": "put", "dte": 45, "strike": 580}]}, "invalid_product"),
        ({"spot": 600, "legs": [{"type": "put", "dte": 45, "strike": 580}] * 7}, "too_many_legs"),
    ],
)
def test_optsim_route_rejects_bad_payloads_with_a_coded_400(client, payload, code):
    resp = client.post("/api/optsim", json=payload)
    assert resp.status_code == 400
    assert resp.get_json()["code"] == code


@pytest.mark.parametrize(("spot", "tick"), [(6000, 5.0), (600, 0.5), (100, 0.1), (5, 0.01)])
def test_strike_tick_is_about_a_tenth_of_a_percent_of_spot(spot, tick):
    assert strike_tick(spot) == tick

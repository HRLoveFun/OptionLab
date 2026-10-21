"""Tests for POST /api/optsim (services/options/optsim.py → core.optsim).

Hypothetical inputs are stated in the request; ticker mode reads a fake option
chain (``fetch_option_chain`` patched in services.options.preload), priced with
the European model on a known smile, and a fake provider answers the ``^IRX``
rate and the instrument type (services.market.reference_data), so everything runs
offline. Expected values come from rule arithmetic (Reg-T), pricing identities and
that known smile, the same oracles as tests/test_optsim.py.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from core.optsim import european
from services.market import reference_data
from services.options import preload
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


def test_atm_strike_rounds_the_spot_to_the_tick_in_hypothetical_mode():
    body = run_optsim({"spot": 600.4, **SMILE, "legs": [{"type": "call", "side": "long", "dte": 30, "strike": "ATM"}]})
    assert body["legs"][0]["strike"] == 600.5


def test_hypothetical_mode_reports_its_market_and_break_even_iv_on_the_chart_dates():
    legs = [
        {"type": "put", "side": "short", "dte": 45, "delta": 0.16},
        {"type": "call", "side": "short", "dte": 45, "delta": 0.16},
    ]
    body = run_optsim({"spot": 600, "rate": 4.5, "div_yield": 1.3, "product": "etf", **SMILE, "legs": legs})
    assert body["market"] == {"source": "hypothetical"}
    assert all(leg["expiry"] is None and leg["iv_source"] == "smile" and leg["mid"] is None for leg in body["legs"])
    be = body["breakeven_iv"]
    chart_dates = [body["days"][i] for i in body["chart_days"]]
    assert be["days"] == [d for d in chart_dates if d > 0] == [14.0, 21.0, 35.0, 45.0]
    for leg, row in zip(body["legs"], be["legs"], strict=True):
        assert len(row["iv"]) == 4 and len(row["iv"][0]) == N_SPOTS
        assert row["at_spot"][-1] is None and all(v is None for v in row["iv"][-1])  # day 45 is the expiry
        assert row["at_spot"][0] > leg["iv"]  # after 14 days of decay it takes more IV to hold the premium
        sign = 1 if leg["type"] == "call" else -1
        assert row["expiry_breakeven"] == pytest.approx(leg["strike"] + sign * leg["premium"], abs=0.01)


# ── ticker mode ───────────────────────────────────────────────────────
# Ticker mode prices with the ^IRX rate and no dividend, so the fake chain does too.
SPOT, RATE, DIV = 500.0, 0.045, 0.0


class _ReferenceProvider:
    """Answers reference_data's two questions: ^IRX in percent, and instrument types."""

    def __init__(self):
        self.irx = RATE * 100
        self.types = {"SPY": "etf", "^RUT": "index", "XLE": "etf"}

    def spot(self, symbol):
        assert symbol == "^IRX"
        return self.irx

    def instrument_type(self, symbol):
        return self.types.get(symbol, "equity")


@pytest.fixture(autouse=True)
def reference(monkeypatch):
    fake = _ReferenceProvider()
    reference_data.clear_cache()
    monkeypatch.setattr(reference_data, "get_provider", lambda: fake)
    yield fake
    reference_data.clear_cache()


def _true_iv(strike, T):
    k = np.log(np.asarray(strike, dtype=float) / SPOT)
    return 0.2 + 0.02 * np.sqrt(T) - 0.6 * k + 1.5 * k * k


def _fake_chain(ticker):
    """``fetch_option_chain``'s payload: 30/45/60-DTE expiries priced on ``_true_iv``, 10-cent wide quotes."""
    chain = {}
    for days in (30, 45, 60):
        expiry = (dt.date.today() + dt.timedelta(days=days)).isoformat()
        strikes, T = np.arange(300.0, 705.0, 5.0), days / 365
        iv = _true_iv(strikes, T)
        sides = {}
        for kind, side in (("call", "calls"), ("put", "puts")):
            mid = european(kind, SPOT, strikes, T, RATE, DIV, iv)["price"]
            sides[side] = pd.DataFrame(
                {
                    "strike": strikes,
                    "bid": np.maximum(mid - 0.05, 0.0),
                    "ask": mid + 0.05,
                    "lastPrice": mid,
                    "impliedVolatility": iv,
                    "openInterest": 10,
                    "volume": 1,
                }
            )
        chain[expiry] = sides
    return {"ticker": ticker, "spot": SPOT, "expiries": list(chain), "chain": chain}


@pytest.fixture
def listed_chain(monkeypatch):
    """Serve ``_fake_chain`` through the real preload cache; yields the tickers fetched."""
    fetched = []

    def fake(ticker):
        fetched.append(ticker)
        return _fake_chain(ticker)

    preload.clear_cache()
    monkeypatch.setattr(preload, "fetch_option_chain", fake)
    yield fetched
    preload.clear_cache()


def _ticker_payload(**extra):
    legs = [
        {"type": "put", "side": "short", "dte": 44, "delta": 0.16},
        {"type": "call", "side": "short", "dte": 44, "delta": 0.16},
    ]
    return {
        "market": "ticker",
        "ticker": "test",
        "rate": 4.5,
        "div_yield": 1.0,
        "product": "equity",
        "legs": legs,
        **extra,
    }


def test_ticker_mode_prices_legs_on_listed_expiries_strikes_and_mids(client, listed_chain):
    resp = client.post("/api/optsim", json=_ticker_payload())
    assert resp.status_code == 200 and "NaN" not in resp.get_data(as_text=True)
    body = resp.get_json()
    market = body["market"]
    assert market["source"] == "ticker" and market["ticker"] == "TEST" and market["spot"] == body["spot"] == SPOT
    assert market["as_of"] and market["atm_expiry"] == body["legs"][0]["expiry"]
    # The preload records carry cents (bid/ask) and 4-decimal IVs, so IVs match the smile to ~0.05 vol pts.
    assert market["atm_iv"] == pytest.approx(float(_true_iv(SPOT, 45 / 365)), abs=5e-4)
    expiry = (dt.date.today() + dt.timedelta(days=45)).isoformat()
    for leg in body["legs"]:
        assert leg["expiry"] == expiry and leg["dte"] == 45  # the listed expiry nearest 44 DTE
        assert leg["strike"] % 5 == 0  # a listed strike
        assert leg["iv_source"] == "mid" and leg["premium"] == pytest.approx(leg["mid"], abs=1e-4)
        assert leg["iv"] == pytest.approx(float(_true_iv(leg["strike"], 45 / 365)), abs=5e-4)
    assert body["legs"][0]["delta"] == pytest.approx(-0.16, abs=0.02)
    assert body["legs"][1]["delta"] == pytest.approx(0.16, abs=0.02)
    assert body["profile"][0]["pnl"] == pytest.approx(0.0, abs=1e-6)
    assert listed_chain == ["TEST"]


def test_ticker_mode_snaps_typed_and_atm_strikes_and_reuses_the_cached_chain(listed_chain):
    legs = [
        {"type": "call", "side": "long", "dte": 60, "strike": "atm"},
        {"type": "put", "side": "long", "dte": 33, "strike": 452.4},
    ]
    body = run_optsim(_ticker_payload(legs=legs))
    assert [leg["strike"] for leg in body["legs"]] == [500.0, 450.0]
    assert [leg["dte"] for leg in body["legs"]] == [60, 30]
    american = run_optsim(_ticker_payload(legs=legs, style="american"))
    assert american["legs"][1]["premium"] == pytest.approx(american["legs"][1]["mid"], abs=1e-4)
    assert listed_chain == ["TEST"]  # the second request reads the preload cache


def test_ticker_mode_ignores_the_hypothetical_spot_smile_dividend_and_margin_class(listed_chain):
    body = run_optsim(_ticker_payload(spot="junk", atm_iv=-1, skew="x", div_yield="x", product="crypto"))
    assert body["spot"] == SPOT and body["market"]["div_yield"] == 0.0 and body["product"] == "equity"


def test_ticker_mode_takes_the_rate_from_irx_and_the_margin_class_from_the_type(listed_chain, reference):
    reference.irx = 3.9
    body = run_optsim(_ticker_payload(ticker="spy", rate=1.0))
    market = body["market"]
    assert market["rate"] == pytest.approx(0.039) and market["rate_source"] == "^IRX" and market["rate_as_of"]
    assert market["div_yield"] == 0.0
    assert market["instrument_type"] == "etf" and market["product"] == body["product"] == "etf"
    for leg in body["legs"]:  # implied from the mid at the ^IRX rate, so the model still reprices the mid
        assert leg["premium"] == pytest.approx(leg["mid"], abs=1e-4)
    assert run_optsim(_ticker_payload(ticker="^RUT"))["product"] == "index_small"
    assert run_optsim(_ticker_payload(ticker="XLE"))["product"] == "equity"  # a narrow-based ETF


@pytest.mark.parametrize("irx", [None, 137.0])
def test_ticker_mode_falls_back_to_the_typed_rate_without_a_usable_irx_quote(listed_chain, reference, irx):
    reference.irx = irx
    market = run_optsim(_ticker_payload(rate=4.25))["market"]
    assert market["rate"] == pytest.approx(0.0425) and market["rate_source"] == "input"
    assert market["rate_as_of"] is None


def test_ticker_mode_falls_back_to_the_quoted_iv_without_a_two_sided_quote(monkeypatch):
    def no_bids(ticker):
        snap = _fake_chain(ticker)
        for sides in snap["chain"].values():
            for frame in sides.values():
                frame["bid"] = 0.0
        return snap

    preload.clear_cache()
    monkeypatch.setattr(preload, "fetch_option_chain", no_bids)
    body = run_optsim(_ticker_payload())
    preload.clear_cache()
    for leg in body["legs"]:
        assert leg["iv_source"] == "curve" and leg["mid"] is None and leg["bid"] is None
        assert leg["iv"] == pytest.approx(float(_true_iv(leg["strike"], 45 / 365)), abs=5e-5)  # the quoted IV


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"market": "live", "spot": 600, "legs": [{"type": "put", "dte": 45, "strike": 580}]}, "invalid_market"),
        (_ticker_payload(ticker=""), "ticker_required"),
        (_ticker_payload(ticker="NOT A TICKER"), "invalid_ticker"),
        (_ticker_payload(rate=99), "invalid_rate"),
        (_ticker_payload(legs=[]), "legs_required"),
        (_ticker_payload(legs=[{"type": "straddle", "dte": 45, "delta": 0.16}]), "invalid_leg"),
        (_ticker_payload(legs=[{"type": "put", "dte": 45, "delta": 0.005}]), "invalid_delta"),
    ],
)
def test_ticker_mode_rejects_bad_requests_before_fetching_a_chain(client, listed_chain, payload, code):
    resp = client.post("/api/optsim", json=payload)
    assert resp.status_code == 400 and resp.get_json()["code"] == code
    assert listed_chain == []


def test_ticker_mode_reports_a_missing_chain_as_502_without_caching_it(client, monkeypatch):
    fetched = []

    def empty(ticker):
        fetched.append(ticker)
        return {"ticker": ticker, "spot": SPOT, "expiries": [], "chain": {}}

    def broken(ticker):
        raise RuntimeError("upstream down")

    preload.clear_cache()
    monkeypatch.setattr(preload, "fetch_option_chain", empty)
    for _ in range(2):
        resp = client.post("/api/optsim", json=_ticker_payload())
        assert resp.status_code == 502 and resp.get_json()["code"] == "chain_unavailable"
    assert fetched == ["TEST", "TEST"]  # an empty chain is not cached
    monkeypatch.setattr(preload, "fetch_option_chain", broken)
    resp = client.post("/api/optsim", json=_ticker_payload())
    assert resp.status_code == 502 and resp.get_json()["code"] == "chain_unavailable"
    preload.clear_cache()

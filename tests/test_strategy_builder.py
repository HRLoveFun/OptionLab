"""Tests for services/strategy_builder.py."""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_DISABLED", "1")

import pandas as pd
import pytest

from services import strategy_builder as sb
from utils.api_errors import ApiError


def _fake_chain(spot: float = 100.0, expiry: str = "2099-12-31"):
    strikes = [80, 90, 95, 100, 105, 110, 120]
    calls = pd.DataFrame(
        {
            "strike": strikes,
            "bid": [21.0, 11.5, 7.0, 3.0, 1.5, 0.6, 0.1],
            "ask": [21.5, 12.0, 7.4, 3.2, 1.8, 0.8, 0.2],
            "lastPrice": [21.2, 11.7, 7.2, 3.1, 1.7, 0.7, 0.15],
            "impliedVolatility": [0.30, 0.28, 0.26, 0.25, 0.27, 0.30, 0.35],
            "openInterest": [100, 200, 500, 1000, 500, 200, 50],
            "volume": [10, 50, 100, 300, 100, 30, 5],
        }
    )
    puts = pd.DataFrame(
        {
            "strike": strikes,
            "bid": [0.1, 0.5, 1.6, 3.0, 6.0, 10.5, 20.5],
            "ask": [0.2, 0.7, 1.9, 3.2, 6.4, 11.0, 21.0],
            "lastPrice": [0.15, 0.6, 1.75, 3.1, 6.2, 10.8, 20.7],
            "impliedVolatility": [0.40, 0.32, 0.28, 0.25, 0.27, 0.30, 0.35],
            "openInterest": [50, 200, 500, 1000, 500, 200, 100],
            "volume": [5, 30, 100, 300, 100, 50, 10],
        }
    )
    return {
        "ticker": "AAPL",
        "spot": spot,
        "expiries": [expiry],
        "chain": {expiry: {"calls": calls, "puts": puts}},
    }


@pytest.fixture
def patched(monkeypatch):
    monkeypatch.setattr(sb, "fetch_option_chain", lambda t: _fake_chain())
    # Skip DB lookup for vol context — return None
    monkeypatch.setattr(sb.DataService, "get_cleaned_daily", staticmethod(lambda *a, **kw: pd.DataFrame()))
    return monkeypatch


def test_build_long_call_populates_mid_and_analytics(patched):
    out = sb.build_from_chain("AAPL", "long_call", "2099-12-31", {"k": 100.0})
    assert out["status"] == "ok"
    assert len(out["legs"]) == 1
    leg = out["legs"][0]
    assert leg["bid"] == 3.0 and leg["ask"] == 3.2
    assert leg["mid"] == pytest.approx(3.1)
    assert leg["liquidity"] in {"GOOD", "FAIR", "AVOID"}
    assert "prices" in out["analytics"] and "pnl" in out["analytics"]


def test_build_iron_condor_four_legs(patched):
    out = sb.build_from_chain(
        "AAPL",
        "iron_condor",
        "2099-12-31",
        {"k_put_long": 80.0, "k_put_short": 95.0, "k_call_short": 105.0, "k_call_long": 120.0},
    )
    assert len(out["legs"]) == 4
    sides = [le["side"] for le in out["legs"]]
    assert sides.count("long") == 2 and sides.count("short") == 2


def test_unknown_template_raises(patched):
    with pytest.raises(ApiError) as ei:
        sb.build_from_chain("AAPL", "moonshot", "2099-12-31", {})
    assert ei.value.code == "bad_template"


def test_missing_strikes_raise(patched):
    with pytest.raises(ApiError) as ei:
        sb.build_from_chain("AAPL", "bull_call_spread", "2099-12-31", {"k_long": 100})
    assert ei.value.code == "missing_strikes"


def test_unavailable_expiry_raises(patched):
    with pytest.raises(ApiError) as ei:
        sb.build_from_chain("AAPL", "long_call", "1999-01-01", {"k": 100})
    assert ei.value.code == "expiry_unavailable"


def test_slippage_is_positive_for_long_legs(patched):
    out = sb.build_from_chain("AAPL", "long_call", "2099-12-31", {"k": 100.0})
    # long call: pays ask, mid is lower → slippage > 0
    assert out["slippage"]["slippage_usd"] > 0


def test_vol_context_unavailable_when_no_history(patched):
    out = sb.build_from_chain("AAPL", "long_call", "2099-12-31", {"k": 100.0})
    vc = out["vol_context"]
    assert vc["available"] is False

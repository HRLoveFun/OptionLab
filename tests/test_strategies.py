"""Tests for core/strategies.py and services/strategy_service.py."""

import math

import pytest

from core import strategies as S
from services.strategy_service import analyze, list_strategies


def test_long_call_unbounded_profit_bounded_loss():
    legs = S.long_call(strike=100, premium=2, dte=30, iv=0.25)
    res = S.analyze_strategy(legs, spot=100, n_points=801)
    # Loss is capped at the premium (per share) when price ≤ strike
    assert res["max_loss"] == pytest.approx(-2.0, abs=0.05)
    # Profit is unbounded above; analyzer should report inf
    assert res["max_profit"] == math.inf
    # Single breakeven at strike + premium
    assert any(abs(b - 102.0) < 0.5 for b in res["breakevens"])


def test_short_put_capped_profit_huge_loss():
    legs = S.short_put(strike=100, premium=2, dte=30, iv=0.25)
    res = S.analyze_strategy(legs, spot=100, n_points=801)
    # Profit capped at premium received
    assert res["max_profit"] == pytest.approx(2.0, abs=0.05)
    # Loss labelled as -inf because grid lower edge is going more negative
    assert res["max_loss"] == -math.inf


def test_bull_call_spread_bounded_both_sides():
    legs = S.bull_call_spread(k_long=100, k_short=110, p_long=3, p_short=1, dte=30, iv=0.25)
    res = S.analyze_strategy(legs, spot=105, n_points=801)
    # Net debit = 2 → max loss = -2, max profit = (110-100) - 2 = 8
    assert res["max_loss"] == pytest.approx(-2.0, abs=0.05)
    assert res["max_profit"] == pytest.approx(8.0, abs=0.05)
    assert res["net_premium"] == pytest.approx(-2.0)
    # Single breakeven near 102
    assert len(res["breakevens"]) == 1
    assert abs(res["breakevens"][0] - 102.0) < 0.5


def test_iron_condor_two_breakevens_credit():
    legs = S.iron_condor(
        k_put_long=90, k_put_short=95, k_call_short=110, k_call_long=115,
        p_put_long=0.5, p_put_short=1.5, p_call_short=1.5, p_call_long=0.5,
        dte=30, iv=0.25,
    )
    res = S.analyze_strategy(legs, spot=100, n_points=1001)
    # Net credit = (1.5+1.5) - (0.5+0.5) = 2.0
    assert res["net_premium"] == pytest.approx(2.0, abs=0.05)
    # Max profit = net credit
    assert res["max_profit"] == pytest.approx(2.0, abs=0.05)
    # Max loss = wing width - credit = 5 - 2 = -3
    assert res["max_loss"] == pytest.approx(-3.0, abs=0.05)
    # Two breakevens (one above 95, one below 110)
    assert len(res["breakevens"]) == 2


def test_long_straddle_two_breakevens_unbounded_profit():
    legs = S.long_straddle(strike=100, p_call=2, p_put=2, dte=30, iv=0.30)
    res = S.analyze_strategy(legs, spot=100, n_points=801)
    # Net debit = 4
    assert res["net_premium"] == pytest.approx(-4.0, abs=0.01)
    # Max loss = -4 at strike
    assert res["max_loss"] == pytest.approx(-4.0, abs=0.05)
    assert len(res["breakevens"]) == 2
    # Breakevens at 96 and 104
    bes = sorted(res["breakevens"])
    assert abs(bes[0] - 96.0) < 0.5
    assert abs(bes[1] - 104.0) < 0.5


def test_long_butterfly_zero_max_loss_at_wings():
    legs = S.long_butterfly(k_low=95, k_mid=100, k_high=105, p_low=6, p_mid=3, p_high=1.2, dte=30, iv=0.25)
    res = S.analyze_strategy(legs, spot=100, n_points=801)
    # Net debit = 6 - 6 + 1.2 = 1.2; max profit at K_mid = 5 - 1.2 = 3.8
    assert res["net_premium"] == pytest.approx(-1.2, abs=0.05)
    assert res["max_profit"] == pytest.approx(3.8, abs=0.05)
    # Max loss = -net_debit (legs all bounded)
    assert res["max_loss"] == pytest.approx(-1.2, abs=0.05)


def test_factory_validation():
    with pytest.raises(ValueError):
        S.bull_call_spread(k_long=110, k_short=100, p_long=3, p_short=1)
    with pytest.raises(ValueError):
        S.iron_condor(
            k_put_long=100, k_put_short=90, k_call_short=110, k_call_long=120,
            p_put_long=0.5, p_put_short=1.5, p_call_short=1.5, p_call_long=0.5,
        )


def test_service_analyze_happy_path():
    res = analyze({
        "strategy": "bull_call_spread",
        "spot": 105,
        "params": {"k_long": 100, "k_short": 110, "p_long": 3, "p_short": 1, "dte": 30, "iv": 0.25},
    })
    assert res["status"] == "ok"
    assert res["strategy"] == "bull_call_spread"
    assert "pnl" in res and "prices" in res
    assert len(res["pnl"]) == len(res["prices"])
    assert res["max_profit"] == pytest.approx(8.0, abs=0.05)


def test_service_analyze_unknown_strategy():
    res = analyze({"strategy": "magic_unicorn", "spot": 100, "params": {}})
    assert res["status"] == "error"
    assert "unknown" in res["message"].lower()


def test_service_analyze_invalid_spot():
    res = analyze({"strategy": "long_call", "spot": -5, "params": {"strike": 100, "premium": 2}})
    assert res["status"] == "error"


def test_service_lists_all_strategies():
    names = list_strategies()
    assert "iron_condor" in names
    assert "calendar_spread" in names
    assert len(names) >= 12


def test_greeks_short_call_negative_delta():
    legs = S.short_call(strike=100, premium=2, dte=30, iv=0.25)
    res = S.analyze_strategy(legs, spot=100)
    # Short call → negative delta
    assert res["greeks"]["delta"] < 0
    # Short call → negative vega (you want IV to drop)
    assert res["greeks"]["vega"] < 0


def test_prob_profit_in_unit_interval():
    legs = S.long_straddle(strike=100, p_call=2, p_put=2, dte=30, iv=0.30)
    res = S.analyze_strategy(legs, spot=100)
    pop = res["prob_profit"]
    assert 0.0 <= pop <= 1.0

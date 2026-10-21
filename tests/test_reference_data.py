"""Tests for services/market/reference_data.py (instrument type and the ^IRX risk-free rate).

A fake provider stands in for yfinance, so these run offline and count how often
the provider is asked.
"""

from __future__ import annotations

import math

import pytest

from services.market import reference_data


class _FakeProvider:
    def __init__(self, irx=4.07, types=None):
        self.irx = irx
        self.types = types or {}
        self.calls = []

    def spot(self, symbol):
        self.calls.append(("spot", symbol))
        if isinstance(self.irx, Exception):
            raise self.irx
        return self.irx

    def instrument_type(self, symbol):
        self.calls.append(("type", symbol))
        return self.types.get(symbol)


@pytest.fixture
def provider(monkeypatch):
    fake = _FakeProvider(types={"SPY": "etf", "^SPX": "index"})
    reference_data.clear_cache()
    monkeypatch.setattr(reference_data, "get_provider", lambda: fake)
    yield fake
    reference_data.clear_cache()


def test_risk_free_rate_reads_irx_in_percent_and_caches_it(provider):
    quote = reference_data.risk_free_rate()
    assert quote.rate == pytest.approx(0.0407) and quote.symbol == "^IRX" and quote.as_of
    assert reference_data.risk_free_rate() == quote
    assert provider.calls == [("spot", "^IRX")]  # the second read came from the cache


@pytest.mark.parametrize("irx", [None, math.nan, 137.0, -6.0, RuntimeError("yahoo down")])
def test_risk_free_rate_is_none_for_a_missing_or_implausible_quote_and_is_not_cached(provider, irx):
    provider.irx = irx
    assert reference_data.risk_free_rate() is None
    provider.irx = 3.9
    assert reference_data.risk_free_rate().rate == pytest.approx(0.039)  # a failure is not remembered


def test_instrument_type_normalises_the_symbol_and_caches_answers_but_not_misses(provider):
    assert reference_data.instrument_type(" spy ") == "etf"
    assert reference_data.instrument_type("SPY") == "etf"
    assert reference_data.instrument_type("NOPE") is None
    assert reference_data.instrument_type("NOPE") is None
    assert reference_data.instrument_type("") is None
    assert provider.calls == [("type", "SPY"), ("type", "NOPE"), ("type", "NOPE")]

"""Bounds on the option-chain preload cache (services/options/preload.py).

The cache is keyed by user-facing tickers and each payload is a full option
chain, so the key space must stay bounded (see review 2026-09-08, P2).
"""

import datetime as dt

import services.options.preload as preload


def setup_function():
    preload.clear_cache()


def teardown_function():
    preload.clear_cache()


def _age_out(key: str) -> None:
    preload._option_chain_cache[key]["ts"] = dt.datetime.now() - dt.timedelta(minutes=preload.CACHE_TTL_MINUTES + 1)


def test_set_cached_evicts_oldest_when_full(monkeypatch):
    monkeypatch.setattr(preload, "_OPTION_CHAIN_CACHE_MAX", 3)
    for i in range(4):
        preload.set_cached(f"T{i}", {"i": i})

    assert len(preload._option_chain_cache) == 3
    assert preload.get_cached("T0") is None  # oldest evicted
    assert preload.get_cached("T3") == {"i": 3}


def test_set_cached_prefers_expired_eviction(monkeypatch):
    monkeypatch.setattr(preload, "_OPTION_CHAIN_CACHE_MAX", 2)
    preload.set_cached("OLD", {"x": 1})
    _age_out("OLD")
    preload.set_cached("A", {"x": 2})
    preload.set_cached("B", {"x": 3})  # eviction pass removes OLD first

    assert len(preload._option_chain_cache) == 2
    assert "OLD" not in preload._option_chain_cache
    assert preload.get_cached("A") == {"x": 2}
    assert preload.get_cached("B") == {"x": 3}


def test_get_cached_drops_expired_entry():
    preload.set_cached("OLD", {"x": 1})
    _age_out("OLD")

    assert preload.get_cached("OLD") is None
    assert "OLD" not in preload._option_chain_cache

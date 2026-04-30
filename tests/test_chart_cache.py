"""LRU cache behaviour for services.chart_service.

WHY: chart cache eviction and hit/miss accounting were uncovered by existing
tests. These behaviours are load-bearing: a leak here grows matplotlib memory
unboundedly in long-running processes.
"""

from __future__ import annotations

import pytest

from services import chart_service as cs


@pytest.fixture(autouse=True)
def _reset_cache():
    cs.ChartService.cache_clear()
    yield
    cs.ChartService.cache_clear()


def test_cache_put_and_get_round_trip():
    cs.ChartService.cache_put(("k", 1), "PAYLOAD")
    assert cs.ChartService.cache_get(("k", 1)) == "PAYLOAD"


def test_cache_miss_returns_none_and_increments_miss_counter():
    assert cs.ChartService.cache_get(("missing",)) is None
    stats = cs.ChartService.cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


def test_cache_hit_increments_hit_counter_and_promotes_recency():
    cs.ChartService.cache_put(("a",), "A")
    cs.ChartService.cache_put(("b",), "B")
    # Access "a" so it becomes most-recent.
    assert cs.ChartService.cache_get(("a",)) == "A"
    stats = cs.ChartService.cache_stats()
    assert stats["hits"] == 1
    assert stats["size"] == 2


def test_cache_evicts_oldest_when_over_max(monkeypatch):
    monkeypatch.setattr(cs, "_CACHE_MAX_ENTRIES", 3)
    for i in range(5):
        cs.ChartService.cache_put((i,), f"v{i}")
    stats = cs.ChartService.cache_stats()
    assert stats["size"] == 3
    # Oldest two (0, 1) should have been evicted.
    assert cs.ChartService.cache_get((0,)) is None
    assert cs.ChartService.cache_get((1,)) is None
    assert cs.ChartService.cache_get((4,)) == "v4"


def test_cache_lru_promotion_keeps_recently_used(monkeypatch):
    monkeypatch.setattr(cs, "_CACHE_MAX_ENTRIES", 2)
    cs.ChartService.cache_put(("x",), "X")
    cs.ChartService.cache_put(("y",), "Y")
    # Touch x so it becomes most-recent; inserting z should evict y.
    cs.ChartService.cache_get(("x",))
    cs.ChartService.cache_put(("z",), "Z")
    assert cs.ChartService.cache_get(("x",)) == "X"
    assert cs.ChartService.cache_get(("y",)) is None
    assert cs.ChartService.cache_get(("z",)) == "Z"


def test_cached_chart_decorator_memoises_calls():
    calls = {"n": 0}

    @cs.cached_chart(key_fn=lambda ticker, **_: ("t", ticker))
    def render(ticker: str) -> str:
        calls["n"] += 1
        return f"png-{ticker}"

    assert render("AAPL") == "png-AAPL"
    assert render("AAPL") == "png-AAPL"
    assert calls["n"] == 1  # second call served from cache
    assert render("MSFT") == "png-MSFT"
    assert calls["n"] == 2


def test_cached_chart_does_not_cache_empty_result():
    calls = {"n": 0}

    @cs.cached_chart(key_fn=lambda **kw: ("k",))
    def render() -> str:
        calls["n"] += 1
        return ""  # falsy: must not be cached

    render()
    render()
    assert calls["n"] == 2


def test_cached_chart_bypasses_cache_when_key_fn_raises(caplog):
    calls = {"n": 0}

    @cs.cached_chart(key_fn=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")))
    def render(**_) -> str:
        calls["n"] += 1
        return "PNG"

    assert render(x=1) == "PNG"
    assert render(x=1) == "PNG"
    assert calls["n"] == 2  # cache fully bypassed


def test_features_hash_stable_for_same_input():
    h1 = cs.features_hash({"a": 1, "b": [1, 2, 3]})
    h2 = cs.features_hash({"b": [1, 2, 3], "a": 1})  # different key order
    assert h1 == h2
    assert len(h1) == 12


def test_features_hash_handles_unserialisable_input():
    # Should not raise; falls back to repr.
    h = cs.features_hash({"obj": object()})
    assert isinstance(h, str) and len(h) == 12

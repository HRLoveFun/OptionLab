"""Tests for data_pipeline/job_cache.py."""

import threading
import time

import pytest

from data_pipeline import job_cache as jc


@pytest.fixture(autouse=True)
def _reset():
    jc._reset()
    yield
    jc._reset()


class TestCreateAndGet:
    def test_create_returns_unique_ids(self):
        a = jc.create_job({"x": 1}, ["AAPL"])
        b = jc.create_job({"x": 2}, ["NVDA"])
        assert a != b
        assert jc._size() == 2

    def test_get_returns_form_data_copy(self):
        original = {"ticker": "AAPL", "frequency": "D"}
        job_id = jc.create_job(original, ["AAPL"])
        # Mutating the source after creation must not affect cached data.
        original["frequency"] = "M"
        entry = jc.get_job(job_id)
        assert entry is not None
        assert entry.form_data["frequency"] == "D"

    def test_get_unknown_returns_none(self):
        assert jc.get_job("does-not-exist") is None
        assert jc.get_job("") is None


class TestCompute:
    def test_single_compute_then_cached(self):
        job_id = jc.create_job({"k": "v"}, ["AAPL"])
        calls = []

        def fn(form_data):
            calls.append(1)
            return {"answer": 42}

        r1 = jc.compute_or_get(job_id, "AAPL", "stat", fn)
        r2 = jc.compute_or_get(job_id, "AAPL", "stat", fn)
        assert r1 == r2 == {"answer": 42}
        # Second call must hit cache.
        assert len(calls) == 1

    def test_different_kinds_compute_independently(self):
        job_id = jc.create_job({}, ["AAPL"])
        calls = {"a": 0, "b": 0}

        def fn_a(_):
            calls["a"] += 1
            return "A"

        def fn_b(_):
            calls["b"] += 1
            return "B"

        assert jc.compute_or_get(job_id, "AAPL", "kind_a", fn_a) == "A"
        assert jc.compute_or_get(job_id, "AAPL", "kind_b", fn_b) == "B"
        assert calls == {"a": 1, "b": 1}

    def test_unknown_job_raises(self):
        with pytest.raises(KeyError):
            jc.compute_or_get("nope", "AAPL", "stat", lambda _: None)

    def test_concurrent_callers_single_flight(self):
        """When N threads call compute_or_get for the same key concurrently,
        the compute_fn must run exactly once (single-flight)."""
        job_id = jc.create_job({}, ["AAPL"])
        call_count = 0
        lock = threading.Lock()
        start = threading.Barrier(5)

        def fn(_):
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.05)  # hold the lock so other threads queue up
            return {"v": call_count}

        results = []

        def worker():
            start.wait()
            results.append(jc.compute_or_get(job_id, "AAPL", "kind", fn))

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert call_count == 1
        # All callers see the same memoised value.
        assert all(r == {"v": 1} for r in results)


class TestExpiry:
    def test_lazy_expiry_on_read(self, monkeypatch):
        # Force a tiny TTL so we can deterministically expire.
        monkeypatch.setattr(jc, "JOB_CACHE_TTL", 0)
        job_id = jc.create_job({}, ["AAPL"])
        # With TTL=0 every read after creation should evict.
        time.sleep(0.001)
        assert jc.get_job(job_id) is None
        with pytest.raises(KeyError):
            jc.compute_or_get(job_id, "AAPL", "k", lambda _: 1)

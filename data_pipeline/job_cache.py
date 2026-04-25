"""In-memory job cache for streaming HTMX render endpoints.

Architecture
------------
The streaming render flow is:

    POST /                       → JobCache.create_job(form_data, tickers)
                                    returns job_id; render skeleton.
    GET  /render/<kind>?job=…    → JobCache.compute_or_get(job_id, ticker, kind, fn)
                                    runs `fn` (the slice computation) under a
                                    per-(job, ticker, kind) lock; subsequent
                                    callers get the cached result.

We keep the cache deliberately small and scoped to a single Flask process. It
is *not* a substitute for a proper task queue — it just bridges the gap
between "POST returns immediately" and "render endpoints know which form data
to use and don't recompute the same slice multiple times".

TTL is short (90s by default) because:
- Browsers usually fire all `hx-trigger="load"` requests within the first
  second or two after POST.
- Sidebar ticker switches that re-fire `/render/*` happen interactively.
- After ~90s the user likely walked away or moved on.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

# TTL is configurable via env so tests can shorten it; default 90s.
JOB_CACHE_TTL = int(os.environ.get("JOB_CACHE_TTL", "90"))


class _JobEntry:
    __slots__ = ("form_data", "tickers", "created_at", "results", "key_locks", "_master_lock")

    def __init__(self, form_data: dict, tickers: list[str]):
        self.form_data: dict = form_data
        self.tickers: list[str] = list(tickers)
        self.created_at: float = time.monotonic()
        # Memoised slice results, keyed by (ticker, kind).
        self.results: dict[tuple[str, str], Any] = {}
        # Per-key locks so concurrent /render/* calls for the same slice
        # collapse into a single computation (single-flight).
        self.key_locks: dict[tuple[str, str], threading.Lock] = {}
        # Mutex for `key_locks` and `results` dict-level mutations.
        self._master_lock = threading.Lock()

    def _lock_for(self, key: tuple[str, str]) -> threading.Lock:
        with self._master_lock:
            lock = self.key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self.key_locks[key] = lock
            return lock


# Module-level store. A dict + lock is sufficient for a single-process Flask
# dev/gunicorn-sync deployment. For multi-worker gunicorn each worker gets its
# own cache — that's fine because the same client's job_id keeps hitting the
# same worker only by chance; a missed cache simply triggers recomputation.
_jobs: dict[str, _JobEntry] = {}
_jobs_lock = threading.Lock()


def _now() -> float:
    return time.monotonic()


def _evict_expired(now: float | None = None) -> None:
    """Drop entries older than TTL. Cheap O(n); n is tiny in practice."""
    cutoff = (now if now is not None else _now()) - JOB_CACHE_TTL
    with _jobs_lock:
        stale = [jid for jid, e in _jobs.items() if e.created_at < cutoff]
        for jid in stale:
            _jobs.pop(jid, None)
    if stale:
        logger.debug("JobCache evicted %d stale job(s)", len(stale))


def create_job(form_data: dict, tickers: list[str]) -> str:
    """Register a new job and return its opaque id.

    `form_data` is shallow-copied so later mutations by the caller don't
    leak into the cache.
    """
    _evict_expired()
    job_id = uuid.uuid4().hex
    entry = _JobEntry(form_data=dict(form_data), tickers=list(tickers))
    with _jobs_lock:
        _jobs[job_id] = entry
    logger.info("JobCache created job=%s tickers=%s", job_id[:8], tickers)
    return job_id


def get_job(job_id: str) -> _JobEntry | None:
    """Return the job entry if present and not expired, else None."""
    if not job_id:
        return None
    with _jobs_lock:
        entry = _jobs.get(job_id)
    if entry is None:
        return None
    if _now() - entry.created_at > JOB_CACHE_TTL:
        # Lazy expiry on read.
        with _jobs_lock:
            _jobs.pop(job_id, None)
        return None
    return entry


def compute_or_get(
    job_id: str, ticker: str, kind: str, compute_fn: Callable[[dict], Any]
) -> Any:
    """Memoised compute under a per-(ticker, kind) single-flight lock.

    Raises:
        KeyError: if `job_id` is unknown or expired.
    """
    entry = get_job(job_id)
    if entry is None:
        raise KeyError(f"unknown or expired job_id={job_id!r}")

    key = (ticker, kind)
    # Fast path: already computed.
    cached = entry.results.get(key)
    if cached is not None:
        return cached

    # Slow path: take the per-key lock so concurrent callers wait instead of
    # racing the same compute.
    lock = entry._lock_for(key)
    with lock:
        # Double-check after acquiring the lock.
        cached = entry.results.get(key)
        if cached is not None:
            return cached
        t0 = _now()
        result = compute_fn(entry.form_data)
        elapsed = _now() - t0
        entry.results[key] = result
        logger.info(
            "JobCache computed job=%s ticker=%s kind=%s in %.2fs",
            job_id[:8], ticker, kind, elapsed,
        )
        return result


# ── Test helpers ────────────────────────────────────────────────────────────
def _reset() -> None:
    """Clear all jobs. Test-only helper."""
    with _jobs_lock:
        _jobs.clear()


def _size() -> int:
    """Number of live job entries. Test/diagnostic helper."""
    with _jobs_lock:
        return len(_jobs)

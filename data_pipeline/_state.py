"""Process-local shared state for the read + orchestrate layers.

Domain:    Data Pipeline — Shared State
Context:
  - All heavy-lifting state (update cooldown locks, the query cache, TTL
    constants) is co-located here so ``read`` and ``orchestrate`` — and the
    tests that inspect them — operate on the **same** underlying objects.
  - It lives at the ``data_pipeline/`` root rather than in ``read/`` or
    ``orchestrate/`` because both layers need it and neither may import the
    other's internals (``read`` imports ``orchestrate``, so ``orchestrate``
    must not import ``read``). See the layer table in
    docs/architecture_review.md §3.
Why not in ``store/``: this is in-memory state, not persistence.
Contracts:
  - ``_query_cache`` / ``_cache_get`` / ``_cache_set`` / ``_cache_invalidate``
  - ``_update_locks`` / ``_update_lock_mutex`` / ``_UPDATE_COOLDOWN`` / ``GAP_SCAN_DAYS``
Dependencies UPWARD:
  - (none — stdlib + pandas only)
Dependencies DOWNWARD:
  - read/ (query cache), orchestrate/ (update locks), tests
"""

import os
import threading
import time

import pandas as pd

_UPDATE_COOLDOWN = 60
GAP_SCAN_DAYS = int(os.environ.get("GAP_SCAN_DAYS", "30"))
_QUERY_CACHE_TTL = 60

# CONSTRAINT: bound on the query cache — keys include user-supplied start/end
# strings, and expired entries were previously only dropped when the same key
# was re-read, so unrevisited keys accumulated forever on a long-lived process.
_QUERY_CACHE_MAX = 256

_update_locks: dict = {}
_update_lock_mutex = threading.Lock()

_query_cache: dict = {}
_query_cache_lock = threading.Lock()


def _cache_get(key: tuple) -> pd.DataFrame | None:
    with _query_cache_lock:
        entry = _query_cache.get(key)
        if entry and (time.monotonic() - entry[0]) < _QUERY_CACHE_TTL:
            return entry[1].copy()
        if entry:
            del _query_cache[key]
    return None


def _cache_set(key: tuple, df: pd.DataFrame) -> None:
    with _query_cache_lock:
        _query_cache[key] = (time.monotonic(), df)
        if len(_query_cache) > _QUERY_CACHE_MAX:
            now = time.monotonic()
            for k in [k for k, (ts, _) in _query_cache.items() if (now - ts) >= _QUERY_CACHE_TTL]:
                del _query_cache[k]
            while len(_query_cache) > _QUERY_CACHE_MAX:
                oldest = min(_query_cache, key=lambda k: _query_cache[k][0])
                del _query_cache[oldest]


def _cache_invalidate(ticker: str) -> None:
    with _query_cache_lock:
        keys_to_remove = [k for k in _query_cache if k[0] == ticker]
        for k in keys_to_remove:
            del _query_cache[k]

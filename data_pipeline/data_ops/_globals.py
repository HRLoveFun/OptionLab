"""Shared globals for data operations (locks, caches, TTLs).

All heavy-lifting state (cooldown locks, query cache, TTL constants) is
co-located here so that ``data_ops._service.DataService`` and tests operate
on the **same** underlying objects.
"""

import os
import threading
import time

import pandas as pd

_UPDATE_COOLDOWN = 60
GAP_SCAN_DAYS = int(os.environ.get("GAP_SCAN_DAYS", "30"))
_QUERY_CACHE_TTL = 60

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


def _cache_invalidate(ticker: str) -> None:
    with _query_cache_lock:
        keys_to_remove = [k for k in _query_cache if k[0] == ticker]
        for k in keys_to_remove:
            del _query_cache[k]

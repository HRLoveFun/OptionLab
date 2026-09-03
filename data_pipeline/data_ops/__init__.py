"""Data operations — DataService facade and shared cache/lock globals.

All heavy-lifting state (cooldown locks, query cache, TTL constants) is
co-located in ``_globals`` so that DataService and tests operate on the
same underlying objects.
"""

from ._globals import (
    _QUERY_CACHE_TTL,
    GAP_SCAN_DAYS,
    _cache_get,
    _cache_invalidate,
    _cache_set,
    _query_cache,
    _query_cache_lock,
    _update_lock_mutex,
    _update_locks,
)
from .facade import DataService

__all__ = [
    "DataService",
    "_query_cache",
    "_query_cache_lock",
    "_update_lock_mutex",
    "_update_locks",
    "_cache_get",
    "_cache_set",
    "_cache_invalidate",
    "_QUERY_CACHE_TTL",
    "GAP_SCAN_DAYS",
]

"""Data service layer — BACKWARD-COMPAT ADAPTER.

All logic has moved to ``data_pipeline.data_ops``.  New code should
import from there directly; this module exists only to satisfy existing
callers in ``app.py``, ``core/``, ``services/`` and ``tests/`` during the
transition.

NOTE: ``_update_locks``, ``_query_cache``, etc. are re-exported from
``data_ops._globals`` so that tests which mutate them continue to operate
on the same underlying objects.
"""

from data_pipeline.data_ops import (
    DataService,
    GAP_SCAN_DAYS,
    _QUERY_CACHE_TTL,
    _cache_get,
    _cache_invalidate,
    _cache_set,
    _query_cache,
    _query_cache_lock,
    _update_lock_mutex,
    _update_locks,
)

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

"""Data operations sub-package.

New code should import directly from here; the legacy module
``data_pipeline.data_service`` is a thin backward-compat adapter.
"""

from ._globals import (
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
from ._service import DataService

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

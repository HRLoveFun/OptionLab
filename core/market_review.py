"""Market review — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.market_review
  from core.market_review import market_review, market_review_timeseries, BENCHMARKS

This module re-exports the canonical implementation from core.market_review.*
to preserve existing import paths during the transition.
"""

from core.market_review import (
    BENCHMARKS,
    _fetch_market_data,
    _mr_cache,
    _mr_cache_lock,
    fetch_close_panel,
    market_review,
    market_review_timeseries,
)

__all__ = [
    "market_review",
    "market_review_timeseries",
    "BENCHMARKS",
    "_mr_cache",
    "_mr_cache_lock",
    "_fetch_market_data",
    "fetch_close_panel",
]

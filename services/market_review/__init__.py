"""Market review — I/O orchestration package.

Assembles the benchmark close-price panel (via ``DataService.get_close_panel``,
which reads ``clean_bars`` and heals coverage through ``ensure_range`` —
ADR 0011 L5) behind a 5-minute L1 in-memory cache, then delegates the pure
computation to ``core.market_review``. Batch B10 retired the standalone
``market_review_prices`` ladder; benchmark symbols now flow through the
provider seam like any other ticker.

Public entry points keep the historical ``(instrument, start, end)`` signature
so routes / services / tests call them the same way they called the old
``core.market_review`` functions.
"""

from core.market_review.constants import BENCHMARKS
from services.market_review.facade import market_review, market_review_timeseries
from services.market_review.fetch import (
    _fetch_market_data,
    _mr_cache,
    _mr_cache_lock,
    fetch_market_data,
)

__all__ = [
    "market_review",
    "market_review_timeseries",
    "fetch_market_data",
    "_fetch_market_data",
    "BENCHMARKS",
    "_mr_cache",
    "_mr_cache_lock",
]

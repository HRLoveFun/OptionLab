"""Market review — I/O orchestration package.

Owns the L1/L2/L3 cache ladder (in-memory TTL → SQLite ``market_review_prices``
→ yfinance) that produces the close-price panel, then delegates the pure
computation to ``core.market_review``. This is the layer permitted to touch
``data_pipeline`` for market review (ADR 0003 / architecture review §2
`core-purity`).

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
    fetch_close_panel,
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
    "fetch_close_panel",
]

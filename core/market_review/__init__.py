"""Market review domain.

Dependency graph:
    fetch.py      # Data fetching (L1/L2/L3 cache)
    compute.py    # Returns / volatility / correlation
    format.py     # HTML / table formatting
    timeseries.py # Chart.js time-series payload
"""

from core.market_review.compute import market_review
from core.market_review.fetch import (
    BENCHMARKS,
    _mr_cache,
    _mr_cache_lock,
)
from core.market_review.fetch import (
    fetch_market_data as _fetch_market_data,
)
from core.market_review.timeseries import market_review_timeseries

# Expose fetch_close_panel at package level so unittest.mock.patch paths work
from data_pipeline.yf_client import fetch_close_panel

__all__ = [
    "market_review",
    "market_review_timeseries",
    "BENCHMARKS",
    "_mr_cache",
    "_mr_cache_lock",
    "_fetch_market_data",
    "fetch_close_panel",
]

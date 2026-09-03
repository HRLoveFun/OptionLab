"""Market review domain — pure computation.

This package is free of I/O: it turns an already-fetched close-price panel
into the review table / Chart.js payload. The L1/L2/L3 cache ladder that
produces the panel lives in ``services.market_review`` (ADR 0003 / architecture
review §2 `core-purity`).

Dependency graph:
    constants.py  # BENCHMARKS, _canonicalize_instrument (pure)
    compute.py    # build_review: returns / volatility / correlation table
    timeseries.py # build_timeseries: Chart.js time-series payload
"""

from core.market_review.compute import build_review
from core.market_review.constants import BENCHMARKS, _canonicalize_instrument
from core.market_review.timeseries import build_timeseries

__all__ = [
    "build_review",
    "build_timeseries",
    "BENCHMARKS",
    "_canonicalize_instrument",
]

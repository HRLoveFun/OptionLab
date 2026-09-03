"""Market review orchestration facade.

Thin glue: fetch the close-price panel via the cache ladder, then hand it to
the pure ``core.market_review`` builders. The historical
``(instrument, start, end)`` signature is preserved so routes / services /
tests call these the same way they called the old ``core.market_review``
functions.

Dependencies:
  - core.market_review (build_review, build_timeseries)
  - services.market_review.fetch (fetch_market_data)
"""

from __future__ import annotations

from core.market_review import build_review, build_timeseries
from services.market_review.fetch import fetch_market_data


def market_review(instrument, start_date=None, end_date=None):
    """Return the market-review summary table for *instrument*."""
    data, returns, display = fetch_market_data(instrument, start_date, end_date)
    return build_review(instrument, data, returns, display)


def market_review_timeseries(instrument, start_date=None, end_date=None):
    """Return the Chart.js time-series payload for *instrument*."""
    data, returns, display = fetch_market_data(instrument, start_date, end_date)
    return build_timeseries(instrument, data, returns, display)

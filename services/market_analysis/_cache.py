"""Chart caching helpers for market analysis."""

import logging

from services.chart_service import ChartService

logger = logging.getLogger(__name__)


def _chart_cache_key(form_data: dict, chart_name: str, *extra) -> tuple:
    """Build a stable LRU cache key for a deep matplotlib chart.

    ``ticker + features_hash`` per the project plan: features include the
    horizon (start/end), frequency, and any chart-specific knobs (rolling
    window, risk threshold, target bias …) passed via ``extra``.
    """
    features = {
        "start": str(form_data.get("parsed_start_time")),
        "end": str(form_data.get("parsed_end_time")),
        "frequency": form_data.get("frequency"),
        "extra": extra,
    }
    return (form_data.get("ticker"), chart_name, ChartService.features_hash(features))


def _cached_or_build(key: tuple, builder):
    """Return a cached base64 chart for ``key`` or build → cache → return.

    ``builder`` is invoked only on cache miss. Unlike ``ChartService.generate_cached``
    this expects ``builder`` to already return a base64 string (the existing
    analyzer methods do the matplotlib→base64 step internally).
    """
    cached = ChartService.cache_get(key)
    if cached is not None:
        return cached
    result = builder()
    if isinstance(result, str) and result:
        ChartService.cache_put(key, result)
    return result

"""Chart rendering helpers + an LRU cache for matplotlib base64 outputs.

The frontend renders the lightweight time-series charts (market review,
regime strip) directly with Chart.js, so this module is the boundary for
the heavier matplotlib panels (deep statistics, projection, options chain
visualisations). Because those charts are deterministic functions of the
underlying data, we can safely memoise them in-process.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import io
import json
import logging
import threading
from collections import OrderedDict
from typing import Any, Callable, Hashable, Optional

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# ── LRU cache ─────────────────────────────────────────────────────
# Bounded so a long-running process can't grow unbounded. Each entry is
# a base64 PNG (~50–500 kB), so 64 entries ≈ 32 MB worst-case.
_CACHE_MAX_ENTRIES = 64
_cache: "OrderedDict[Hashable, str]" = OrderedDict()
_cache_lock = threading.Lock()
_cache_hits = 0
_cache_misses = 0


def _cache_get(key: Hashable) -> Optional[str]:
    global _cache_hits, _cache_misses
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            _cache_hits += 1
            return _cache[key]
        _cache_misses += 1
    return None


def _cache_put(key: Hashable, value: str) -> None:
    with _cache_lock:
        _cache[key] = value
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX_ENTRIES:
            evicted_key, _ = _cache.popitem(last=False)
            logger.debug("chart cache evicted key=%r", evicted_key)


def _cache_clear() -> None:
    global _cache_hits, _cache_misses
    with _cache_lock:
        _cache.clear()
        _cache_hits = 0
        _cache_misses = 0


def _cache_stats() -> dict[str, int]:
    with _cache_lock:
        return {
            "size": len(_cache),
            "max": _CACHE_MAX_ENTRIES,
            "hits": _cache_hits,
            "misses": _cache_misses,
        }


def features_hash(features: Any) -> str:
    """Stable short hash for arbitrary JSON-serialisable feature dicts.

    Used to build cache keys that namespace by the parameters that influence
    the chart (windows, thresholds, last bar date). Non-serialisable objects
    fall back to ``repr()`` so this is best-effort but never raises.
    """
    try:
        payload = json.dumps(features, sort_keys=True, default=repr)
    except (TypeError, ValueError):
        payload = repr(features)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def cached_chart(key_fn: Callable[..., Hashable]) -> Callable:
    """Decorator that memoises a function returning a base64 PNG string.

    ``key_fn(*args, **kwargs)`` must produce a hashable cache key — typically
    ``(ticker, features_hash(...))``. Cache hits skip the wrapped function.
    """

    def _decorator(func: Callable[..., Optional[str]]) -> Callable[..., Optional[str]]:
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                key = key_fn(*args, **kwargs)
            except Exception:
                logger.warning(
                    "cached_chart key_fn raised; bypassing cache for %s", func.__name__
                )
                return func(*args, **kwargs)
            cached = _cache_get(key)
            if cached is not None:
                logger.debug("chart cache HIT %s key=%r", func.__name__, key)
                return cached
            result = func(*args, **kwargs)
            if isinstance(result, str) and result:
                _cache_put(key, result)
                logger.debug("chart cache MISS→stored %s key=%r", func.__name__, key)
            return result

        return _wrapper

    return _decorator


class ChartService:
    """Service for generating charts and visualizations."""

    # Re-exposed so callers don't have to import the module-level helpers.
    cache_get = staticmethod(_cache_get)
    cache_put = staticmethod(_cache_put)
    cache_clear = staticmethod(_cache_clear)
    cache_stats = staticmethod(_cache_stats)
    features_hash = staticmethod(features_hash)

    @staticmethod
    def convert_plot_to_base64(fig):
        """Convert matplotlib figure to base64 string."""
        try:
            buffer = io.BytesIO()
            fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close(fig)
            return base64.b64encode(plot_data).decode()
        except Exception as e:
            logger.error(f"Error converting plot to base64: {e}")
            plt.close(fig)
            return None

    @staticmethod
    def generate_cached(key: Hashable, builder: Callable[[], Any]) -> Optional[str]:
        """Return cached base64 for ``key`` or build → encode → cache.

        ``builder`` is invoked only on cache miss and must return a matplotlib
        ``Figure`` (which this method will close after encoding).
        """
        cached = _cache_get(key)
        if cached is not None:
            logger.debug("chart cache HIT key=%r", key)
            return cached
        fig = builder()
        if fig is None:
            return None
        encoded = ChartService.convert_plot_to_base64(fig)
        if encoded:
            _cache_put(key, encoded)
            logger.debug("chart cache MISS→stored key=%r", key)
        return encoded

"""Regime domain services — market-regime labelling over VIX/SPY.

Package map:

- ``facade.py`` — :class:`RegimeService` (compute / persist / backfill / coverage)
- ``ops/``      — history bootstrap and ``regime_log`` persistence helpers
"""

from .facade import RegimeService

__all__ = ["RegimeService"]

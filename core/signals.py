"""Pure-OHLCV market signals — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.signals
  from core.signals import build_signals, hv_pct, rsi, bollinger_position

This module re-exports the canonical implementation from core.signals.*
to preserve existing import paths.
"""

from core.signals.bollinger import bollinger_position
from core.signals.bundle import _close, build_signals
from core.signals.hv import hv_context, hv_pct, hv_percentile, hv_vs_iv
from core.signals.rsi import rsi

__all__ = [
    "hv_pct",
    "hv_percentile",
    "hv_vs_iv",
    "hv_context",
    "rsi",
    "bollinger_position",
    "build_signals",
    "_close",
]

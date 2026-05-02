"""Market Analyzer — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.market.analyzer
  from core.market.analyzer import MarketAnalyzer

This module re-exports the canonical implementation from
``core.market.analyzer`` to preserve existing import paths during the
transition.
"""

from core.market.analyzer import MarketAnalyzer

__all__ = ["MarketAnalyzer"]

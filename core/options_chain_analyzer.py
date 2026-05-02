"""Options Chain Analyzer — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.options.chain.analyzer
  from core.options.chain.analyzer import (
      OptionsChainAnalyzer, liquidity_score, _dte, get_odds_with_vol_context,
  )

This module re-exports the canonical implementation from
``core.options.chain.analyzer`` to preserve existing import paths during
the transition.
"""

from core.options.chain.analyzer import (
    OptionsChainAnalyzer,
    _dte,
    get_odds_with_vol_context,
    liquidity_score,
)

__all__ = [
    "OptionsChainAnalyzer",
    "liquidity_score",
    "_dte",
    "get_odds_with_vol_context",
]

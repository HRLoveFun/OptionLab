"""Option-chain pure computation.

Domain:    Options Analysis — Chain Metrics
Context:
  - Stateless functions over DataFrame snapshots.
Contracts:
  - max_pain(calls, puts) -> float
  - expected_move(calls, puts, spot) -> float | None
  - skew_25d(puts, calls, spot) -> float | None
  - liquidity_score(...) -> tuple[str, str]
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.options.charts, services.options_chain_service
"""

from core.options.chain.analyzer import OptionsChainAnalyzer, _dte, get_odds_with_vol_context, liquidity_score
from core.options.chain.filters import filter_by_moneyness, filter_option_chain
from core.options.chain.metrics import expected_move, max_pain, skew_25d
from core.options.chain.term_structure import atm_iv_for_expiry, calc_implied_realized_vol, iv_percentile, iv_rank

__all__ = [
    "OptionsChainAnalyzer",
    "_dte",
    "filter_option_chain",
    "filter_by_moneyness",
    "get_odds_with_vol_context",
    "liquidity_score",
    "max_pain",
    "expected_move",
    "skew_25d",
    "atm_iv_for_expiry",
    "calc_implied_realized_vol",
    "iv_rank",
    "iv_percentile",
]

"""Option decision — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.decision
  from core.decision import (
      build_candidate_matrix, enrich_contract, compute_ev,
      filter_and_rank, select_dte_range, get_heuristic_notes,
      fetch_market_data, get_term_structure,
      calculate_iv_rank, calculate_iv_percentile,
  )

This module re-exports the canonical implementation from core.decision.*
to preserve existing import paths during the transition.
"""

from core.decision import (
    build_candidate_matrix,
    calculate_iv_percentile,
    calculate_iv_rank,
    compute_ev,
    enrich_contract,
    fetch_market_data,
    filter_and_rank,
    get_heuristic_notes,
    get_term_structure,
    select_dte_range,
)

__all__ = [
    "build_candidate_matrix",
    "calculate_iv_percentile",
    "calculate_iv_rank",
    "compute_ev",
    "enrich_contract",
    "fetch_market_data",
    "filter_and_rank",
    "get_heuristic_notes",
    "get_term_structure",
    "select_dte_range",
]

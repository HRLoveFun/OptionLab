"""Put option selection — quantitative decision process.

Dependency graph:
    models.py       # Candidate dataclass
    market_data.py  # IV rank / percentile / term structure
    candidate.py    # Build candidate matrix
    enrich.py       # Derived metrics
    ev.py           # Subjective expected value
    filter_rank.py  # Filter & rank
"""

from core.decision.candidate import build_candidate_matrix
from core.decision.enrich import enrich_contract
from core.decision.ev import compute_ev
from core.decision.filter_rank import filter_and_rank, get_heuristic_notes, select_dte_range
from core.decision.market_data import calculate_iv_percentile, calculate_iv_rank, fetch_market_data, get_term_structure

__all__ = [
    "fetch_market_data",
    "get_term_structure",
    "calculate_iv_rank",
    "calculate_iv_percentile",
    "build_candidate_matrix",
    "enrich_contract",
    "compute_ev",
    "select_dte_range",
    "filter_and_rank",
    "get_heuristic_notes",
]

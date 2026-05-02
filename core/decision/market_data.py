"""Market data helpers for option decision.

Domain:    Option Decision — Market Data
Contracts:
  - fetch_market_data(ticker) -> dict
  - get_term_structure(analyzer) -> dict[int, float]
  - calculate_iv_rank(term_structure) -> float | None
  - calculate_iv_percentile(term_structure) -> float | None
Dependencies UPWARD:
  - core.options.chain.term_structure
Dependencies DOWNWARD:
  - core.decision.candidate
"""

from __future__ import annotations

import logging

from core.options.chain.term_structure import atm_iv_for_expiry, iv_percentile, iv_rank
from core.options_chain_analyzer import OptionsChainAnalyzer

logger = logging.getLogger(__name__)


def _dte(expiry_str: str) -> int:
    import datetime as dt
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return max(0, (exp - today).days)


def get_term_structure(analyzer: OptionsChainAnalyzer) -> dict[int, float]:
    ts: dict[int, float] = {}
    for exp in analyzer.expiries:
        if exp not in analyzer.chain:
            continue
        puts = analyzer.chain[exp]["puts"]
        atm_iv = atm_iv_for_expiry(puts, analyzer.spot)
        if atm_iv is not None:
            ts[_dte(exp)] = atm_iv
    return ts


def calculate_iv_rank(term_structure: dict[int, float]) -> float | None:
    return iv_rank(term_structure)


def calculate_iv_percentile(term_structure: dict[int, float]) -> float | None:
    return iv_percentile(term_structure)


def fetch_market_data(ticker: str) -> dict:
    analyzer = OptionsChainAnalyzer(ticker)
    ts = get_term_structure(analyzer)
    return {
        "spot_price": analyzer.spot,
        "iv_rank": calculate_iv_rank(ts),
        "iv_pct": calculate_iv_percentile(ts),
        "term_structure": ts,
        "analyzer": analyzer,
    }

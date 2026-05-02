"""Option-chain filtering by DTE, moneyness, and contract count.

Domain:    Options Analysis — Chain Filtering
Context:
  - Stateless pure functions over option-chain records (dict/list).
Contracts:
  - filter_option_chain(result, max_dte, moneyness_low, moneyness_high, max_contracts) -> dict
  - filter_by_moneyness(chain_data, exps, spot, m_low, m_high) -> tuple[dict, int]
Dependencies UPWARD:
  - None (stdlib only)
Dependencies DOWNWARD:
  - app.py (Thin Adapter shim)
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _filter_expirations_by_dte(
    expirations: list[str], max_dte: int, today: dt.date | None = None
) -> list[str]:
    """Return expiration strings whose DTE is within [0, max_dte]."""
    today = today or dt.datetime.now().date()
    filtered: list[str] = []
    for exp in expirations:
        try:
            exp_date = dt.datetime.strptime(exp, "%Y-%m-%d").date()
            dte = (exp_date - today).days
            if 0 <= dte <= max_dte:
                filtered.append(exp)
        except (ValueError, TypeError):
            continue
    return filtered


def filter_by_moneyness(
    chain_data: dict[str, Any],
    exps: list[str],
    spot: float,
    m_low: float,
    m_high: float,
) -> tuple[dict[str, Any], int]:
    """Filter option chain by moneyness range.

    Returns ``(filtered_chain, total_contract_count)``.
    """
    filtered_chain: dict[str, Any] = {}
    total_count = 0
    low_strike = spot * m_low
    high_strike = spot * m_high

    for exp in exps:
        if exp not in chain_data:
            continue
        exp_data = chain_data[exp]

        filtered_calls = [
            r
            for r in exp_data.get("calls", [])
            if r.get("strike") and low_strike <= r["strike"] <= high_strike
        ]
        filtered_puts = [
            r
            for r in exp_data.get("puts", [])
            if r.get("strike") and low_strike <= r["strike"] <= high_strike
        ]

        if filtered_calls or filtered_puts:
            filtered_chain[exp] = {"calls": filtered_calls, "puts": filtered_puts}
            total_count += len(filtered_calls) + len(filtered_puts)

    return filtered_chain, total_count


def filter_option_chain(
    result: dict[str, Any],
    max_dte: int = 60,
    moneyness_low: float = 0.7,
    moneyness_high: float = 1.3,
    max_contracts: int = 1000,
) -> dict[str, Any]:
    """Filter option chain result by DTE, moneyness range, and total contract count.

    If total contracts exceed ``max_contracts`` after DTE + moneyness filtering,
    progressively narrow the moneyness range until count ≤ max_contracts.
    """
    spot = result.get("spot")
    chain = result.get("chain", {})
    expirations = result.get("expirations", [])

    today = dt.datetime.now().date()

    # Step 1: Filter expirations by DTE (always applies, does not need spot)
    filtered_exps = _filter_expirations_by_dte(expirations, max_dte, today)

    # If spot is missing, skip moneyness filter — just apply DTE filter
    if not spot or spot <= 0:
        filtered_chain = {exp: chain[exp] for exp in filtered_exps if exp in chain}
        final_exps = [exp for exp in filtered_exps if exp in filtered_chain]
        return {
            "expirations": final_exps,
            "chain": filtered_chain,
            "spot": spot,
        }

    # Step 2: Filter by moneyness range
    filtered_chain, total_count = filter_by_moneyness(
        chain, filtered_exps, spot, moneyness_low, moneyness_high
    )

    # Step 3: If over max_contracts, progressively narrow moneyness
    if total_count > max_contracts:
        step = 0.05
        m_low = moneyness_low
        m_high = moneyness_high
        while total_count > max_contracts and (m_high - m_low) > 0.1:
            m_low += step
            m_high -= step
            filtered_chain, total_count = filter_by_moneyness(
                chain, filtered_exps, spot, m_low, m_high
            )
            logger.info(
                "Narrowed moneyness to [%.2f, %.2f], contracts: %d",
                m_low,
                m_high,
                total_count,
            )

    # Build filtered expirations list (only those with data)
    final_exps = [exp for exp in filtered_exps if exp in filtered_chain]

    return {
        "expirations": final_exps,
        "chain": filtered_chain,
        "spot": spot,
    }

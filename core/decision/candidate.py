"""Candidate matrix builder.

Domain:    Option Decision — Candidate Matrix
Contracts:
  - build_candidate_matrix(analyzer, candidate_deltas, candidate_dtes) -> list[dict]
Dependencies UPWARD:
  - core.options.greeks.black_scholes
Dependencies DOWNWARD:
  - core.decision.enrich
"""

from __future__ import annotations

import logging

import numpy as np

from core.options.greeks.black_scholes import greeks_vectorized
from core.options_chain_analyzer import OptionsChainAnalyzer

logger = logging.getLogger(__name__)

CANDIDATE_DELTAS: list[float] = [-0.25, -0.40, -0.55, -0.70]
CANDIDATE_DTES: list[int] = [21, 45, 60, 90]
RISK_FREE_RATE: float = 0.05


def _dte(expiry_str: str) -> int:
    import datetime as dt
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, "%Y-%m-%d").date()
    return max(0, (exp - today).days)


def build_candidate_matrix(
    analyzer: OptionsChainAnalyzer,
    candidate_deltas: list[float] | None = None,
    candidate_dtes: list[int] | None = None,
) -> list[dict]:
    if candidate_deltas is None:
        candidate_deltas = CANDIDATE_DELTAS
    if candidate_dtes is None:
        candidate_dtes = CANDIDATE_DTES

    spot = analyzer.spot
    matrix: list[dict] = []
    for target_dte in candidate_dtes:
        closest_exp = None
        closest_diff = float("inf")
        for exp in analyzer.expiries:
            d = _dte(exp)
            diff = abs(d - target_dte)
            if diff < closest_diff:
                closest_diff = diff
                closest_exp = exp
        if closest_exp is None or closest_exp not in analyzer.chain:
            continue
        actual_dte = _dte(closest_exp)
        puts_df = analyzer.chain[closest_exp]["puts"]
        T = max(actual_dte, 1) / 365
        for target_delta in candidate_deltas:
            valid = puts_df.dropna(subset=["impliedVolatility", "strike"])
            valid = valid[valid["impliedVolatility"] > 0]
            if valid.empty:
                continue
            strikes = valid["strike"].values
            ivs = valid["impliedVolatility"].values
            g = greeks_vectorized(S=spot, K=strikes, T=T, r=RISK_FREE_RATE, sigma=ivs, option_type="put")
            deltas = np.asarray(g["delta"], dtype=float)
            diffs = np.abs(deltas - target_delta)
            best_idx = np.nanargmin(diffs)
            row = valid.iloc[best_idx]
            bid = float(row.get("bid", 0) or 0)
            ask = float(row.get("ask", 0) or 0)
            last_price = float(row.get("lastPrice", 0) or 0)
            mid = (bid + ask) / 2 if bid > 0 and ask > 0 else last_price
            iv = float(row["impliedVolatility"])
            strike = float(row["strike"])
            greeks = greeks_vectorized(S=spot, K=strike, T=T, r=RISK_FREE_RATE, sigma=iv, option_type="put")
            contract = {
                "strike": strike,
                "dte": actual_dte,
                "expiry": closest_exp,
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "last_price": round(last_price, 2),
                "mid_price": round(mid, 2),
                "delta": round(float(greeks["delta"]), 4),
                "gamma": round(float(greeks["gamma"]), 6),
                "theta": round(float(greeks["theta"]), 4),
                "vega": round(float(greeks["vega"]), 4),
                "iv": round(iv * 100, 2),
            }
            matrix.append(contract)
    return matrix

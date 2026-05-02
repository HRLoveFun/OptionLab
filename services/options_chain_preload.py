"""Option-chain preload logic for Position-module dropdowns.

Domain:    Services — Options Chain Preload
Context:
  - Fetches an option chain snapshot and converts DataFrames to plain records.
  - Maintains a short-lived in-memory cache (15 min TTL).
Contracts:
  - build_preload_payload(ticker) -> dict
  - expiry_df_to_records(df, expiry) -> list[dict]
Dependencies UPWARD:
  - core.options_chain_analyzer (OptionsChainAnalyzer, _dte)
Dependencies DOWNWARD:
  - routes/options.py
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import pandas as pd

from core.options_chain_analyzer import OptionsChainAnalyzer, _dte

logger = logging.getLogger(__name__)

# Module-level cache (mirrors legacy app.py cache)
_option_chain_cache: dict[str, Any] = {}
CACHE_TTL_MINUTES = 15


def expiry_df_to_records(df: pd.DataFrame | None, expiry: str) -> list[dict[str, Any]]:
    """Convert a single-expiry DataFrame into JSON-safe record dicts."""
    if df is None or df.empty:
        return []
    result: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        bid = float(row.get("bid", 0) or 0)
        ask = float(row.get("ask", 0) or 0)
        mid = (
            (bid + ask) / 2
            if bid > 0 and ask > 0
            else float(row.get("lastPrice", 0) or 0)
        )
        result.append(
            {
                "strike": float(row["strike"]),
                "bid": round(bid, 2),
                "ask": round(ask, 2),
                "mid": round(mid, 2),
                "last": round(float(row.get("lastPrice", 0) or 0), 2),
                "iv": round(float(row.get("impliedVolatility", 0) or 0), 4),
                "iv_pct": round(float(row.get("impliedVolatility", 0) or 0) * 100, 1),
                "oi": int(row.get("openInterest", 0) or 0),
                "volume": int(row.get("volume", 0) or 0),
                "dte": _dte(expiry),
            }
        )
    return result


def build_preload_payload(ticker: str) -> dict[str, Any]:
    """Build the option-chain preload payload for *ticker*.

    Returns a dict with keys:
        ticker, spot, expiries, chain
    """
    analyzer = OptionsChainAnalyzer(ticker)
    chain_out: dict[str, Any] = {}
    for exp in analyzer.expiries:
        if exp not in analyzer.chain:
            continue
        calls_df = analyzer.chain[exp]["calls"]
        puts_df = analyzer.chain[exp]["puts"]
        chain_out[exp] = {
            "calls": expiry_df_to_records(calls_df, exp),
            "puts": expiry_df_to_records(puts_df, exp),
        }

    return {
        "ticker": analyzer.ticker,
        "spot": round(analyzer.spot, 2),
        "expiries": analyzer.expiries,
        "chain": chain_out,
    }


def get_cached(ticker: str) -> dict[str, Any] | None:
    """Return cached payload if present and not expired."""
    cached = _option_chain_cache.get(ticker)
    if not cached:
        return None
    age = (dt.datetime.now() - cached["ts"]).total_seconds() / 60
    if age >= CACHE_TTL_MINUTES:
        return None
    return cached["data"]


def set_cached(ticker: str, payload: dict[str, Any]) -> None:
    """Store payload in the in-memory cache."""
    _option_chain_cache[ticker] = {"ts": dt.datetime.now(), "data": payload}


def clear_cache() -> None:
    """Clear the preload cache (useful in tests)."""
    _option_chain_cache.clear()

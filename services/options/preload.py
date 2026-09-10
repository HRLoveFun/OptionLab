"""Option-chain preload logic for Position-module dropdowns.

Domain:    Services — Options Chain Preload
Context:
  - Fetches an option chain snapshot and converts DataFrames to plain records.
  - Maintains a short-lived in-memory cache (15 min TTL).
Contracts:
  - build_preload_payload(ticker) -> dict
  - expiry_df_to_records(df, expiry) -> list[dict]
Dependencies UPWARD:
  - core._shared.dates (dte)
  - core.options.chain.analyzer (OptionsChainAnalyzer)
  - data_pipeline.providers.yf_client
Dependencies DOWNWARD:
  - routes/options.py
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import pandas as pd

from core._shared.dates import dte
from core.options.chain.analyzer import OptionsChainAnalyzer
from data_pipeline.providers.yf_client import fetch_option_chain

logger = logging.getLogger(__name__)

# Module-level cache (mirrors legacy app.py cache)
_option_chain_cache: dict[str, Any] = {}
CACHE_TTL_MINUTES = 15

# CONSTRAINT: bound on the cache key space. Each payload is a full option
# chain (up to MBs) and keys come from a public endpoint, so ticker
# enumeration would otherwise grow memory without limit (mirrors
# data_pipeline/_state.py::_cache_set).
_OPTION_CHAIN_CACHE_MAX = 128


def expiry_df_to_records(df: pd.DataFrame | None, expiry: str) -> list[dict[str, Any]]:
    """Convert a single-expiry DataFrame into JSON-safe record dicts."""
    if df is None or df.empty:
        return []
    result: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        bid = float(row.get("bid", 0) or 0)
        ask = float(row.get("ask", 0) or 0)
        mid = (bid + ask) / 2 if bid > 0 and ask > 0 else float(row.get("lastPrice", 0) or 0)
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
                "dte": dte(expiry),
            }
        )
    return result


def build_preload_payload(ticker: str) -> dict[str, Any]:
    """Build the option-chain preload payload for *ticker*.

    Returns a dict with keys:
        ticker, spot, expiries, chain
    """
    analyzer = OptionsChainAnalyzer(ticker, snapshot=fetch_option_chain(ticker))
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
        # Drop the expired entry: each payload is a full option chain (up to
        # MBs) and would otherwise linger until the same ticker is preloaded
        # again — unbounded growth on a long-lived process.
        _option_chain_cache.pop(ticker, None)
        return None
    return cached["data"]


def set_cached(ticker: str, payload: dict[str, Any]) -> None:
    """Store payload in the in-memory cache (bounded key space)."""
    if len(_option_chain_cache) >= _OPTION_CHAIN_CACHE_MAX:
        now = dt.datetime.now()
        expired = [
            k for k, v in _option_chain_cache.items() if (now - v["ts"]).total_seconds() / 60 >= CACHE_TTL_MINUTES
        ]
        for k in expired:
            del _option_chain_cache[k]
        while len(_option_chain_cache) >= _OPTION_CHAIN_CACHE_MAX:
            oldest = min(_option_chain_cache, key=lambda k: _option_chain_cache[k]["ts"])
            del _option_chain_cache[oldest]
    _option_chain_cache[ticker] = {"ts": dt.datetime.now(), "data": payload}


def clear_cache() -> None:
    """Clear the preload cache (useful in tests)."""
    _option_chain_cache.clear()

"""yfinance live-snapshot acquisition: spot price + option chain.

Domain:    Data Pipeline — yfinance Provider (Live Snapshots)
Context:
  - Live snapshots are the endpoints ADR 0004 says are never persisted: the
    current spot and the current option chain. They are also the largest
    yfinance surface, so they live in their own module and keep
    ``providers/yfinance_provider.py`` under the 400-line god-file cap — a split
    pre-registered in docs/architecture_review.md §2.
  - Batch B1 moved this code verbatim out of ``data_pipeline/yf_client.py`` (no
    behaviour change); only the canonical mapping at the bottom is new.
  - INVARIANT (keeps the import graph acyclic): this module must never import
    ``providers/yfinance_provider.py``.
Contracts:
  - ``fetch_spot(ticker)`` / ``fetch_spots_bulk(tickers)`` -> ``float`` / ``dict``.
  - ``fetch_option_chain(ticker)`` keeps the legacy payload contract
    (``ticker`` / ``spot`` / ``expiries`` / ``chain{expiry:{calls,puts}}``) for
    callers that still import it through the ``data_pipeline.providers.yf_client`` shim.
  - ``to_option_chain_snapshot(payload)`` -> canonical ``OptionChainSnapshot``.
Design rules:
  - CONSTRAINT: every public function calls ``yf_throttle()`` before each
    yfinance call — see docs/decisions/0005-token-bucket-throttle.md.
  - WHY (never raise on transient failure): callers receive ``None`` / an empty
    chain and decide how to surface the error. Raising here would cascade into
    unhandled 500s from several routes.
Dependencies UPWARD:
  - utils.network (throttle), data_pipeline.store.quality_log (via providers._log)
Dependencies DOWNWARD:
  - providers/base, providers/_log
"""

from __future__ import annotations

import logging
import math
import os
import threading
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd
import yfinance as yf

from data_pipeline.providers._log import _log_dq
from data_pipeline.providers.base import OptionChainSnapshot, OptionLeg
from utils.network import yf_throttle

logger = logging.getLogger(__name__)


# Standard option-chain numeric columns we always coerce.
_OPT_NUMERIC_COLS = (
    "strike",
    "bid",
    "ask",
    "lastPrice",
    "impliedVolatility",
    "openInterest",
    "volume",
)


# ---------------------------------------------------------------------------
# Spot price
# ---------------------------------------------------------------------------
def fetch_spot(ticker: str) -> float | None:
    """Return the current spot price for ``ticker`` or ``None`` on failure.

    Tries ``fast_info.last_price`` then ``regularMarketPrice`` then a tiny
    history fallback (1d) so we always have *something* for tickers whose
    fast_info is flaky.
    """
    try:
        yf_throttle()
        tk = yf.Ticker(ticker)
        fi = tk.fast_info
        price = getattr(fi, "last_price", None) or getattr(fi, "regularMarketPrice", None)
        if price is not None:
            return float(price)
    except Exception as exc:  # noqa: BLE001 — yfinance raises a wide variety
        logger.debug("fetch_spot fast_info failed for %s: %s", ticker, exc)

    try:
        yf_throttle()
        hist = yf.Ticker(ticker).history(period="1d")
        if not hist.empty and "Close" in hist.columns:
            return float(hist["Close"].iloc[-1])
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_spot history fallback failed for %s: %s", ticker, exc)
        _log_dq("yf_client.fetch_spot", "spot_unavailable", str(exc), ticker=ticker)
    return None


def fetch_spots_bulk(tickers: list[str]) -> dict[str, float]:
    """Return ``{ticker: spot}`` for every ticker that resolved successfully.

    Sequential (one yfinance call per ticker) — the global token bucket in
    ``yf_throttle`` already paces us. Failures are logged and omitted from
    the result; callers must handle missing keys.
    """
    out: dict[str, float] = {}
    for t in tickers:
        spot = fetch_spot(t)
        if spot is not None:
            out[t] = spot
    return out


# ---------------------------------------------------------------------------
# Option chain
# ---------------------------------------------------------------------------
def fetch_option_chain(ticker: str) -> dict[str, Any]:
    """Fetch a full option-chain snapshot.

    Returns
    -------
    dict
        Shape::

            {
                "ticker": str,
                "spot": float | None,
                "expiries": list[str],          # YYYY-MM-DD strings
                "chain": {
                    expiry_str: {
                        "calls": pd.DataFrame,
                        "puts":  pd.DataFrame,
                    }
                }
            }

        Numeric columns on the DataFrames are coerced via ``pd.to_numeric``.
        ``openInterest`` / ``volume`` NaNs are filled with 0.

        On total failure (no expiries returned), ``expiries`` and ``chain``
        are empty but ``spot`` may still be populated.
    """
    spot = fetch_spot(ticker)
    expiries: list[str] = []
    chain: dict[str, dict[str, pd.DataFrame]] = {}

    try:
        yf_throttle()
        tk = yf.Ticker(ticker)
        expiries = list(tk.options or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("fetch_option_chain: failed to list expiries for %s: %s", ticker, exc)
        _log_dq("yf_client.fetch_option_chain", "expiries_unavailable", str(exc), ticker=ticker)
        return {"ticker": ticker, "spot": spot, "expiries": [], "chain": {}}

    # WHY: track consecutive empty responses. Yahoo's 429 / curl_cffi's
    # empty-body behaviour applies to the WHOLE option-chain endpoint
    # uniformly — once one expiry returns None, the rest will too. Bail
    # after a few empties to avoid burning the throttle on guaranteed misses.
    EMPTY_FAIL_FAST = 3
    # WHY (concurrency): option_chain HTTP latency (~2s) typically exceeds the
    # 1.5s throttle gap, so overlapping HTTP across a small worker pool
    # reduces total wall time even though throttle still serialises call
    # *starts*. Cap at 2 by default — higher counts give diminishing returns
    # and risk tripping Yahoo's burst detection. CONSTRAINT: every worker
    # MUST call yf_throttle() before each yfinance call (ADR 0005).
    max_workers = max(1, int(os.environ.get("YF_OPTION_CHAIN_WORKERS", "2")))
    if max_workers == 1 or len(expiries) <= 1:
        return _fetch_option_chain_serial(ticker, spot, expiries, EMPTY_FAIL_FAST)

    consecutive_empty_lock = threading.Lock()
    consecutive_empty = {"n": 0, "abort": False}

    def _fetch_one(exp: str):
        if consecutive_empty["abort"]:
            return exp, None
        try:
            yf_throttle()
            # WHY (per-thread Ticker): yfinance.Ticker is not documented as
            # thread-safe; create a fresh instance per worker to avoid
            # hidden shared state in tk._options_data.
            opt = yf.Ticker(ticker).option_chain(exp)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_option_chain: %s exp=%s failed: %s", ticker, exp, exc)
            # Exceptions (e.g. 429s surfacing as raised errors) count toward
            # the fail-fast budget too, otherwise an error-storm burns the
            # throttle across every expiry instead of aborting early.
            with consecutive_empty_lock:
                consecutive_empty["n"] += 1
                if consecutive_empty["n"] >= EMPTY_FAIL_FAST:
                    consecutive_empty["abort"] = True
            return exp, "error"
        if opt is None or opt.calls is None or opt.puts is None:
            with consecutive_empty_lock:
                consecutive_empty["n"] += 1
                if consecutive_empty["n"] == 1:
                    logger.warning("fetch_option_chain: %s exp=%s returned no data (rate-limited?)", ticker, exp)
                if consecutive_empty["n"] >= EMPTY_FAIL_FAST:
                    consecutive_empty["abort"] = True
            return exp, None
        with consecutive_empty_lock:
            consecutive_empty["n"] = 0
        return exp, _coerce_chain_side_payload(opt)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_one, exp): exp for exp in expiries}
        for future in as_completed(futures):
            exp, payload = future.result()
            if isinstance(payload, dict):
                chain[exp] = payload

    # WHY: preserve the user-meaningful order (front-month first) from the
    # original ``expiries`` list — as_completed yields in completion order.
    ordered_chain = {exp: chain[exp] for exp in expiries if exp in chain}
    return {"ticker": ticker, "spot": spot, "expiries": list(ordered_chain.keys()), "chain": ordered_chain}


def _coerce_chain_side_payload(opt: Any) -> dict[str, pd.DataFrame]:
    """Coerce one ``opt.calls`` / ``opt.puts`` pair: numeric columns, OI/volume NaN→0."""
    calls = opt.calls.copy()
    puts = opt.puts.copy()
    for col in _OPT_NUMERIC_COLS:
        if col in calls.columns:
            calls[col] = pd.to_numeric(calls[col], errors="coerce")
        if col in puts.columns:
            puts[col] = pd.to_numeric(puts[col], errors="coerce")
    for col in ("openInterest", "volume"):
        if col in calls.columns:
            calls[col] = calls[col].fillna(0)
        if col in puts.columns:
            puts[col] = puts[col].fillna(0)
    return {"calls": calls, "puts": puts}


def _fetch_option_chain_serial(
    ticker: str, spot: float | None, expiries: list[str], empty_fail_fast: int
) -> dict[str, Any]:
    """Sequential fallback path used when YF_OPTION_CHAIN_WORKERS=1 or only
    one expiry exists. Behaviourally identical to the pre-concurrency loop.
    """
    chain: dict[str, dict[str, pd.DataFrame]] = {}
    consecutive_empty = 0
    tk = yf.Ticker(ticker)
    for exp in expiries:
        try:
            yf_throttle()
            opt = tk.option_chain(exp)
            if opt is None or opt.calls is None or opt.puts is None:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    logger.warning("fetch_option_chain: %s exp=%s returned no data (rate-limited?)", ticker, exp)
                if consecutive_empty >= empty_fail_fast:
                    logger.warning(
                        "fetch_option_chain: %s aborting after %d empty expiries (likely rate-limited)",
                        ticker,
                        consecutive_empty,
                    )
                    break
                continue
            consecutive_empty = 0
            chain[exp] = _coerce_chain_side_payload(opt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_option_chain: %s exp=%s failed: %s", ticker, exp, exc)
            continue

    return {"ticker": ticker, "spot": spot, "expiries": list(chain.keys()), "chain": chain}


# ---------------------------------------------------------------------------
# Canonical mapping
# ---------------------------------------------------------------------------
def _opt_float(value: Any) -> float | None:
    """Coerce a yfinance cell to float, mapping NaN/inf/None to ``None``."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) or math.isinf(out) else out


def _leg_from_row(row: pd.Series) -> OptionLeg:
    """Map one yfinance chain row onto a canonical ``OptionLeg``."""
    return OptionLeg(
        strike=_opt_float(row.get("strike")) or 0.0,
        bid=_opt_float(row.get("bid")),
        ask=_opt_float(row.get("ask")),
        last=_opt_float(row.get("lastPrice")),
        iv=_opt_float(row.get("impliedVolatility")),
        open_interest=_opt_float(row.get("openInterest")),
        volume=_opt_float(row.get("volume")),
    )


def to_option_chain_snapshot(payload: Mapping[str, Any], *, provider: str = "yfinance") -> OptionChainSnapshot:
    """Map a legacy ``fetch_option_chain`` payload onto the canonical schema.

    INVARIANT: no ``inTheMoney`` column is carried over (derivable), and ``iv``
    stays a decimal — see ``providers/base.py`` for the unit conventions.
    """
    expiries = tuple(payload.get("expiries") or ())
    raw_chain = payload.get("chain") or {}
    chain: dict[str, dict[str, tuple[OptionLeg, ...]]] = {}
    for expiry in expiries:
        sides = raw_chain.get(expiry)
        if not sides:
            continue
        chain[expiry] = {
            side: tuple(_leg_from_row(row) for _, row in sides[side].iterrows())
            for side in ("calls", "puts")
            if side in sides
        }
    return OptionChainSnapshot(
        provider=provider,
        symbol=str(payload.get("ticker") or ""),
        spot=payload.get("spot"),
        expiries=expiries,
        chain=chain,
    )

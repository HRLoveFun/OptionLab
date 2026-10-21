"""Ticker-mode market inputs for the Position Simulator (``POST /api/optsim``).

Domain:    Option Simulation — service layer (ticker mode)
Context:
  - With ``market == "ticker"`` the position is priced on the header ticker: its
    listed market (spot, expiries, strikes, quotes) from the option-chain preload
    cache (15-minute TTL, fetched on a miss; an empty chain is not cached), the
    risk-free rate from the 13-week T-bill (``^IRX``), a dividend yield of 0, and
    the margin class picked from the underlying's instrument type
    (``core.optsim.margin.margin_class``). The user settled the last three on
    2026-10-21 (ADR 0013).
  - When ``^IRX`` is unavailable the request's typed rate stands in, and
    ``rate_source`` says so; an unknown instrument type gets the most
    conservative margin class (equity).
Contracts:
  - TickerMarket(listed, rate, rate_source, rate_as_of, product, instrument_type, div_yield)
  - ticker_market(raw_ticker, fallback_rate) -> TickerMarket
Dependencies UPWARD:
  - core.optsim, services.options.preload, services.market.reference_data,
    utils.api_errors, utils.ticker_utils
Dependencies DOWNWARD:
  - services.options.optsim, tests
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.optsim import listed_market, margin_class
from core.optsim.market import ListedMarket
from services.market import reference_data
from services.options import preload
from utils.api_errors import ApiError
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

# CONSTRAINT: longer than any Yahoo or futu symbol; keeps junk out of the chain cache keys.
MAX_TICKER_LEN = 20


@dataclass(frozen=True)
class TickerMarket:
    """Everything ticker mode prices on besides the legs."""

    listed: ListedMarket
    rate: float  # decimal
    rate_source: str  # "^IRX", or "input" when the T-bill quote was unavailable
    rate_as_of: str | None
    product: str  # a core.optsim.margin.PRODUCTS key
    instrument_type: str | None
    div_yield: float = 0.0


def _listed(raw: Any) -> ListedMarket:
    """The ticker's listed market, from the option-chain preload cache (fetched on a miss)."""
    ticker = str(raw or "").strip().upper()
    if not ticker:
        raise ApiError("ticker mode needs a ticker", code="ticker_required")
    if len(ticker) > MAX_TICKER_LEN or any(c.isspace() for c in ticker):
        raise ApiError("ticker is not a valid symbol", code="invalid_ticker", details={"value": raw})
    try:
        ticker, _ = normalize_ticker(ticker)
    except ValueError:
        pass
    snap = preload.get_cached(ticker)
    if snap is None:
        try:
            snap = preload.build_preload_payload(ticker)
        except Exception as exc:  # noqa: BLE001 — the provider fails in many ways; all mean "no chain"
            logger.warning("optsim: option chain for %s unavailable: %s", ticker, exc)
            raise ApiError(
                f"could not load the option chain for {ticker}", code="chain_unavailable", status=502
            ) from None
        # WHY: an empty chain is usually a transient Yahoo failure; caching it would pin the miss for 15 minutes.
        if snap.get("chain"):
            preload.set_cached(ticker, snap)
    try:
        listed = listed_market(ticker, snap.get("spot"), snap.get("chain") or {}, as_of=snap.get("fetched_at"))
    except ValueError:
        raise ApiError(f"no spot price for {ticker}", code="chain_unavailable", status=502) from None
    if not listed.expiries:
        raise ApiError(f"{ticker} has no listed options a day or more out", code="chain_unavailable", status=502)
    return listed


def ticker_market(raw_ticker: Any, fallback_rate: float) -> TickerMarket:
    """Listed market, risk-free rate, dividend yield and margin class for ``raw_ticker``.

    ``fallback_rate`` (a decimal: the request's typed rate) is used only when the
    T-bill quote is unavailable. Raises ``ApiError`` when the chain is.
    """
    listed = _listed(raw_ticker)
    kind = reference_data.instrument_type(listed.ticker)
    quote = reference_data.risk_free_rate()
    return TickerMarket(
        listed=listed,
        rate=quote.rate if quote else fallback_rate,
        rate_source=quote.symbol if quote else "input",
        rate_as_of=quote.as_of if quote else None,
        product=margin_class(listed.ticker, kind),
        instrument_type=kind,
    )

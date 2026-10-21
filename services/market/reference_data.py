"""Slow-moving market reference data, cached in process: instrument type and the risk-free rate.

Domain:    Services — Market Reference Data
Context:
  - ``instrument_type(symbol)`` asks the provider seam whether an underlying is an
    index, an ETF or a stock. A symbol rarely changes type, so an answer is kept for
    a day; a failure (``None``) is not kept, so the next request asks again.
  - ``risk_free_rate()`` is the 13-week Treasury bill yield: yfinance's ``^IRX``,
    which Yahoo quotes in percent (4.07 means 4.07%), kept for 15 minutes like the
    option-chain preload cache. It is a discount yield used as-is: a few basis
    points below the continuously compounded rate the pricing models assume.
    ``None`` when the quote is missing or outside -5%..50% (the range the web form
    accepts), so callers fall back to their own rate.
  - Callers today: the Position Simulator's ticker mode (services/options/optsim.py).
Contracts:
  - instrument_type(symbol) -> str | None   ("index" | "etf" | "equity" | "other")
  - risk_free_rate() -> RiskFreeQuote | None  (rate as a decimal, symbol, as_of)
  - clear_cache() -> None
Dependencies UPWARD:
  - data_pipeline.providers
Dependencies DOWNWARD:
  - services.options.optsim_ticker, tests
"""

from __future__ import annotations

import datetime as dt
import logging
import math
from dataclasses import dataclass

from data_pipeline.providers import get_provider

logger = logging.getLogger(__name__)

# DOMAIN: the 13-week (3-month) Treasury bill yield on Yahoo, quoted in percent.
RISK_FREE_SYMBOL = "^IRX"
# CONSTRAINT: the same bounds POST /api/optsim puts on a typed rate, in percent.
_RATE_BOUNDS_PCT = (-5.0, 50.0)
# CONSTRAINT: a T-bill quote moves slowly; 15 minutes matches the option-chain preload cache.
RISK_FREE_TTL = dt.timedelta(minutes=15)
# CONSTRAINT: an instrument's type practically never changes; one lookup a day per symbol.
INSTRUMENT_TYPE_TTL = dt.timedelta(days=1)
# CONSTRAINT: symbols come from a public endpoint; bound the cache like the preload cache.
_TYPE_CACHE_MAX = 256

_types: dict[str, tuple[dt.datetime, str]] = {}
_rate: dict[str, tuple[dt.datetime, RiskFreeQuote]] = {}


@dataclass(frozen=True)
class RiskFreeQuote:
    """The risk-free rate as a decimal, where it came from and when it was read (UTC, ISO 8601)."""

    rate: float
    symbol: str
    as_of: str


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def instrument_type(symbol: str) -> str | None:
    """``index`` / ``etf`` / ``equity`` / ``other`` for ``symbol``; ``None`` when the provider cannot say."""
    key = str(symbol or "").strip().upper()
    if not key:
        return None
    hit = _types.get(key)
    if hit is not None and _now() - hit[0] < INSTRUMENT_TYPE_TTL:
        return hit[1]
    try:
        kind = get_provider().instrument_type(key)
    except Exception as exc:  # noqa: BLE001 — a lookup is best-effort; the caller has a fallback
        logger.warning("instrument type for %s unavailable: %s", key, exc)
        return None
    if kind is None:
        return None
    if len(_types) >= _TYPE_CACHE_MAX:
        _types.pop(min(_types, key=lambda k: _types[k][0]))
    _types[key] = (_now(), kind)
    return kind


def risk_free_rate() -> RiskFreeQuote | None:
    """The 13-week T-bill yield (``^IRX``) as a decimal; ``None`` when missing or implausible."""
    hit = _rate.get(RISK_FREE_SYMBOL)
    if hit is not None and _now() - hit[0] < RISK_FREE_TTL:
        return hit[1]
    try:
        pct = get_provider().spot(RISK_FREE_SYMBOL)
    except Exception as exc:  # noqa: BLE001 — a lookup is best-effort; the caller has a fallback
        logger.warning("risk-free rate (%s) unavailable: %s", RISK_FREE_SYMBOL, exc)
        return None
    lo, hi = _RATE_BOUNDS_PCT
    if pct is None or not math.isfinite(pct) or not lo <= pct <= hi:
        logger.warning("risk-free rate (%s) unusable: %r", RISK_FREE_SYMBOL, pct)
        return None
    now = _now()
    quote = RiskFreeQuote(rate=pct / 100.0, symbol=RISK_FREE_SYMBOL, as_of=now.isoformat(timespec="seconds"))
    _rate[RISK_FREE_SYMBOL] = (now, quote)
    return quote


def clear_cache() -> None:
    """Forget every cached answer (tests)."""
    _types.clear()
    _rate.clear()

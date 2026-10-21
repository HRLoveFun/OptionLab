"""Listed option market for the optsim ticker mode.

Domain:    Option Simulation — Listed Market
Context:
  - Reshapes an option-chain snapshot (spot, expiries, per-expiry call/put rows
    with strike, bid, ask and vendor IV) into what the ticker mode prices legs
    on: listed expiries and strikes, two-sided quotes and one IV curve per expiry.
    Pure: services/options/optsim.py fetches the snapshot.
  - A quote has a mid only when both sides are quoted (bid > 0 and ask >= bid).
    Off-hours chains carry zero bids and asks, and a last trade can be days old,
    so neither stands in for a mid.
  - The IV curve of an expiry takes the out-of-the-money side at each listed
    strike (puts below spot, calls at or above): the IV implied by the mid
    (European model, the caller's r and q), else the vendor IV, each kept only
    inside [IV_MIN, IV_MAX]; the other side fills strikes the OTM side cannot.
    Linear in strike between points, flat beyond the ends. |Δ| targets are
    solved on it; a leg prices at its own contract's mid when that has one.
Contracts:
  - Quote(strike, bid, ask, iv); Quote.mid -> float | None
  - ListedExpiry(expiry, dte, calls, puts); ListedMarket(ticker, spot, expiries, as_of)
  - listed_market(ticker, spot, chain, *, today=None, as_of=None) -> ListedMarket
  - nearest_expiry(listed, dte) -> ListedExpiry
  - nearest_quote(quotes, strike) -> Quote
  - IvCurve(strikes, ivs).iv(strike, spot=None) -> float   (the Smile.iv signature)
  - iv_curve(expiry, market) -> IvCurve
  - leg_iv(kind, quote, expiry, market, curve, style, steps) -> (iv, source)
Dependencies UPWARD:
  - numpy, core.optsim.models, core.optsim.pricing
Dependencies DOWNWARD:
  - services.options.optsim, tests
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from core.optsim.models import Market
from core.optsim.pricing import DEFAULT_STEPS, IV_MAX, IV_MIN, implied_vol


def _positive(value) -> float | None:
    """A finite, strictly positive float, else ``None`` (zero quotes mean "not quoted")."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) and out > 0 else None


@dataclass(frozen=True)
class Quote:
    """One listed contract: strike, bid / ask (``None`` when not quoted) and the vendor IV."""

    strike: float
    bid: float | None = None
    ask: float | None = None
    iv: float | None = None

    @property
    def mid(self) -> float | None:
        """Mid of a two-sided quote, else ``None``."""
        if self.bid is None or self.ask is None or self.ask < self.bid:
            return None
        return 0.5 * (self.bid + self.ask)


@dataclass(frozen=True)
class ListedExpiry:
    """The listed calls and puts of one expiry, sorted by strike."""

    expiry: str  # YYYY-MM-DD
    dte: int
    calls: tuple[Quote, ...]
    puts: tuple[Quote, ...]

    def quotes(self, kind: str) -> tuple[Quote, ...]:
        return self.calls if kind == "call" else self.puts


@dataclass(frozen=True)
class ListedMarket:
    """Spot and the listed expiries of one underlying, as of one chain snapshot."""

    ticker: str
    spot: float
    expiries: tuple[ListedExpiry, ...]
    as_of: str | None = None


def _quotes(rows) -> tuple[Quote, ...]:
    by_strike: dict[float, Quote] = {}
    for row in rows or ():
        strike = _positive(row.get("strike"))
        if strike is None or strike in by_strike:
            continue
        by_strike[strike] = Quote(
            strike, _positive(row.get("bid")), _positive(row.get("ask")), _positive(row.get("iv"))
        )
    return tuple(by_strike[k] for k in sorted(by_strike))


def listed_market(
    ticker: str,
    spot,
    chain: Mapping[str, Mapping[str, Sequence[Mapping]]],
    *,
    today: dt.date | None = None,
    as_of: str | None = None,
) -> ListedMarket:
    """Parse ``{expiry: {"calls": rows, "puts": rows}}``; each row has strike, bid, ask and iv (decimal).

    Expiries keep date order from one calendar day out (``today`` defaults to the
    local date); an expiry without a single listed strike is dropped.
    """
    spot_ = _positive(spot)
    if spot_ is None:
        raise ValueError("the chain has no spot price")
    today = today or dt.date.today()
    expiries = []
    for expiry in sorted(chain or {}):
        try:
            days = (dt.date.fromisoformat(str(expiry)[:10]) - today).days
        except ValueError:
            continue
        sides = chain[expiry] or {}
        calls, puts = _quotes(sides.get("calls")), _quotes(sides.get("puts"))
        if days >= 1 and (calls or puts):
            expiries.append(ListedExpiry(str(expiry)[:10], days, calls, puts))
    return ListedMarket(str(ticker), spot_, tuple(expiries), as_of)


def nearest_expiry(listed: ListedMarket, dte: int) -> ListedExpiry:
    """The listed expiry closest to ``dte`` days out; a tie goes to the later one."""
    if not listed.expiries:
        raise ValueError("no listed expiry at least one day out")
    return min(listed.expiries, key=lambda e: (abs(e.dte - dte), -e.dte))


def nearest_quote(quotes: Sequence[Quote], strike: float) -> Quote:
    """The listed contract whose strike is closest to ``strike``; a tie goes to the lower strike."""
    if not quotes:
        raise ValueError("no listed strikes")
    return min(quotes, key=lambda q: (abs(q.strike - strike), q.strike))


@dataclass(frozen=True)
class IvCurve:
    """IV over strike for one expiry: linear between listed points, flat beyond the ends."""

    strikes: np.ndarray
    ivs: np.ndarray

    def iv(self, strike, spot=None):
        """IV at ``strike``; ``spot`` is accepted so the curve can stand in for a ``Smile``."""
        out = np.interp(strike, self.strikes, self.ivs)
        return float(out) if np.ndim(out) == 0 else out


def _side_ivs(kind: str, quotes: Sequence[Quote], expiry: ListedExpiry, market: Market) -> dict[float, float]:
    """Usable IV per strike on one side: implied by the mid (European), else the vendor IV."""
    if not quotes:
        return {}
    strikes = np.array([q.strike for q in quotes])
    mids = np.array([np.nan if q.mid is None else q.mid for q in quotes])
    implied = implied_vol(kind, mids, market.spot, strikes, expiry.dte / 365.0, market.rate, market.div_yield)
    out = {}
    for quote, from_mid in zip(quotes, implied, strict=True):
        iv = float(from_mid) if np.isfinite(from_mid) else quote.iv
        if iv is not None and IV_MIN <= iv <= IV_MAX:
            out[quote.strike] = iv
    return out


def iv_curve(expiry: ListedExpiry, market: Market) -> IvCurve:
    """The expiry's IV curve, out-of-the-money side first (see the module notes)."""
    calls = _side_ivs("call", expiry.calls, expiry, market)
    puts = _side_ivs("put", expiry.puts, expiry, market)
    points = {}
    for strike in sorted(set(calls) | set(puts)):
        otm, other = (puts, calls) if strike < market.spot else (calls, puts)
        iv = otm.get(strike, other.get(strike))
        if iv is not None:
            points[strike] = iv
    if not points:
        raise ValueError(f"no usable implied volatility on {expiry.expiry}")
    strikes = np.array(sorted(points))
    return IvCurve(strikes, np.array([points[k] for k in strikes]))


def leg_iv(
    kind: str,
    quote: Quote,
    expiry: ListedExpiry,
    market: Market,
    curve: IvCurve,
    style: str = "european",
    steps: int = DEFAULT_STEPS,
) -> tuple[float, str]:
    """IV a listed leg prices at: implied by its own mid in ``style`` ("mid"), else the curve ("curve")."""
    if quote.mid is not None:
        iv = float(
            implied_vol(
                kind,
                quote.mid,
                market.spot,
                quote.strike,
                expiry.dte / 365.0,
                market.rate,
                market.div_yield,
                style,
                steps,
            )
        )
        if math.isfinite(iv):
            return iv, "mid"
    return float(curve.iv(quote.strike)), "curve"

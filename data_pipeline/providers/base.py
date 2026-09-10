"""Provider seam: the canonical internal schema and the acquisition protocol.

Domain:    Data Pipeline — Acquisition Seam
Context:
  - ADR 0011 splits acquisition from processing/serving: a *provider* owns every
    call to an external market-data API and maps that API's fields onto one
    canonical internal schema, so nothing downstream of acquisition sees a
    vendor-specific shape.
  - yfinance is the only implementation today (ADR 0002, as amended by 0011).
    This protocol is deliberately sketched against *two* field maps — yfinance
    and the archived futu integration
    (``archive/futu_integration/field_mapping.md``) — so it does not bake in
    yfinance-isms. That comparison is the §8 Q5 decision gate for batch B1 and is
    recorded in ADR 0011.
Contracts:
  - ``MarketDataProvider``: the minimal acquisition surface.
  - ``CANONICAL_BAR_COLUMNS`` / ``CANONICAL_LEG_COLUMNS``: canonical frame columns.
  - ``CanonicalBar`` / ``OptionLeg`` / ``OptionChainSnapshot``: canonical records.
Unit conventions — INVARIANT for every provider implementation:
  - ``iv`` is a **decimal** (0.2436 means 24.36 %). futu reports percent,
    yfinance reports decimal; the provider normalises at its own boundary.
  - ``bid`` / ``ask`` may be ``None``. futu's ``get_stock_quote`` exposes no
    bid/ask without an ORDER_BOOK subscription, so "absent" must be expressible —
    a provider must never invent a quote.
  - ``inTheMoney`` is intentionally **not** canonical: it is derivable from
    ``(strike, spot)`` and futu has no equivalent column.
  - OHLCV values are plain floats; ``volume`` / ``open_interest`` are
    non-negative counts.
Dependencies UPWARD:
  - (none — no external SDK is imported here; implementations sit beside it)
Dependencies DOWNWARD:
  - providers/yfinance_provider.py, providers/yf_option_chain.py,
    providers/_registry.py
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import pandas as pd

# INVARIANT: the column names (and order) of the frame ``history()`` returns,
# indexed by a tz-naive DatetimeIndex of trading days.
CANONICAL_BAR_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "adj_close", "volume")

# INVARIANT: the fields every canonical option leg exposes. See the unit
# conventions in the module docstring for the semantics of ``iv`` / ``bid``.
CANONICAL_LEG_COLUMNS: tuple[str, ...] = (
    "strike",
    "bid",
    "ask",
    "last",
    "iv",
    "open_interest",
    "volume",
)


@dataclass(frozen=True)
class CanonicalBar:
    """One daily OHLCV bar in the canonical schema."""

    provider: str
    symbol: str
    date: dt.date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adj_close: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class OptionLeg:
    """One option contract quote in the canonical schema."""

    strike: float
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    iv: float | None = None
    open_interest: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class OptionChainSnapshot:
    """A live option-chain snapshot. Never persisted — see ADR 0004."""

    provider: str
    symbol: str
    spot: float | None
    expiries: tuple[str, ...] = ()
    chain: Mapping[str, Mapping[str, tuple[OptionLeg, ...]]] = field(default_factory=dict)

    def legs(self, expiry: str, side: str) -> tuple[OptionLeg, ...]:
        """Return the legs for ``expiry`` and ``side`` (``calls`` | ``puts``)."""
        return tuple(self.chain.get(expiry, {}).get(side, ()))


@runtime_checkable
class MarketDataProvider(Protocol):
    """The acquisition surface a data provider must offer.

    An implementation owns (a) every call to its external API and (b) the mapping
    from that API's fields onto the canonical schema above. Callers resolve an
    implementation through ``providers.get_provider()`` rather than importing a
    concrete provider, so adding a vendor is a localised change (ADR 0011).
    """

    @property
    def name(self) -> str:
        """Stable provider id, also stored in the ``provider`` column."""
        ...

    def history(self, symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        """Daily bars for ``[start, end]`` as a ``CANONICAL_BAR_COLUMNS`` frame."""
        ...

    def close_panel(
        self,
        symbols: list[str],
        *,
        start: dt.date | str | None = None,
        end: dt.date | str | None = None,
        period: str | None = None,
    ) -> pd.DataFrame:
        """Wide Close-price frame: index = date, columns = symbols."""
        ...

    def spot(self, symbol: str) -> float | None:
        """Latest traded price for ``symbol``, or ``None`` when unavailable."""
        ...

    def option_chain(self, symbol: str) -> OptionChainSnapshot:
        """Live chain snapshot (spot + expiries + canonical legs)."""
        ...


def bars_to_frame(bars: Iterable[CanonicalBar]) -> pd.DataFrame:
    """Render ``CanonicalBar`` records as a ``CANONICAL_BAR_COLUMNS`` DataFrame."""
    rows = list(bars)
    if not rows:
        return pd.DataFrame(columns=list(CANONICAL_BAR_COLUMNS))
    frame = pd.DataFrame(
        [{col: getattr(bar, col) for col in CANONICAL_BAR_COLUMNS} for bar in rows],
        index=pd.DatetimeIndex([pd.Timestamp(bar.date) for bar in rows]),
    )
    return frame.sort_index()

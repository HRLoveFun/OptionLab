"""Provider registry: name → MarketDataProvider instance.

Domain:    Data Pipeline — Provider Selection
Context:
  - ADR 0011: acquisition is selected by name, so a second vendor is one new
    provider module plus one line in ``_FACTORIES`` — no caller changes.
    yfinance stays the only implementation until a second provider is actually
    needed (the seam is the deliverable, not the vendor).
  - Selection order: explicit ``name`` argument → ``MARKET_DATA_PROVIDER`` env
    var → ``DEFAULT_PROVIDER``.
Contracts:
  - ``get_provider(name=None) -> MarketDataProvider``
  - ``available_providers() -> tuple[str, ...]``
Dependencies UPWARD:
  - (none)
Dependencies DOWNWARD:
  - providers/base, providers/yfinance_provider
"""

from __future__ import annotations

import os
from collections.abc import Callable

from data_pipeline.providers.base import MarketDataProvider
from data_pipeline.providers.yfinance_provider import YFinanceProvider

PROVIDER_ENV_VAR = "MARKET_DATA_PROVIDER"
DEFAULT_PROVIDER = "yfinance"

_FACTORIES: dict[str, Callable[[], MarketDataProvider]] = {
    DEFAULT_PROVIDER: YFinanceProvider,
}
# WHY (cache): providers are stateless, but re-reading env/config on every fetch
# is pointless. Instances are keyed by resolved name.
_INSTANCES: dict[str, MarketDataProvider] = {}


def available_providers() -> tuple[str, ...]:
    """Return the registered provider names, sorted."""
    return tuple(sorted(_FACTORIES))


def get_provider(name: str | None = None) -> MarketDataProvider:
    """Return the (cached) provider instance for ``name``.

    Raises ``ValueError`` for an unknown name rather than silently falling back
    to yfinance — a typo in ``MARKET_DATA_PROVIDER`` must fail loudly.
    """
    resolved = name or os.environ.get(PROVIDER_ENV_VAR) or DEFAULT_PROVIDER
    if resolved not in _FACTORIES:
        raise ValueError(f"unknown data provider {resolved!r}; available: {list(available_providers())}")
    if resolved not in _INSTANCES:
        _INSTANCES[resolved] = _FACTORIES[resolved]()
    return _INSTANCES[resolved]

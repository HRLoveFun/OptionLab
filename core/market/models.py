"""Data contracts for the market analysis domain.

Domain:    Market Analysis
Context:
  - Immutable dataclasses used across market.features, market.projections,
    and market.charts to enforce explicit contracts.
Contracts:
  - MarketFeatures: container for oscillation / returns series
  - ProjectionResult: output of oscillation projection compute
Dependencies UPWARD:
  - core._shared.types (Frequency)
Dependencies DOWNWARD:
  - core.market.features, core.market.projections, core.market.charts
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from core._shared.types import Frequency


@dataclass(frozen=True)
class MarketFeatures:
    """Aligned feature set computed from price bars."""

    ticker: str
    frequency: Frequency
    oscillation: pd.Series
    osc_high: pd.Series
    osc_low: pd.Series
    returns: pd.Series
    difference: pd.Series

    def is_valid(self) -> bool:
        return all(
            s is not None and not s.empty
            for s in (self.oscillation, self.osc_high, self.osc_low, self.returns, self.difference)
        )

    def common_index(self, *names: Literal["oscillation", "osc_high", "osc_low", "returns", "difference"]) -> pd.Index:
        """Return intersection index of requested series."""
        series_map = {
            "oscillation": self.oscillation,
            "osc_high": self.osc_high,
            "osc_low": self.osc_low,
            "returns": self.returns,
            "difference": self.difference,
        }
        idx = None
        for name in names:
            s = series_map[name]
            if s is not None and not s.empty:
                idx = s.index if idx is None else idx.intersection(s.index)
        return idx if idx is not None else pd.Index([])


@dataclass(frozen=True)
class Band:
    """Single projection band (high / low)."""

    high: float
    low: float
    weight: float  # high weight (0–1)


@dataclass(frozen=True)
class ProjectionResult:
    """Output of oscillation projection computation."""

    ticker: str
    percentile: float
    proj_volatility: float
    bias_text: str
    current_band: Band
    next_band: Band
    oos_accuracy: float | None
    train_size: int
    valid_size: int


@dataclass(frozen=True)
class Horizon:
    """User-selected display window."""

    start: dt.date
    end: dt.date
    user_provided_end: bool
    frequency: Frequency

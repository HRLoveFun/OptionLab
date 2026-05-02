"""Price dynamic analysis — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD USE: core.market.data_context.build_data_context

This module re-exports the canonical data-fetching path via a thin
PriceDynamic wrapper so existing tests and callers that monkeypatch
PriceDynamic.__init__ continue to work during the transition.
"""

import datetime as dt
import logging

import pandas as pd

from core.market.data_context import build_data_context
from core.signals.hv import hv_context, vol_premium_context

logger = logging.getLogger(__name__)


class PriceDynamic:
    """Backward-compat wrapper over DataContext.

    Attributes exposed for legacy callers:
      ticker, user_start_date, user_end_date, _user_provided_end,
      frequency, _data, _daily_data

    All data-fetching logic has moved to ``core.market.data_context``.
    """

    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency="D", end_date: dt.date | None = None):
        # Validate and normalise using the canonical helpers
        from core.market.data_context import _normalize_ticker, _validate_inputs

        _validate_inputs(ticker, start_date, frequency, end_date)
        self.ticker = _normalize_ticker(ticker)
        self.user_start_date = start_date
        self.frequency = frequency
        self._user_provided_end = end_date is not None
        self.user_end_date = end_date or dt.date.today()

        # Build context via the canonical data pipeline
        ctx = build_data_context(self.ticker, start_date, frequency, end_date)
        self._data = ctx.bars
        self._daily_data = ctx.daily_bars

    def __getattr__(self, attr):
        if self._data is not None and hasattr(self._data, attr):
            return getattr(self._data, attr)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def __getitem__(self, item):
        if self._data is not None:
            return self._data[item]
        raise KeyError(f"No data available for key: {item}")

    def is_valid(self):
        return self._data is not None and not self._data.empty

    def calculate_hv_context(self) -> dict | None:
        """Multi-window historical volatility and percentile rank."""
        daily = self._daily_data
        if daily is None or len(daily) < 30:
            return None
        try:
            return hv_context(daily.get("Adj Close"))
        except Exception as e:
            logger.warning("HV context calculation failed: %s", e)
            return None

    def build_vol_premium_context(self, atm_iv: float | None) -> dict | None:
        """Compare current IV snapshot with historical HV."""
        daily = self._daily_data
        if daily is None or len(daily) < 30 or atm_iv is None:
            return None
        try:
            return vol_premium_context(daily.get("Adj Close"), atm_iv)
        except Exception as e:
            logger.warning("Vol premium context failed: %s", e)
            return None

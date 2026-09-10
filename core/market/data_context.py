"""Market data context — pure container + resampling.

Domain:    Market Analysis — Data Context
Context:
  - The container market analysis works on: ``bars`` (at the requested
    frequency) plus the ``daily_bars`` they were derived from.
  - INVARIANT (ADR 0001; batch B4 of the reorg): this module performs **no
    I/O**. It receives already-fetched bars and resamples them; acquisition
    (DB-first read + provider fallback) lives in
    ``services/market/data_context_fetch.py``. Closing that leak is what lets
    ``tests/test_architecture_purity.py`` require ``core/`` to have zero
    ``data_pipeline`` imports.
  - No feature calculation, no matplotlib, no business logic.
Contracts:
  - ``DataContext`` — the container (``bars``, ``daily_bars``, ``horizon``,
    ``ticker``, ``frequency``, ``is_valid()``, ``features_df``, ``current_price``).
  - ``refrequency(df, frequency)`` — daily bars → bars at ``D``/``W``/``ME``/``QE``.
  - ``build_data_context(*, ticker, frequency, horizon, raw_data)`` — pure assembly.
Dependencies UPWARD:
  - core.market.features, core.market.models, core._shared.types
Dependencies DOWNWARD:
  - core.market.analyzer, core.market.correlation_validator,
    core.market.charts.facade, services.market.data_context_fetch
"""

from __future__ import annotations

import datetime as dt
import logging

import pandas as pd

from core._shared.types import Frequency
from core.market.models import Horizon

logger = logging.getLogger(__name__)


class DataContext:
    """Immutable-ish container for market data fetched for a given ticker/horizon."""

    def __init__(
        self,
        ticker: str,
        frequency: Frequency,
        horizon: Horizon,
        bars: pd.DataFrame | None,
        daily_bars: pd.DataFrame | None,
    ):
        self.ticker = ticker
        self.frequency = frequency
        self.horizon = horizon
        self.bars = bars
        self.daily_bars = daily_bars

    def is_valid(self) -> bool:
        return self.bars is not None and not self.bars.empty

    @property
    def features_df(self) -> pd.DataFrame:
        """Lazy-assembled feature DataFrame (backward-compat shim)."""
        from core.market.features import osc, price_difference, price_returns

        if not self.is_valid():
            return pd.DataFrame()
        try:
            return pd.DataFrame(
                {
                    "Oscillation": osc(self.bars, on_effect=True),
                    "Osc_high": self._safe_series("Osc_high"),
                    "Osc_low": self._safe_series("Osc_low"),
                    "Returns": price_returns(self.bars),
                    "Difference": price_difference(self.bars),
                }
            ).dropna(how="all")
        except Exception as e:
            logger.warning("features_df assembly failed: %s", e)
            return pd.DataFrame()

    def _safe_series(self, name: str) -> pd.Series | None:
        from core.market.features import osc_high, osc_low

        if name == "Osc_high":
            return osc_high(self.bars)
        if name == "Osc_low":
            return osc_low(self.bars)
        return None

    @property
    def current_price(self) -> float | None:
        if not self.is_valid():
            return None
        try:
            return float(self.bars["Close"].iloc[-1])
        except Exception:
            return None

    @property
    def bars_date_range(self) -> tuple[str, str] | None:
        if not self.is_valid():
            return None
        try:
            return (
                self.bars.index.min().date().isoformat(),
                self.bars.index.max().date().isoformat(),
            )
        except Exception:
            return None


def refrequency(df: pd.DataFrame | None, frequency: Frequency) -> pd.DataFrame | None:
    """Resample daily bars to ``frequency`` and add ``LastClose``/``LastAdjClose``."""
    if df is None or df.empty:
        return None
    try:
        if frequency == "D":
            df = df.copy()
            df["LastClose"] = df["Close"].shift(1)
            df["LastAdjClose"] = df["Adj Close"].shift(1)
            return df
        resampled = (
            df.resample(frequency)
            .agg(
                {
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Adj Close": "last",
                    "Volume": "sum",
                }
            )
            .dropna()
        )
        resampled["LastClose"] = resampled["Close"].shift(1)
        resampled["LastAdjClose"] = resampled["Adj Close"].shift(1)
        date_agg = df.resample(frequency).agg(
            {
                "Open": lambda x: x.index[0] if len(x) > 0 else pd.NaT,
                "High": lambda x: x.index[x.argmax()] if len(x) > 0 else pd.NaT,
                "Low": lambda x: x.index[x.argmin()] if len(x) > 0 else pd.NaT,
                "Close": lambda x: x.index[-1] if len(x) > 0 else pd.NaT,
            }
        )
        resampled["OpenDate"] = date_agg["Open"]
        resampled["HighDate"] = date_agg["High"]
        resampled["LowDate"] = date_agg["Low"]
        resampled["CloseDate"] = date_agg["Close"]
        return resampled
    except Exception as e:
        logger.error("Error resampling data: %s", e)
        return None


def build_data_context(
    *,
    ticker: str,
    frequency: Frequency,
    horizon: Horizon,
    raw_data: pd.DataFrame | None,
) -> DataContext:
    """Assemble a ``DataContext`` from bars that were already fetched.

    WHY keyword-only with an explicit ``raw_data``: the caller (a service) owns
    acquisition, so this function stays pure and cannot accidentally re-introduce
    the core→data_pipeline edge that batch B4 removed.
    """
    return DataContext(
        ticker=ticker,
        frequency=frequency,
        horizon=horizon,
        bars=refrequency(raw_data, frequency),
        daily_bars=raw_data,
    )


def empty_data_context(ticker: str, start_date: dt.date, frequency: Frequency, end_date: dt.date | None) -> DataContext:
    """Return an invalid context for a failed acquisition (no bars)."""
    return DataContext(
        ticker=ticker,
        frequency=frequency,
        horizon=Horizon(
            start=start_date,
            end=end_date or dt.date.today(),
            user_provided_end=end_date is not None,
            frequency=frequency,
        ),
        bars=None,
        daily_bars=None,
    )

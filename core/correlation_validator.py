"""Correlation Validation Module — BACKWARD-COMPAT ADAPTER.

Rolling correlation computation stays here (domain-specific logic);
rendering has moved to core.market.charts.correlation.
"""

from __future__ import annotations

import datetime as dt
import logging

import numpy as np
import pandas as pd

from core.market.charts.correlation import render_correlation
from core.market.data_context import build_data_context
from core.market.features._horizon import apply_horizon, compute_effective_end

logger = logging.getLogger(__name__)


class CorrelationValidator:
    """Validates market patterns through rolling correlation analysis."""

    def __init__(
        self,
        ticker: str,
        start_date: dt.date = dt.date(2016, 12, 1),
        frequency: str = "W",
        end_date: dt.date | None = None,
        price_data=None,
    ):
        self.ticker = ticker
        self.user_start_date = start_date
        self.frequency = frequency
        self.user_end_date = end_date or dt.date.today()
        self._user_provided_end = end_date is not None

        # Duck-type support: injected object may be _PriceDynamicShim (has _data)
        # or DataContext (has bars).
        if price_data is not None:
            self._raw_data = getattr(price_data, "_data", None) or getattr(price_data, "bars", None)
            is_valid_fn = getattr(price_data, "is_valid", None)
            self._is_valid = bool(is_valid_fn()) if is_valid_fn else self._raw_data is not None
        else:
            ctx = build_data_context(ticker, start_date, frequency, end_date)
            self._raw_data = ctx.bars
            self._is_valid = ctx.is_valid()

        self.data = self._build_data()

    def _build_data(self) -> pd.DataFrame | None:
        try:
            if not self._is_valid:
                logger.warning("No valid data for %s", self.ticker)
                return None
            full_df = self._raw_data
            if full_df is None or full_df.empty:
                logger.warning("No full dataset available for %s", self.ticker)
                return None

            data = pd.DataFrame(index=full_df.index)
            try:
                ret_pct = ((full_df["Close"] - full_df["LastClose"]) / full_df["LastClose"]) * 100
                data["log_return"] = np.log1p(ret_pct / 100.0)
            except Exception as e:
                logger.warning("Failed computing log_return: %s", e)
            try:
                data["osc_high"] = (full_df["High"] / full_df["LastClose"] - 1) * 100
            except Exception as e:
                logger.warning("Failed computing osc_high: %s", e)
            try:
                data["osc_low"] = (full_df["Low"] / full_df["LastClose"] - 1) * 100
            except Exception as e:
                logger.warning("Failed computing osc_low: %s", e)

            data = data.dropna(how="all")
            return data if not data.empty else None
        except Exception as e:
            logger.error("Error building data: %s", e)
            return None

    def is_data_valid(self) -> bool:
        return self.data is not None and not self.data.empty

    def _horizon_filter(self, series: pd.Series | None) -> pd.Series | None:
        """Apply horizon filtering using the canonical helper from core.market.features."""
        if series is None or series.empty:
            return series
        try:
            end_ts = (
                pd.Timestamp(self.user_end_date)
                if self._user_provided_end
                else compute_effective_end(self.frequency)
            )
            return apply_horizon(series, self.user_start_date, end_ts.date(), self._user_provided_end, self.frequency)
        except Exception:
            return series

    def calculate_return_autocorrelation(self, window_years: int = 1) -> pd.Series | None:
        if self.data is None or self.data.empty:
            return None
        try:
            returns = self.data["log_return"].dropna()
            if len(returns) < 2:
                return None
            returns_shifted = returns.shift(1)
            if self.frequency == "D":
                window = window_years * 252
            elif self.frequency == "W":
                window = window_years * 52
            elif self.frequency == "ME":
                window = window_years * 12
            elif self.frequency == "QE":
                window = window_years * 4
            else:
                window = window_years * 52
            rolling_corr = returns.rolling(window=window, min_periods=max(10, window // 2)).corr(returns_shifted)
            rolling_corr.name = f"Return_Autocorr_{window_years}Y"
            return self._horizon_filter(rolling_corr.dropna())
        except Exception as e:
            logger.error("Error calculating return autocorrelation: %s", e)
            return None

    def calculate_osc_correlation(self, window_years: int = 1) -> pd.Series | None:
        if self.data is None or self.data.empty:
            return None
        try:
            osc_high = self.data.get("osc_high")
            osc_low = self.data.get("osc_low")
            if osc_high is None or osc_low is None:
                logger.warning("osc_high or osc_low not available")
                return None
            osc_high = osc_high.dropna()
            osc_low = osc_low.dropna()
            if self.frequency == "D":
                window = window_years * 252
            elif self.frequency == "W":
                window = window_years * 52
            elif self.frequency == "ME":
                window = window_years * 12
            elif self.frequency == "QE":
                window = window_years * 4
            else:
                window = window_years * 52
            rolling_corr = osc_high.rolling(window=window, min_periods=max(10, window // 2)).corr(osc_low)
            rolling_corr.name = f"Osc_Corr_{window_years}Y"
            return self._horizon_filter(rolling_corr.dropna())
        except Exception as e:
            logger.error("Error calculating osc correlation: %s", e)
            return None

    def generate_consolidated_correlation_chart(self) -> str | None:
        try:
            return_1y = self.calculate_return_autocorrelation(window_years=1)
            return_5y = self.calculate_return_autocorrelation(window_years=5)
            osc_1y = self.calculate_osc_correlation(window_years=1)
            osc_5y = self.calculate_osc_correlation(window_years=5)
            return render_correlation(return_1y, return_5y, osc_1y, osc_5y)
        except Exception as e:
            logger.error("Error generating consolidated correlation chart: %s", e)
            return None

    def generate_all_correlation_charts(self) -> dict:
        results = {}
        try:
            consolidated_chart = self.generate_consolidated_correlation_chart()
            if consolidated_chart:
                results["correlation_dynamics_chart"] = consolidated_chart
                results["return_autocorr_chart"] = consolidated_chart
                results["osc_corr_chart"] = consolidated_chart
        except Exception as e:
            logger.error("Error generating correlation charts: %s", e)
        return results

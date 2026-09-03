"""Aggregated chart assembly for market analysis.

Domain:    Market Analysis — Chart Assembly (facade over renderers)
Context:
  - Owns every chart-producing method that previously lived on
    ``core.market.analyzer.MarketAnalyzer``. The analyzer was the repo's top
    fan-out change-magnet (15) because it imported every renderer plus the
    feature/projection primitives used to feed them. Pulling the chart
    assembly here pins the boundary exactly like the options side did with
    ``core.options.charts.facade``: adding a chart type touches this file and
    the renderer, never the orchestrator.
  - ``MarketAnalyzer`` stays a thin orchestrator: it builds the ``DataContext``
    and delegates all chart generation to ``MarketChartAssembly``.
Contracts:
  - MarketChartAssembly(ctx, features_df, ticker, frequency)
  - generate_scatter_plots(feature_name, rolling_window=20, risk_threshold=90) -> str | None
  - generate_high_low_scatter() -> str | None
  - generate_return_osc_high_low_chart(rolling_window=20, risk_threshold=90) -> str | None
  - generate_volatility_dynamics() -> str | None
  - generate_oscillation_projection(percentile=0.90, target_bias=None) -> (str|None, str|None)
  - analyze_options(option_data) -> str | None
Dependencies UPWARD:
  - core.market.charts.{dynamics, projection, scatter_high_low, scatter_osc, volatility, option_pnl}
  - core.market.charts._scales.format_projection_value
  - core.market.features.{osc, osc_high, osc_low, price_returns, _horizon, regime_segments, volatility}
  - core.market.projections.oscillation
  - core.market.option_pnl
Dependencies DOWNWARD:
  - core.market.analyzer
"""

from __future__ import annotations

import logging

from core.market.charts._scales import format_projection_value
from core.market.charts.dynamics import render_dynamics
from core.market.charts.option_pnl import render_option_pnl
from core.market.charts.projection import render_projection
from core.market.charts.scatter_high_low import render_scatter_high_low
from core.market.charts.scatter_osc import render_scatter_osc
from core.market.charts.volatility import render_volatility
from core.market.features import osc, osc_high, osc_low, price_returns
from core.market.features._horizon import apply_horizon
from core.market.features.regime_segments import bull_bear_segments
from core.market.features.volatility import calculate_volatility
from core.market.option_pnl import build_option_matrix
from core.market.projections.oscillation import compute_oscillation_projection

logger = logging.getLogger(__name__)


class MarketChartAssembly:
    """Chart-producing methods extracted from ``MarketAnalyzer``.

    INVARIANT: this class is pure chart assembly — it never fetches data and
    never constructs a ``DataContext``. It receives everything it needs from
    the orchestrator.
    """

    def __init__(self, ctx, features_df, ticker: str, frequency: str):
        self._ctx = ctx
        self.features_df = features_df
        self.ticker = ticker
        self.frequency = frequency

    def generate_scatter_plots(self, feature_name, rolling_window=20, risk_threshold=90):
        """Generate scatter plot with marginal histograms."""
        if not self._ctx.is_valid() or feature_name not in self.features_df.columns:
            return None
        try:
            h = self._ctx.horizon
            osc_s = apply_horizon(osc(self._ctx.bars, on_effect=True), h.start, h.end, h.user_provided_end, h.frequency)
            ret_s = apply_horizon(price_returns(self._ctx.bars), h.start, h.end, h.user_provided_end, h.frequency)
            if osc_s is None or ret_s is None:
                return None
            return render_scatter_osc(osc_s, ret_s)
        except Exception as e:
            logger.error("Error generating scatter plot: %s", e)
            return None

    def generate_high_low_scatter(self):
        """Generate Osc_Low vs Osc_High scatter plot with marginal histograms."""
        if not self._ctx.is_valid():
            return None
        try:
            h = self._ctx.horizon
            oh = apply_horizon(osc_high(self._ctx.bars), h.start, h.end, h.user_provided_end, h.frequency)
            ol = apply_horizon(osc_low(self._ctx.bars), h.start, h.end, h.user_provided_end, h.frequency)
            if oh is None or ol is None:
                return None
            return render_scatter_high_low(ol, oh)
        except Exception as e:
            logger.error("Error generating high-low scatter: %s", e)
            return None

    def generate_return_osc_high_low_chart(self, rolling_window=20, risk_threshold=90):
        """Generate Return-Oscillation line chart with rolling projections."""
        if not self._ctx.is_valid() or self.features_df.empty:
            return None
        try:
            h = self._ctx.horizon
            returns_full = price_returns(self._ctx.bars)
            osc_high_full = osc_high(self._ctx.bars)
            osc_low_full = osc_low(self._ctx.bars)

            returns = apply_horizon(returns_full, h.start, h.end, h.user_provided_end, h.frequency)
            osc_high_f = apply_horizon(osc_high_full, h.start, h.end, h.user_provided_end, h.frequency)
            osc_low_f = apply_horizon(osc_low_full, h.start, h.end, h.user_provided_end, h.frequency)

            if returns is None or osc_high_f is None or osc_low_f is None:
                return None
            return render_dynamics(
                returns, osc_high_f, osc_low_f, osc_high_full, osc_low_full, rolling_window, risk_threshold
            )
        except Exception as e:
            logger.error("Error generating return-osc chart: %s", e)
            return None

    def generate_volatility_dynamics(self):
        """Generate price & volatility dynamics chart with bull/bear segments."""
        if not self._ctx.is_valid():
            return None
        try:
            daily_bars = self._ctx.daily_bars
            if daily_bars is None or daily_bars.empty or "Close" not in daily_bars.columns:
                return None
            daily_close = daily_bars["Close"]
            logger.debug(
                "generate_volatility_dynamics ticker=%s: bars=%d, range=%s to %s",
                self.ticker,
                len(daily_close),
                daily_close.index[0].date(),
                daily_close.index[-1].date(),
            )
            h = self._ctx.horizon
            volatility = calculate_volatility(daily_close, self.frequency)
            if volatility is not None and not volatility.empty:
                logger.debug(
                    "generate_volatility_dynamics ticker=%s: raw volatility len=%d, last=%.4f%%",
                    self.ticker,
                    len(volatility),
                    volatility.iloc[-1],
                )
            volatility = apply_horizon(volatility, h.start, h.end, h.user_provided_end, h.frequency)
            if volatility is None or volatility.empty:
                logger.warning(
                    "generate_volatility_dynamics ticker=%s: volatility empty after horizon filter", self.ticker
                )
                return None
            daily_close_filtered = apply_horizon(daily_close, h.start, h.end, h.user_provided_end, h.frequency)
            segs = bull_bear_segments(daily_close_filtered)
            return render_volatility(daily_close_filtered, volatility, segs, self.ticker, self.frequency)
        except Exception as e:
            logger.error("Error generating volatility dynamics: %s", e)
            return None

    def generate_oscillation_projection(self, percentile=0.90, target_bias=None):
        """Generate oscillation projection figure and summary table."""
        if not self._ctx.is_valid():
            return None, None
        try:
            bars = self._ctx.bars.copy()
            bars["Oscillation"] = osc(bars, on_effect=True)
            result, proj_df = compute_oscillation_projection(
                bars, self._ctx.daily_bars, percentile, target_bias, self.frequency
            )
            if result is None:
                return None, None

            chart = render_projection(
                proj_df,
                result.percentile,
                result.proj_volatility,
                result.bias_text,
                result.oos_accuracy,
                result.train_size,
                result.valid_size,
            )
            projection_table = (
                proj_df.dropna(how="all")
                .fillna("")
                .apply(
                    lambda col: (
                        col.apply(format_projection_value)
                        if col.name in ["Close", "High", "Low", "iHigh", "iLow", "iHigh1", "iLow1"]
                        else col
                    )
                )
                .to_html(classes="table table-striped table-sm", index=True, escape=False)
            )
            return chart, projection_table
        except Exception as e:
            logger.error("Error generating oscillation projection: %s", e)
            return None, None

    def analyze_options(self, option_data):
        if not option_data:
            return None
        try:
            current_price = self._ctx.current_price
            if current_price is None:
                return None
            matrix_df = build_option_matrix(option_data, current_price)
            return render_option_pnl(matrix_df, current_price, option_data)
        except Exception as e:
            logger.error("Error analyzing options: %s", e)
            return None


__all__ = ["MarketChartAssembly"]

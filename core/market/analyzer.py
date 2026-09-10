"""Market Analyzer — canonical implementation.

Domain:    Market Analysis — Orchestration
Context:
  - Wraps an already-fetched ``DataContext`` and delegates all chart rendering
    to ``core.market.charts.facade.MarketChartAssembly``.
  - INVARIANT (ADR 0001; batch B4): it does **not** fetch. Callers build the
    context with ``services.market.data_context_fetch.fetch_data_context`` and
    pass it in — see ``OptionsChainAnalyzer(snapshot=…)`` for the same pattern.
  - Kept intentionally thin: the chart-assembly fan-out (renderers + the
    feature/projection primitives that feed them) lives in the facade, so this
    module is no longer the repo's top change-magnet.
Dependencies UPWARD:
  - core.market.data_context, core.market.charts.facade
Dependencies DOWNWARD:
  - services.market.analysis.facade, services.market.analysis.statistical, tests
"""

from __future__ import annotations

import logging

from core.market.charts.facade import MarketChartAssembly
from core.market.data_context import DataContext

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """High-level market analysis — thin orchestrator over core.market submodules."""

    def __init__(self, data_context: DataContext):
        """Wrap ``data_context``.

        WHY the context is injected rather than built here: constructing it means
        reading the DB and possibly the provider, which core/ must not do (ADR
        0001). Services own that decision — see
        ``services/market/data_context_fetch.py``.
        """
        self._ctx = data_context
        self.ticker = data_context.ticker
        self.frequency = data_context.frequency
        # Backward-compat: the old signature exposed the caller's ``end_date``
        # (None when the horizon end was implicit).
        self.end_date = data_context.horizon.end if data_context.horizon.user_provided_end else None
        self.features_df = self._ctx.features_df
        self._charts = MarketChartAssembly(self._ctx, self.features_df, self.ticker, self.frequency)

    @property
    def data_context(self) -> DataContext:
        """The wrapped context (public accessor for service-layer callers)."""
        return self._ctx

    def is_data_valid(self):
        return self._ctx.is_valid()

    def _get_current_price(self):
        # WHY: referenced by services.market.analysis.assessment but previously
        # unimplemented; exposed here to keep the orchestrator's contract stable.
        return self._ctx.current_price

    # ------------------------------------------------------------------
    # Charts — delegate to core.market.charts.facade.MarketChartAssembly
    # ------------------------------------------------------------------

    def generate_scatter_plots(self, feature_name, rolling_window=20, risk_threshold=90):
        return self._charts.generate_scatter_plots(feature_name, rolling_window, risk_threshold)

    def generate_high_low_scatter(self):
        return self._charts.generate_high_low_scatter()

    def generate_return_osc_high_low_chart(self, rolling_window=20, risk_threshold=90):
        return self._charts.generate_return_osc_high_low_chart(rolling_window, risk_threshold)

    def generate_volatility_dynamics(self):
        return self._charts.generate_volatility_dynamics()

    def generate_oscillation_projection(self, percentile=0.90, target_bias=None):
        return self._charts.generate_oscillation_projection(percentile, target_bias)

    def analyze_options(self, option_data):
        return self._charts.analyze_options(option_data)

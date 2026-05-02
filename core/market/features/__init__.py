"""Market feature computation — pure functions, no I/O.

Domain:    Market Analysis — Feature Engineering
Context:
  - All functions accept pd.DataFrame/Series and return pd.Series.
  - No external data fetching; callers pass price bars.
Contracts:
  - osc(bars, on_effect=True) -> pd.Series
  - returns(bars) -> pd.Series
  - volatility(daily_close, window) -> pd.Series
Dependencies UPWARD:
  - pandas, numpy
Dependencies DOWNWARD:
  - core.market.projections, core.market.charts
"""

from core.market.features._horizon import apply_horizon, compute_effective_end
from core.market.features.osc import osc, osc_high, osc_low
from core.market.features.regime_segments import bull_bear_segments
from core.market.features.returns import price_difference, price_returns
from core.market.features.volatility import calculate_volatility, hv_context

__all__ = [
    "apply_horizon",
    "compute_effective_end",
    "osc",
    "osc_high",
    "osc_low",
    "bull_bear_segments",
    "price_returns",
    "price_difference",
    "calculate_volatility",
    "hv_context",
]

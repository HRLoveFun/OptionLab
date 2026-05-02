"""Market chart rendering — matplotlib only, no data fetching.

Domain:    Market Analysis — Charts
Context:
  - Each module renders one chart type from pre-computed data.
  - All use core._shared.plotting.new_figure() for explicit lifecycle.
Contracts:
  - render_scatter_osc(features) -> str
  - render_scatter_high_low(features) -> str
  - render_dynamics(...) -> str
  - render_volatility(...) -> str
  - render_projection(proj_result, proj_df) -> str
  - render_correlation(...) -> str
Dependencies UPWARD:
  - core._shared.plotting, core.market.features, core.market.projections
Dependencies DOWNWARD:
  - services.chart_service, app.py routes
"""

"""Options chart rendering — matplotlib only.

Domain:    Options Analysis — Charts
Context:
  - Each function renders one chart type from pre-fetched chain data.
Contracts:
  - render_iv_smile(calls, puts, spot, expiry) -> str | None
  - render_iv_term_structure(expiries_data, spot) -> str | None
  - render_iv_surface(records, spot, ticker) -> str | None
  - render_skew(calls, puts, spot, expiry) -> str | None
  - render_oi_volume(calls, puts, spot, expiry) -> str | None
  - render_pcr(rows, ticker) -> str | None
Dependencies UPWARD:
  - core._shared.plotting
Dependencies DOWNWARD:
  - services.chart_service, services.options_chain_service
"""

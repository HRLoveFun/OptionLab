"""Aggregated access point for the options chart renderers.

Domain:    Options Analysis — Charts Facade
Context:
  - Single import surface over the six chart modules so orchestrators (e.g.
    ``core.options.chain.analyzer``) depend on one module instead of six.
    WHY: the analyzer previously fanned out to every renderer directly, which
    made its import graph a mirror of the charts package layout and inflated
    its coupling metrics. The facade pins the boundary: adding a chart type
    touches this file and the renderer, not every orchestrator.
Contracts:
  - render_iv_smile(calls, puts, spot, expiry) -> str | None
  - render_iv_term_structure(dates, atm_ivs, spot) -> str | None
  - render_iv_surface(records, spot, ticker) -> str | None
  - render_skew(calls, puts, spot, expiry) -> str | None
  - render_oi_volume(calls, puts, spot, expiry) -> str | None
  - render_pcr(rows, ticker) -> str | None
Dependencies UPWARD:
  - core.options.charts.{iv_smile, iv_surface, iv_term, oi_volume, pcr, skew}
Dependencies DOWNWARD:
  - core.options.chain.analyzer
"""

from __future__ import annotations

from core.options.charts.iv_smile import render_iv_smile
from core.options.charts.iv_surface import render_iv_surface
from core.options.charts.iv_term import render_iv_term_structure
from core.options.charts.oi_volume import render_oi_volume
from core.options.charts.pcr import render_pcr
from core.options.charts.skew import render_skew

__all__ = [
    "render_iv_smile",
    "render_iv_surface",
    "render_iv_term_structure",
    "render_oi_volume",
    "render_pcr",
    "render_skew",
]

"""Option-portfolio simulator (optsim): value and risk of a hypothetical position over time.

Domain:    Option Simulation
Context:
  - Core scope: revalue a multi-leg position on spot × day × IV-shift, with
    position Greeks, Reg-T and portfolio-margin requirements, and a switch
    between European and American exercise.
  - Pure computation; the CLI in ``scripts/optsim.py`` does the file I/O, and
    services/options/optsim.py fetches the chain the ticker mode prices on.
  - Design notes: docs/decisions/0013-optsim-scenario-engine.md.
Contracts:
  - Market, Smile, Position, make_leg, strike_for_delta
  - scenario_grid, time_profile, breakevens, breakeven_iv, Grid
  - european, american, option_greeks, implied_vol
  - regt_bpr, pm_bpr, pm_offsets, margin_class, PRODUCTS
  - listed_market, nearest_expiry, nearest_quote, iv_curve, leg_iv
  - render_grid_png
Dependencies UPWARD:
  - core.optsim.models, core.optsim.pricing, core.optsim.margin,
    core.optsim.engine, core.optsim.market, core.optsim.charts
Dependencies DOWNWARD:
  - scripts/optsim.py, services.options.optsim, tests
"""

from core.optsim.charts import render_grid_png
from core.optsim.engine import Grid, breakeven_iv, breakevens, default_days, scenario_grid, time_profile
from core.optsim.margin import PRODUCTS, margin_class, pm_bpr, pm_offsets, regt_bpr
from core.optsim.market import iv_curve, leg_iv, listed_market, nearest_expiry, nearest_quote
from core.optsim.models import Market, Position, Smile, make_leg, strike_for_delta
from core.optsim.pricing import american, european, implied_vol, option_greeks

__all__ = [
    "Grid",
    "Market",
    "PRODUCTS",
    "Position",
    "Smile",
    "american",
    "breakeven_iv",
    "breakevens",
    "default_days",
    "european",
    "implied_vol",
    "iv_curve",
    "leg_iv",
    "listed_market",
    "make_leg",
    "margin_class",
    "nearest_expiry",
    "nearest_quote",
    "option_greeks",
    "pm_bpr",
    "pm_offsets",
    "regt_bpr",
    "render_grid_png",
    "scenario_grid",
    "strike_for_delta",
    "time_profile",
]

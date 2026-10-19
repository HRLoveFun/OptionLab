"""Option-portfolio simulator (optsim): value and risk of a hypothetical position over time.

Domain:    Option Simulation
Context:
  - Core scope: revalue a multi-leg position on spot × day × IV-shift, with
    position Greeks, Reg-T and portfolio-margin requirements, and a switch
    between European and American exercise.
  - Pure computation; the CLI in ``scripts/optsim.py`` does the file I/O.
  - Design notes: docs/decisions/0013-optsim-scenario-engine.md.
Contracts:
  - Market, Smile, Position, make_leg, strike_for_delta
  - scenario_grid, time_profile, breakevens, Grid
  - european, american, option_greeks
  - regt_bpr, pm_bpr, pm_offsets, PRODUCTS
  - render_grid_png
Dependencies UPWARD:
  - core.optsim.models, core.optsim.pricing, core.optsim.margin,
    core.optsim.engine, core.optsim.charts
Dependencies DOWNWARD:
  - scripts/optsim.py, tests
"""

from core.optsim.charts import render_grid_png
from core.optsim.engine import Grid, breakevens, default_days, scenario_grid, time_profile
from core.optsim.margin import PRODUCTS, pm_bpr, pm_offsets, regt_bpr
from core.optsim.models import Market, Position, Smile, make_leg, strike_for_delta
from core.optsim.pricing import american, european, option_greeks

__all__ = [
    "Grid",
    "Market",
    "PRODUCTS",
    "Position",
    "Smile",
    "american",
    "breakevens",
    "default_days",
    "european",
    "make_leg",
    "option_greeks",
    "pm_bpr",
    "pm_offsets",
    "regt_bpr",
    "render_grid_png",
    "scenario_grid",
    "strike_for_delta",
    "time_profile",
]

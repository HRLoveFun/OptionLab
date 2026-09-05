"""Options expiry-payoff simulation package.

Domain:    Options Analysis — Expiry Simulation
Context:
  - Groups the pure (network-free) maths used by the dashboard "Simulation"
    tab: price a strike with Black-Scholes, then project what it pays at
    expiration under every requested (maturity, implied-vol) scenario.
Contracts:
  - simulate_expiry(...)          -> dict
  - parse_expiries(values, ...)   -> list[dict]
  - generate_expiry_calendar(...) -> list[dict]
Dependencies UPWARD:
  - core.options.simulation.expiry (payoff maths)
  - core.options.simulation.expiry_calendar (listed expirations)
Dependencies DOWNWARD:
  - services.options.simulation, routes.options, tests
"""

from core.options.simulation.expiry import (
    parse_expiries,
    simulate_expiry,
)
from core.options.simulation.expiry_calendar import generate_expiry_calendar

__all__ = ["parse_expiries", "simulate_expiry", "generate_expiry_calendar"]

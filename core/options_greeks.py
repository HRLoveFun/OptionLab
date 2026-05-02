"""Options Greeks — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.options.greeks
  from core.options.greeks import greeks_vectorized, portfolio_greeks_table, theta_decay_path

This module re-exports the canonical implementation from core.options.greeks.*
to preserve existing import paths during the transition.
"""

from core.options.greeks.black_scholes import greeks_vectorized
from core.options.greeks.portfolio import portfolio_greeks_table, theta_decay_path

__all__ = [
    "greeks_vectorized",
    "portfolio_greeks_table",
    "theta_decay_path",
]

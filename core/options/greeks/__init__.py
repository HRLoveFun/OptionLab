"""Black-Scholes Greeks computation.

Domain:    Options Analysis — Greeks
Context:
  - Vectorised numpy functions; no pandas/matplotlib.
Contracts:
  - greeks_vectorized(S, K, T, r, sigma, option_type) -> dict[str, np.ndarray]
  - portfolio_greeks_table(positions, spot) -> tuple[dict, pd.DataFrame]
  - theta_decay_path(positions, spot) -> tuple[np.ndarray, np.ndarray]
Dependencies UPWARD:
  - scipy.stats, numpy
Dependencies DOWNWARD:
  - core.strategies, core.portfolio, core.options.chain
"""

from core.options.greeks.black_scholes import greeks_vectorized
from core.options.greeks.portfolio import portfolio_greeks_table, theta_decay_path

__all__ = [
    "greeks_vectorized",
    "portfolio_greeks_table",
    "theta_decay_path",
]

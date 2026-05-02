"""Vectorized Black-Scholes Greeks calculation.

Domain:    Options Analysis — Black-Scholes
Context:
  - Inputs come from yfinance option-chain snapshots.
  - Defensive against illiquid strikes (bid=0, IV=999.x).
  - European exercise assumption.
Contracts:
  - greeks_vectorized(S, K, T, r, sigma, option_type) -> dict[str, np.ndarray]
Dependencies UPWARD:
  - scipy.stats, numpy
Dependencies DOWNWARD:
  - core.options.greeks.portfolio, core.strategies
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.stats import norm

logger = logging.getLogger(__name__)

_T_MIN = 1 / 365

# CONSTRAINT: zero-IV inputs would trigger division-by-zero in the d1 / d2 formulas.
_SIGMA_MIN = 0.001

# CONSTRAINT: corrupt chain data (e.g. IV=999) would explode exponent terms and swamp valid Greeks with NaNs.
_SIGMA_MAX = 20.0


def _safe_inputs(S, K, T, sigma):
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    valid = (
        np.isfinite(S) & (S > 0) & np.isfinite(K) & (K > 0)
        & np.isfinite(sigma) & (sigma >= _SIGMA_MIN) & (sigma <= _SIGMA_MAX)
        & np.isfinite(T) & (T >= _T_MIN)
    )
    S_ = np.where(valid, S, 100.0)
    K_ = np.where(valid, K, 100.0)
    T_ = np.where(valid, T, 1 / 365)
    sigma_ = np.where(valid, sigma, 0.2)
    return S_, K_, T_, sigma_, valid


def greeks_vectorized(S, K, T, r, sigma, option_type="call"):
    """Vectorized Black-Scholes Greeks.

    Parameters can be scalars or equal-length NumPy arrays.
    Returns dict with same-shape arrays; invalid positions contain np.nan.
    """
    S_, K_, T_, sigma_, valid = _safe_inputs(S, K, T, sigma)
    r_ = float(r)
    sqrt_T = np.sqrt(T_)
    d1 = (np.log(S_ / K_) + (r_ + 0.5 * sigma_**2) * T_) / (sigma_ * sqrt_T)
    d2 = d1 - sigma_ * sqrt_T
    n_d1 = norm.pdf(d1)
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    disc = np.exp(-r_ * T_)

    gamma = np.where(valid, n_d1 / (S_ * sigma_ * sqrt_T), np.nan)
    vega = np.where(valid, S_ * n_d1 * sqrt_T / 100, np.nan)

    if option_type == "call":
        delta = np.where(valid, N_d1, np.nan)
        theta = np.where(valid, (-(S_ * n_d1 * sigma_) / (2 * sqrt_T) - r_ * K_ * disc * N_d2) / 365, np.nan)
        price = np.where(valid, S_ * N_d1 - K_ * disc * N_d2, np.nan)
    else:
        delta = np.where(valid, N_d1 - 1, np.nan)
        theta = np.where(valid, (-(S_ * n_d1 * sigma_) / (2 * sqrt_T) + r_ * K_ * disc * norm.cdf(-d2)) / 365, np.nan)
        price = np.where(valid, K_ * disc * norm.cdf(-d2) - S_ * norm.cdf(-d1), np.nan)

    S_raw = np.asarray(S, dtype=float)
    K_raw = np.asarray(K, dtype=float)
    intrinsic = np.where(option_type == "call", np.maximum(S_raw - K_raw, 0), np.maximum(K_raw - S_raw, 0))

    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "bs_price": price,
        "intrinsic": intrinsic,
        "time_value": np.where(valid, np.maximum(price - intrinsic, 0), np.nan),
    }

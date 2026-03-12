"""
Vectorized Black-Scholes Greeks calculation.

All functions accept scalar or NumPy array inputs (broadcast-compatible).
Invalid inputs produce np.nan in the output rather than raising exceptions.
"""

import numpy as np
from scipy.stats import norm
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Numerical stability constants
_T_MIN = 1 / 365        # minimum valid time (1 day)
_SIGMA_MIN = 0.001       # minimum valid IV (0.1%)
_SIGMA_MAX = 20.0        # maximum valid IV (2000%), filters yfinance anomalies


def _safe_inputs(S, K, T, sigma):
    """Sanitise inputs and return (S, K, T, sigma, valid_mask).

    All parameters accept scalars or NumPy arrays (broadcast-compatible).
    """
    S     = np.asarray(S, dtype=float)
    K     = np.asarray(K, dtype=float)
    T     = np.asarray(T, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    valid = (
        np.isfinite(S) & (S > 0) &
        np.isfinite(K) & (K > 0) &
        np.isfinite(sigma) & (sigma >= _SIGMA_MIN) & (sigma <= _SIGMA_MAX) &
        np.isfinite(T) & (T >= _T_MIN)
    )
    S_     = np.where(valid, S,     100.0)
    K_     = np.where(valid, K,     100.0)
    T_     = np.where(valid, T,     1 / 365)
    sigma_ = np.where(valid, sigma, 0.2)

    return S_, K_, T_, sigma_, valid


def greeks_vectorized(S, K, T, r, sigma, option_type='call'):
    """Vectorized Black-Scholes Greeks.

    Parameters can be scalars or equal-length NumPy arrays.

    Returns a dict where each value has the same shape as the inputs.
    Invalid-input positions contain np.nan.
    """
    S_, K_, T_, sigma_, valid = _safe_inputs(S, K, T, sigma)
    r_ = float(r)

    sqrt_T = np.sqrt(T_)
    d1 = (np.log(S_ / K_) + (r_ + 0.5 * sigma_ ** 2) * T_) / (sigma_ * sqrt_T)
    d2 = d1 - sigma_ * sqrt_T

    n_d1 = norm.pdf(d1)
    N_d1 = norm.cdf(d1)
    N_d2 = norm.cdf(d2)
    disc = np.exp(-r_ * T_)

    gamma = np.where(valid, n_d1 / (S_ * sigma_ * sqrt_T), np.nan)
    vega  = np.where(valid, S_ * n_d1 * sqrt_T / 100,      np.nan)

    if option_type == 'call':
        delta = np.where(valid, N_d1,                                    np.nan)
        theta = np.where(valid,
                         (-(S_ * n_d1 * sigma_) / (2 * sqrt_T)
                          - r_ * K_ * disc * N_d2) / 365,               np.nan)
        price = np.where(valid, S_ * N_d1 - K_ * disc * N_d2,           np.nan)
    else:
        delta = np.where(valid, N_d1 - 1,                               np.nan)
        theta = np.where(valid,
                         (-(S_ * n_d1 * sigma_) / (2 * sqrt_T)
                          + r_ * K_ * disc * norm.cdf(-d2)) / 365,      np.nan)
        price = np.where(valid, K_ * disc * norm.cdf(-d2) - S_ * norm.cdf(-d1), np.nan)

    S_raw  = np.asarray(S, dtype=float)
    K_raw  = np.asarray(K, dtype=float)
    intrinsic = np.where(
        option_type == 'call',
        np.maximum(S_raw - K_raw, 0),
        np.maximum(K_raw - S_raw, 0)
    )

    return {
        'delta':      delta,
        'gamma':      gamma,
        'theta':      theta,
        'vega':       vega,
        'bs_price':   price,
        'intrinsic':  intrinsic,
        'time_value': np.where(valid, np.maximum(price - intrinsic, 0), np.nan),
    }


def portfolio_greeks_table(positions: list, spot: float, r: float = 0.05) -> tuple:
    """Compute net Greeks and a detail table for a multi-leg option portfolio.

    positions format:
        [{'type': 'LC'|'SC'|'LP'|'SP',
          'strike': float, 'dte': int,
          'iv': float (decimal, e.g. 0.25),
          'qty': int, 'premium': float}, ...]

    Returns (totals_dict, detail_df).
    """
    totals = {'delta': 0.0, 'gamma': 0.0, 'theta': 0.0,
              'vega': 0.0, 'net_premium': 0.0}
    rows = []

    for pos in positions:
        try:
            is_call = pos['type'] in ('LC', 'SC')
            is_long = pos['type'] in ('LC', 'LP')
            sign = 1 if is_long else -1
            T = max(pos['dte'], 1) / 365

            g = greeks_vectorized(
                S=float(spot), K=float(pos['strike']),
                T=T, r=r, sigma=float(pos['iv']),
                option_type='call' if is_call else 'put'
            )

            qty = int(pos['qty']) * sign

            def _val(key):
                v = g[key]
                return float(v) if np.isfinite(v) else 0.0

            totals['delta']       += _val('delta')  * qty
            totals['gamma']       += _val('gamma')  * qty
            totals['theta']       += _val('theta')  * qty
            totals['vega']        += _val('vega')   * qty
            totals['net_premium'] += float(pos['premium']) * int(pos['qty']) * (-sign)

            rows.append({
                'Leg':     pos['type'],
                'Strike':  pos['strike'],
                'DTE':     pos['dte'],
                'IV':      f"{pos['iv'] * 100:.1f}%",
                'Qty':     qty,
                'Delta':   f"{_val('delta') * qty:+.3f}",
                'Gamma':   f"{_val('gamma') * qty:+.5f}",
                'Theta/d': f"{_val('theta') * qty:+.2f}",
                'Vega/1%': f"{_val('vega') * qty:+.2f}",
            })
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping leg {pos} due to error: {e}")
            continue

    return totals, pd.DataFrame(rows)


def theta_decay_path(positions: list, spot: float,
                     r: float = 0.05) -> tuple:
    """Compute portfolio theta as a function of remaining DTE.

    For each leg, vectorizes across all time points in a single call.

    Returns (days_array, daily_theta_array).
    """
    if not positions:
        return np.array([]), np.array([])

    max_dte = max(max(pos.get('dte', 0) for pos in positions), 1)
    days = np.arange(0, max_dte + 1)
    total_theta = np.zeros(len(days))

    for pos in positions:
        try:
            is_call = pos['type'] in ('LC', 'SC')
            is_long = pos['type'] in ('LC', 'LP')
            sign = 1 if is_long else -1
            qty = int(pos['qty']) * sign

            dte_remain = np.maximum(pos['dte'] - days, 0)
            T_arr = np.maximum(dte_remain / 365, _T_MIN)

            g = greeks_vectorized(
                S=float(spot),
                K=float(pos['strike']),
                T=T_arr,
                r=r,
                sigma=float(pos['iv']),
                option_type='call' if is_call else 'put'
            )

            theta_series = np.where(np.isfinite(g['theta']),
                                    g['theta'] * qty, 0.0)
            total_theta += theta_series

        except Exception as e:
            logger.warning(f"theta_decay_path skipping leg: {e}")
            continue

    return days, total_theta

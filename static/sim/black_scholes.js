// black_scholes.js — scalar Black–Scholes price + Greeks.
//
// Port of core/options/greeks/black_scholes.py::greeks_vectorized, kept scalar
// (the simulator evaluates at the current spot). The safety clamps are copied
// VERBATIM from the Python source — they are intentional domain constants
// (see docs/constraints.md §5), not magic numbers.

import { normCdf, normPdf } from './norm.js';

export const T_MIN = 1 / 365;
export const SIGMA_MIN = 0.001;
export const SIGMA_MAX = 20.0;

function _safeInputs(S, K, T, sigma) {
  const valid =
    Number.isFinite(S) && S > 0 &&
    Number.isFinite(K) && K > 0 &&
    Number.isFinite(sigma) && sigma >= SIGMA_MIN && sigma <= SIGMA_MAX &&
    Number.isFinite(T) && T >= T_MIN;
  return {
    valid,
    S: valid ? S : 100,
    K: valid ? K : 100,
    T: valid ? T : 1 / 365,
    sigma: valid ? sigma : 0.2,
  };
}

// Returns the same keys as the Python greeks_vectorized.
export function bsGreeks(S, K, T, r, sigma, optionType = 'call') {
  const { valid, S: S_, K: K_, T: T_, sigma: sigma_ } = _safeInputs(S, K, T, sigma);
  const sqrtT = Math.sqrt(T_);
  const d1 = (Math.log(S_ / K_) + (r + 0.5 * sigma_ * sigma_) * T_) / (sigma_ * sqrtT);
  const d2 = d1 - sigma_ * sqrtT;
  const n_d1 = normPdf(d1);
  const N_d1 = normCdf(d1);
  const N_d2 = normCdf(d2);
  const N_m_d2 = normCdf(-d2);
  const N_m_d1 = normCdf(-d1);
  const disc = Math.exp(-r * T_);

  const gamma = valid ? n_d1 / (S_ * sigma_ * sqrtT) : NaN;
  const vega = valid ? (S_ * n_d1 * sqrtT) / 100 : NaN;

  let delta, theta, price;
  if (optionType === 'call') {
    delta = valid ? N_d1 : NaN;
    theta = valid ? (-(S_ * n_d1 * sigma_) / (2 * sqrtT) - r * K_ * disc * N_d2) / 365 : NaN;
    price = valid ? S_ * N_d1 - K_ * disc * N_d2 : NaN;
  } else {
    delta = valid ? N_d1 - 1 : NaN;
    theta = valid ? (-(S_ * n_d1 * sigma_) / (2 * sqrtT) + r * K_ * disc * N_m_d2) / 365 : NaN;
    price = valid ? K_ * disc * N_m_d2 - S_ * N_m_d1 : NaN;
  }

  const intrinsic = optionType === 'call' ? Math.max(S - K, 0) : Math.max(K - S, 0);
  const timeValue = valid ? Math.max(price - intrinsic, 0) : NaN;

  return {
    delta,
    gamma,
    theta,
    vega,
    bs_price: price,
    intrinsic,
    time_value: timeValue,
  };
}

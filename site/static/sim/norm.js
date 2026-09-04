// norm.js — standard normal PDF/CDF for client-side Black–Scholes.
//
// Pure, dependency-free, zero I/O (Pages-safe). No `fetch`, no DOM.
//
// normCdf uses the Numerical Recipes `erfcc` Chebyshev approximation
// (absolute error ~1.2e-7), matching scipy.stats.norm.cdf closely enough
// for display-precision (1e-6) parity with the Python backend.

function _erfc(x) {
  const z = Math.abs(x);
  const t = 1 / (1 + 0.5 * z);
  const p = [
    -1.26551223, 1.00002368, 0.37409196, 0.09678418,
    -0.18628806, 0.27886807, -1.13520398, 1.48851587,
    -0.82215223, 0.17087277,
  ];
  let poly = p[0] + p[1] * t;
  for (let i = 2; i < p.length; i++) poly += p[i] * Math.pow(t, i);
  const ans = t * Math.exp(-z * z + poly);
  return x >= 0 ? ans : 2 - ans;
}

export function erf(x) {
  return 1 - _erfc(x);
}

export function normCdf(x) {
  // Standard normal CDF: Φ(x) = 0.5 * (1 + erf(x / √2)).
  return 0.5 * (1 + erf(x / Math.SQRT2));
}

export function normPdf(x) {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

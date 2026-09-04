// stats.js — lognormal terminal distribution over S_T and its payoffs.
//
// Port of core/strategies/prob_profit.py (and the E[P&L] integrand that the
// Python side does NOT expose). CRITICAL: E[P&L] integrates pnl(s)*f(s) over
// the FULL grid, while PoP integrates f(s) over only the pnl>0 region — they
// are NOT the same integrand.

import { normPdf } from './norm.js';

// f_S(S) — lognormal pdf of the terminal underlying, w.r.t. S (NOT log-S).
export function lognormalPdf(prices, spot, sigma, dte, r = 0.05) {
  const T = dte / 365;
  const mu = Math.log(spot) + (r - 0.5 * sigma * sigma) * T;
  const sd = sigma * Math.sqrt(T);
  return prices.map((S) => {
    if (!(S > 0)) return 0;
    return normPdf((Math.log(S) - mu) / sd) / sd / S;
  });
}

function _trapzRun(prices, y, from, to) {
  let total = 0;
  for (let k = from; k < to; k++) {
    total += (y[k] + y[k + 1]) * (prices[k + 1] - prices[k]) / 2;
  }
  return total;
}

// Integrate over maximal contiguous runs where mask is true (mirrors
// np.trapz over a boolean-indexed subsequence, preserving x = prices order).
function _trapzMasked(prices, y, mask) {
  let total = 0;
  let i = 0;
  while (i < prices.length) {
    if (!mask[i]) {
      i++;
      continue;
    }
    let j = i;
    while (j + 1 < prices.length && mask[j + 1]) j++;
    total += _trapzRun(prices, y, i, j);
    i = j + 1;
  }
  return total;
}

// Probability of profit under BS lognormal assumption.
export function probProfit(prices, pnl, spot, sigma, dte, r = 0.05) {
  if (!(sigma > 0) || !(dte > 0) || !(spot > 0)) return NaN;
  const pdf = lognormalPdf(prices, spot, sigma, dte, r);
  const mask = pnl.map((p) => p > 0);
  const prob = _trapzMasked(prices, pdf, mask);
  return Math.max(0, Math.min(1, prob));
}

// Expected P&L: ∫ pnl(s) · f(s) ds over the FULL grid (no mask).
export function expectedPnl(prices, pnl, spot, sigma, dte, r = 0.05) {
  if (!(sigma > 0) || !(dte > 0) || !(spot > 0)) return NaN;
  const pdf = lognormalPdf(prices, spot, sigma, dte, r);
  return _trapzRun(prices, pnl.map((p, i) => p * pdf[i]), 0, prices.length - 1);
}

// CDF of S (cumulative trapezoid of the pdf) — used for P5/P95 quantile proxies.
export function cdf(prices, pdf) {
  const c = new Array(prices.length).fill(0);
  let acc = 0;
  for (let k = 0; k < prices.length - 1; k++) {
    acc += (pdf[k] + pdf[k + 1]) * (prices[k + 1] - prices[k]) / 2;
    c[k + 1] = acc;
  }
  return c;
}

// q-th quantile of S (q in [0,1]); returns the S-level for a VaR-style proxy.
export function quantileS(prices, pdf, q) {
  const c = cdf(prices, pdf);
  for (let i = 1; i < prices.length; i++) {
    if (c[i] >= q) {
      const c0 = c[i - 1];
      const c1 = c[i];
      if (c1 === c0) return prices[i];
      const t = (q - c0) / (c1 - c0);
      return prices[i - 1] + t * (prices[i] - prices[i - 1]);
    }
  }
  return prices[prices.length - 1];
}

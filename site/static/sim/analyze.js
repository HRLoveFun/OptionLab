// analyze.js — multi-leg strategy aggregation, mirroring
// core/strategies/analyze.py::analyze_strategy.
//
// Returns the SAME shape the existing browser renderer expects
// (prices, pnl, breakevens, max_profit, max_loss, net_premium, greeks,
// prob_profit), so static/components/payoff_chart.js::renderPayoff works
// unchanged. The naked-leg ±inf logic is copied VERBATIM — including the
// deliberate "long put is NOT treated as unbounded" detail.

import { bsGreeks } from './black_scholes.js';
import { payoffAtExpiration, netPremium, findBreakevens } from './payoff.js';
import { probProfit } from './stats.js';

// Banker's rounding (round half to even) to match Python's round() used by
// core/strategies/greeks.py::net_greeks.
export function round4(x) {
  if (!Number.isFinite(x)) return x;
  const f = 1e4;
  const y = x * f;
  const rb = Math.round(y);
  if (Math.abs(y - rb) === 0.5 && Math.abs(rb % 2) === 1) return (rb - 1) / f;
  return rb / f;
}

export function netGreeks(legs, spot, r = 0.05) {
  const totals = { delta: 0, gamma: 0, theta: 0, vega: 0 };
  for (const leg of legs) {
    const T = Math.max(leg.dte ?? 30, 1) / 365;
    const g = bsGreeks(spot, leg.strike, T, r, leg.iv ?? 0.25, leg.optionType);
    const scale = (leg.side === 'long' ? 1 : -1) * (leg.qty ?? 1);
    for (const k of Object.keys(totals)) {
      const v = g[k];
      if (Number.isFinite(v)) totals[k] += scale * v;
    }
  }
  const out = {};
  for (const k of Object.keys(totals)) out[k] = round4(totals[k]);
  return out;
}

export function analyzeStrategy(legs, spot, opts = {}) {
  const { priceRange = null, nPoints = 401, r = 0.05 } = opts;
  if (!legs || legs.length === 0) throw new Error('analyzeStrategy: legs must not be empty');
  if (!(spot > 0)) throw new Error('analyzeStrategy: spot must be positive');

  const strikes = legs.map((l) => l.strike);
  let lo, hi;
  if (priceRange) {
    [lo, hi] = priceRange;
  } else {
    lo = Math.min(Math.min(...strikes), spot) * 0.85;
    hi = Math.max(Math.max(...strikes), spot) * 1.15;
  }
  lo = Math.max(lo, 0.01);

  const prices = [];
  for (let i = 0; i < nPoints; i++) prices.push(lo + ((hi - lo) * i) / (nPoints - 1));

  const pnl = payoffAtExpiration(legs, prices);

  const edgeLeft = pnl[1] - pnl[0];
  const edgeRight = pnl[pnl.length - 1] - pnl[pnl.length - 2];

  let longCalls = 0, shortCalls = 0, longPuts = 0, shortPuts = 0;
  for (const l of legs) {
    const q = l.qty ?? 1;
    if (l.optionType === 'call') {
      if (l.side === 'long') longCalls += q;
      else shortCalls += q;
    } else {
      if (l.side === 'long') longPuts += q;
      else shortPuts += q;
    }
  }
  const upsideNaked = shortCalls > longCalls;
  const downsideNaked = shortPuts > longPuts;

  let maxProfit = Math.max(...pnl);
  let maxLoss = Math.min(...pnl);
  if (upsideNaked && edgeRight < 0) maxLoss = -Infinity;
  if (downsideNaked && edgeLeft > 0) maxLoss = -Infinity;
  if (longCalls > shortCalls && edgeRight > 0) maxProfit = Infinity;

  const dteMax = Math.max(...legs.map((l) => l.dte ?? 30), 30);
  let ivNum = 0, ivDen = 0;
  for (const l of legs) {
    ivNum += (l.iv ?? 0.25) * (l.qty ?? 1);
    ivDen += l.qty ?? 1;
  }
  const ivAvg = ivDen ? ivNum / ivDen : 0;

  return {
    prices,
    pnl,
    breakevens: findBreakevens(prices, pnl),
    maxProfit,
    maxLoss,
    netPremium: netPremium(legs),
    greeks: netGreeks(legs, spot, r),
    probProfit: probProfit(prices, pnl, spot, ivAvg, dteMax, r),
  };
}

// sim.parity.test.js — assert the browser sim matches the REAL Python backend.
//
// No mocked data: fixtures come from scripts/gen_sim_golden.py, which calls the
// actual core/strategies/* and core/options/greeks/* implementations. Tolerance
// is 1e-6 (display precision); greeks are compared at 1e-4 because both sides
// round to 4 dp.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { analyzeStrategy } from '../../../static/sim/analyze.js';
import { bsGreeks } from '../../../static/sim/black_scholes.js';
import { expectedPnl } from '../../../static/sim/stats.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(
  readFileSync(resolve(__dirname, 'golden.json'), 'utf-8'),
);

// Decode the inf/-inf/nan markers the generator emits.
function num(x) {
  if (x === 'Infinity') return Infinity;
  if (x === '-Infinity') return -Infinity;
  if (x === 'NaN') return NaN;
  return x;
}

function close(a, b, tol = 1e-6) {
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return a === b;
  return Math.abs(a - b) <= tol;
}

function arrClose(a, b, tol = 1e-6) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (!close(num(a[i]), num(b[i]), tol)) return false;
  }
  return true;
}

// golden.json stores Python snake_case (option_type); the JS API uses optionType.
function toJsLeg(l) {
  return { ...l, optionType: l.option_type ?? l.optionType };
}

describe('analyzeStrategy parity (browser vs Python)', () => {
  for (const c of golden.analyze) {
    it(`matches Python for "${c.name}"`, () => {
      const res = analyzeStrategy(c.legs.map(toJsLeg), c.spot, { nPoints: golden.meta.n_points, r: c.r });
      const g = c.result;

      expect(arrClose(res.prices, g.prices, 1e-9)).toBe(true);
      expect(arrClose(res.pnl, g.pnl, 1e-6)).toBe(true);
      expect(res.breakevens.length).toBe(g.breakevens.length);
      for (let i = 0; i < res.breakevens.length; i++) {
        expect(Math.abs(res.breakevens[i] - num(g.breakevens[i]))).toBeLessThan(1e-6);
      }
      expect(close(res.maxProfit, num(g.max_profit))).toBe(true);
      expect(close(res.maxLoss, num(g.max_loss))).toBe(true);
      expect(Math.abs(res.netPremium - num(g.net_premium))).toBeLessThan(1e-9);

      for (const k of Object.keys(g.greeks)) {
        expect(Math.abs(res.greeks[k] - num(g.greeks[k]))).toBeLessThan(1e-4);
      }

      expect(close(res.probProfit, num(g.prob_profit), 1e-5)).toBe(true);
      expect(close(res.probProfit, num(g.prob_profit), 1e-5)).toBe(true);

      const ep = expectedPnl(
        res.prices,
        res.pnl,
        c.spot,
        c.legs.reduce((a, l) => a + l.iv * l.qty, 0) /
          Math.max(c.legs.reduce((a, l) => a + l.qty, 0), 1),
        Math.max(...c.legs.map((l) => l.dte), 30),
        c.r,
      );
      expect(close(ep, num(g.expected_pnl), 1e-4)).toBe(true);
    });
  }
});

describe('bsGreeks parity (browser vs Python)', () => {
  for (const c of golden.bs) {
    it(`matches Python for "${c.name}"`, () => {
      const g = bsGreeks(c.S, c.K, c.T, c.r, c.sigma, c.option_type);
      const e = c.greeks;
      // bs_price / time_value subtract two ~50-unit terms that each carry the
      // ~1e-7 erf error, so they only match to ~1e-5 (still 5+ significant figs).
      const tol = (k) => (k === 'bs_price' || k === 'time_value' ? 1e-5 : 1e-6);
      for (const k of Object.keys(e)) {
        const a = g[k];
        const b = num(e[k]);
        if (Number.isNaN(a) || Number.isNaN(b)) {
          expect(Number.isNaN(a) && Number.isNaN(b)).toBe(true);
        } else {
          expect(Math.abs(a - b)).toBeLessThan(tol(k));
        }
      }
    });
  }
});

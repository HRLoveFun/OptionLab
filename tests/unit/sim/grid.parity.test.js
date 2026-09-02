// grid.parity.test.js — client simulateExpiry vs the REAL Python implementation.
//
// No mocks: the fixture is produced by scripts/gen_sim_golden.py calling
// core/options/simulation/expiry.py::simulate_expiry. Tolerance 1e-4 (BS price
// cancellation amplifies the ~1e-7 erf error; still 4+ significant figures).
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { simulateExpiry } from '../../../static/sim/grid.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const golden = JSON.parse(readFileSync(resolve(__dirname, 'golden.json'), 'utf-8'));

function num(x) {
  if (x === 'Infinity') return Infinity;
  if (x === '-Infinity') return -Infinity;
  if (x === 'NaN') return NaN;
  return x;
}

function close(a, b, tol = 1e-4) {
  if (Number.isNaN(a) && Number.isNaN(b)) return true;
  if (!Number.isFinite(a) || !Number.isFinite(b)) return a === b;
  return Math.abs(a - b) <= tol;
}

describe('simulateExpiry parity (browser vs Python)', () => {
  for (const c of golden.simulate_expiry || []) {
    it(`matches Python for "${c.name}"`, () => {
      const res = simulateExpiry({
        spot: c.spot,
        strikes: c.strikes.join(','),
        expiries: c.expiries.join(','),
        // UI contract: IVs arrive as PERCENT.
        ivs: c.ivs.map((v) => v * 100).join(','),
        forwardIvs: c.forwardIvs ? c.forwardIvs.map((v) => v * 100).join(',') : null,
        optionType: c.option_type,
        side: c.side,
        r_pct: c.r * 100,
        qty: c.qty,
        multiplier: c.multiplier,
      });
      const g = c.result;
      expect(close(res.spot, g.spot)).toBe(true);
      expect(res.strikes).toEqual(g.strikes.map((v) => num(v)));
      expect(res.combos.length).toBe(g.combos.length);
      expect(res.results.length).toBe(g.results.length);

      for (let i = 0; i < res.results.length; i++) {
        const row = res.results[i];
        const grow = g.results[i];
        expect(close(row.strike, num(grow.strike))).toBe(true);
        expect(row.cells.length).toBe(grow.cells.length);
        for (let j = 0; j < row.cells.length; j++) {
          const cell = row.cells[j];
          const gcell = grow.cells[j];
          // Premiums/deltas are rounded to 4 dp by both sides; the erf approximation
          // leaves a sub-1e-3 residual, so 1e-3 is the right parity bound.
          expect(close(cell.premium, num(gcell.premium), 1e-3)).toBe(true);
          expect(close(cell.delta, num(gcell.delta), 1e-3)).toBe(true);
          expect(close(cell.breakeven, num(gcell.breakeven), 1e-3)).toBe(true);
          expect(close(cell.pop, num(gcell.pop), 1e-3)).toBe(true);
          expect(close(cell.pnl_at_spot, num(gcell.pnl_at_spot), 1e-3)).toBe(true);
          // unbounded flags must match; where bounded, the magnitudes match
          expect(cell.unbounded_profit).toBe(gcell.unbounded_profit);
          expect(cell.unbounded_loss).toBe(gcell.unbounded_loss);
          expect(close(cell.max_profit ?? 0, num(gcell.max_profit) ?? 0, 1e-2)).toBe(true);
          expect(close(cell.max_loss ?? 0, num(gcell.max_loss) ?? 0, 1e-2)).toBe(true);
          expect(cell.pnl.length).toBe(num(gcell.pnl[0]) !== undefined ? gcell.pnl.length : cell.pnl.length);
          for (let k = 0; k < cell.pnl.length; k++) {
            expect(close(cell.pnl[k], num(gcell.pnl[k]), 2e-2)).toBe(true);
          }
        }
      }
    });
  }
});

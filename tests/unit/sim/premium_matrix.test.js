// premium_matrix.test.js — premium-rate matrix engine.
//
// No mocked data: every assertion either checks a closed-form identity
// (put–call parity, the premium-rate definitions, the σ geometry) or compares
// the optimised hot path against the existing bsGreeks implementation, which
// is the project's established pricing source of truth.
import { describe, it, expect } from 'vitest';

import { bsGreeks } from '../../../static/sim/black_scholes.js';
import {
  buildPremiumMatrix,
  buildStrikeLadder,
  fillPrice,
  normalizeDtes,
  premiumRate,
  sigmaMove,
  sigmaMultiple,
  DEFAULT_DTES,
} from '../../../static/sim/premium_matrix.js';

const SPOT = 100;
const IV = 25;
const RF = 3;

function matrix(overrides) {
  return buildPremiumMatrix({ spot: SPOT, ivPct: IV, rPct: RF, spreadPct: 0, ...overrides });
}

function sortedUniqueGap(values) {
  let minGap = Infinity;
  for (let i = 1; i < values.length; i++) {
    if (values[i] <= values[i - 1]) return 0;
    minGap = Math.min(minGap, values[i] - values[i - 1]);
  }
  return minGap;
}

describe('buildStrikeLadder', () => {
  it('rounds to integers, dedupes and keeps a 1-wide minimum gap at spot 100', () => {
    const { strikes, decimals, step } = buildStrikeLadder({ spot: 100 });
    expect(decimals).toBe(0);
    expect(step).toBe(1);
    expect(strikes[0]).toBe(80);
    expect(strikes[strikes.length - 1]).toBe(120);
    expect(strikes).toHaveLength(41);
    expect(strikes.every((k) => Number.isInteger(k))).toBe(true);
    expect(new Set(strikes).size).toBe(strikes.length);
    expect(sortedUniqueGap(strikes)).toBeGreaterThanOrEqual(1);
  });

  it('never collapses for low-priced underlyings', () => {
    for (const spot of [1, 5, 12, 47, 680]) {
      const { strikes, decimals } = buildStrikeLadder({ spot });
      expect(strikes.length).toBeGreaterThanOrEqual(5);
      expect(new Set(strikes).size).toBe(strikes.length);
      expect(sortedUniqueGap(strikes)).toBeGreaterThanOrEqual(Math.pow(10, -decimals) - 1e-9);
      expect(strikes.every((k) => k > 0)).toBe(true);
    }
  });

  it('honours a custom range and target row count', () => {
    const { strikes } = buildStrikeLadder({ spot: 100, rangePct: 0.1, targetRows: 11 });
    expect(strikes[0]).toBe(90);
    expect(strikes[strikes.length - 1]).toBe(110);
    expect(strikes.length).toBeLessThanOrEqual(18);
  });

  it('rejects unusable inputs', () => {
    expect(() => buildStrikeLadder({ spot: 0 })).toThrow(/positive/);
    expect(() => buildStrikeLadder({ spot: 100, rangePct: 0 })).toThrow(/rangePct/);
    expect(() => buildStrikeLadder({ spot: 100, rangePct: 3 })).toThrow(/rangePct/);
  });
});

describe('sigma geometry', () => {
  it('one year of 25% vol is a 25-point move on a 100 spot', () => {
    expect(sigmaMove(100, 0.25, 365)).toBeCloseTo(25, 12);
  });

  it('one sigma-move away from spot is a multiple of 1', () => {
    expect(sigmaMultiple(100, 125, 0.25, 365)).toBeCloseTo(1, 12);
    expect(sigmaMultiple(100, 75, 0.25, 365)).toBeCloseTo(-1, 12);
  });

  it('scales with sqrt(time)', () => {
    expect(sigmaMove(100, 0.25, 91.25)).toBeCloseTo(12.5, 10);
  });

  it('is undefined for degenerate inputs', () => {
    expect(Number.isNaN(sigmaMove(100, 0, 30))).toBe(true);
    expect(Number.isNaN(sigmaMove(100, 0.25, 0))).toBe(true);
    expect(Number.isNaN(sigmaMultiple(100, 110, 0.25, 0))).toBe(true);
  });
});

describe('fillPrice / premiumRate', () => {
  it('applies half the spread around the mid price', () => {
    expect(fillPrice(2, 4, 'buy')).toBeCloseTo(2 * 1.02, 12);
    expect(fillPrice(2, 4, 'sell')).toBeCloseTo(2 * 0.98, 12);
    expect(fillPrice(2, 0, 'sell')).toBe(2);
    expect(fillPrice(2, 1000, 'sell')).toBe(1); // clamped to 100%
  });

  it('uses the breakeven-move definitions verbatim', () => {
    // call: (K + P − S) / S ;  put: (S − K + P) / S
    expect(premiumRate(100, 105, 2.5, 'call')).toBeCloseTo(0.075, 12);
    expect(premiumRate(100, 95, 2.5, 'put')).toBeCloseTo(0.075, 12);
    expect(Number.isNaN(premiumRate(0, 100, 1, 'call'))).toBe(true);
  });
});

describe('buildPremiumMatrix — pricing', () => {
  it('matches bsGreeks for every cell (parity path off)', () => {
    const m = matrix({ putViaParity: false });
    const r = RF / 100;
    const iv = IV / 100;
    for (const row of m.rows) {
      for (const cell of row.cells) {
        const T = cell.dte / 365;
        const call = bsGreeks(SPOT, row.strike, T, r, iv, 'call').bs_price;
        const put = bsGreeks(SPOT, row.strike, T, r, iv, 'put').bs_price;
        expect(cell.call.mid).toBeCloseTo(call, 5);
        expect(cell.put.mid).toBeCloseTo(put, 5);
      }
    }
  });

  it('put–call parity path agrees with direct pricing to 1e-12', () => {
    const fast = matrix({ putViaParity: true });
    const direct = matrix({ putViaParity: false });
    for (let i = 0; i < fast.rows.length; i++) {
      for (let j = 0; j < fast.columns.length; j++) {
        const a = fast.rows[i].cells[j];
        const b = direct.rows[i].cells[j];
        expect(Math.abs(a.call.mid - b.call.mid)).toBeLessThan(1e-12);
        expect(Math.abs(a.put.mid - b.put.mid)).toBeLessThan(1e-12);
      }
    }
  });

  it('satisfies put–call parity in the emitted cells', () => {
    const m = matrix();
    const r = RF / 100;
    for (const row of m.rows) {
      for (const cell of row.cells) {
        const lhs = cell.call.mid - cell.put.mid;
        const rhs = SPOT - row.strike * Math.exp(-r * (cell.dte / 365));
        // Residuals only come from the 6-dp rounding of the emitted mids.
        expect(Math.abs(lhs - rhs)).toBeLessThan(2e-6);
      }
    }
  });

  it('prices the ATM 30-day call in a sane band', () => {
    const m = matrix();
    const atm = m.rows[m.atm_index];
    expect(atm.strike).toBe(100);
    const col = m.columns.findIndex((c) => Math.abs(c.dte - 30) <= 1);
    const cell = atm.cells[col];
    // BS(100, 100, 30/365, 3%, 25%) ≈ 2.98 → 2.98% of spot
    expect(cell.call.mid).toBeGreaterThan(2.5);
    expect(cell.call.mid).toBeLessThan(3.5);
    expect(cell.call.premium_rate).toBeCloseTo(cell.call.mid / SPOT, 6);
  });
});

describe('buildPremiumMatrix — structure', () => {
  it('lays out 18 DTE columns and one cell per column', () => {
    const m = matrix();
    expect(m.columns.map((c) => c.dte)).toEqual(DEFAULT_DTES);
    expect(m.columns).toHaveLength(18);
    expect(m.rows.every((r) => r.cells.length === m.columns.length)).toBe(true);
  });

  it('exposes per-column sigma moves that grow with sqrt(time)', () => {
    const m = matrix();
    for (let i = 1; i < m.columns.length; i++) {
      expect(m.columns[i].sigma_move).toBeGreaterThan(m.columns[i - 1].sigma_move);
    }
    expect(m.columns[0].sigma_pct).toBeCloseTo(0.25 * Math.sqrt(1 / 365), 6);
  });

  it('point the row header sigma at the column nearest 30 DTE', () => {
    const m = matrix();
    expect(m.columns[m.ref_column_index].dte).toBe(31);
  });

  it('sorts rows ascending and marks the ATM row', () => {
    const m = matrix();
    expect(sortedUniqueGap(m.rows.map((r) => r.strike))).toBeGreaterThan(0);
    expect(m.rows[m.atm_index].strike).toBe(100);
    expect(m.rows[0].moneyness_pct).toBeCloseTo(-0.2, 8);
    expect(m.rows[m.rows.length - 1].moneyness_pct).toBeCloseTo(0.2, 8);
  });

  it('is memoised per input signature', () => {
    const a = matrix();
    const b = matrix();
    expect(b).toBe(a);
    const c = matrix({ ivPct: 30 });
    expect(c).not.toBe(a);
  });
});

describe('buildPremiumMatrix — shape of the rates', () => {
  it('call rate rises with strike, put rate falls with strike', () => {
    const m = matrix();
    const col = m.ref_column_index;
    for (let i = 1; i < m.rows.length; i++) {
      const prev = m.rows[i - 1].cells[col];
      const cur = m.rows[i].cells[col];
      expect(cur.call.premium_rate).toBeGreaterThan(prev.call.premium_rate);
      expect(cur.put.premium_rate).toBeLessThan(prev.put.premium_rate);
    }
  });

  it('rate equals the breakeven move implied by the displayed fill', () => {
    const m = matrix({ spreadPct: 6, perspective: 'buy' });
    for (const row of m.rows) {
      for (const cell of row.cells) {
        expect(cell.call.premium_rate).toBeCloseTo((row.strike + cell.call.fill - SPOT) / SPOT, 8);
        expect(cell.put.premium_rate).toBeCloseTo((SPOT - row.strike + cell.put.fill) / SPOT, 8);
        // Sub-cent premiums round to the same 6-dp value, so only cells with
        // a material premium can show a strict ask > mid gap.
        expect(cell.call.fill).toBeGreaterThanOrEqual(cell.call.mid);
        if (cell.call.mid > 0.01) expect(cell.call.fill).toBeGreaterThan(cell.call.mid);
      }
    }
  });

  it('selling through the spread lowers every rate vs buying', () => {
    const buy = matrix({ spreadPct: 8, perspective: 'buy' });
    const sell = matrix({ spreadPct: 8, perspective: 'sell' });
    for (let i = 0; i < buy.rows.length; i++) {
      for (let j = 0; j < buy.columns.length; j++) {
        // Zero-time-value cells sit on intrinsic and are spread-invariant.
        expect(sell.rows[i].cells[j].call.premium_rate)
          .toBeLessThanOrEqual(buy.rows[i].cells[j].call.premium_rate);
        expect(sell.rows[i].cells[j].put.fill)
          .toBeLessThanOrEqual(buy.rows[i].cells[j].put.fill);
      }
    }
    const j = buy.ref_column_index;
    const atm = buy.atm_index;
    expect(sell.rows[atm].cells[j].call.premium_rate)
      .toBeLessThan(buy.rows[atm].cells[j].call.premium_rate);
    expect(sell.rows[atm].cells[j].put.fill)
      .toBeLessThan(buy.rows[atm].cells[j].put.fill);
  });

  it('higher IV raises every premium rate', () => {
    const low = matrix({ ivPct: 15 });
    const high = matrix({ ivPct: 45 });
    for (let i = 0; i < low.rows.length; i++) {
      for (let j = 0; j < low.columns.length; j++) {
        expect(high.rows[i].cells[j].call.mid).toBeGreaterThanOrEqual(low.rows[i].cells[j].call.mid);
        expect(high.rows[i].cells[j].call.premium_rate)
          .toBeGreaterThanOrEqual(low.rows[i].cells[j].call.premium_rate);
      }
    }
    // Away from the intrinsic-only corners vol strictly increases the premium.
    const j = low.ref_column_index;
    const atm = low.atm_index;
    expect(high.rows[atm].cells[j].call.mid).toBeGreaterThan(low.rows[atm].cells[j].call.mid);
    expect(high.rows[atm].cells[j].call.premium_rate)
      .toBeGreaterThan(low.rows[atm].cells[j].call.premium_rate);
  });
});

describe('buildPremiumMatrix — inputs and boundaries', () => {
  it('normalises DTE tokens', () => {
    expect(normalizeDtes('30, 7, 30, 0, 9999, abc')).toEqual([7, 30]);
    expect(normalizeDtes([5, 5, 10])).toEqual([5, 10]);
  });

  it('rejects out-of-range inputs', () => {
    expect(() => matrix({ spot: -1 })).toThrow(/spot/);
    expect(() => matrix({ ivPct: 0 })).toThrow(/ivPct/);
    expect(() => matrix({ ivPct: 900 })).toThrow(/ivPct/);
    expect(() => matrix({ rPct: 99 })).toThrow(/rPct/);
    expect(() => matrix({ dtes: [] })).toThrow(/DTE/);
  });

  it('prices the extreme corners of the allowed input space', () => {
    const m = buildPremiumMatrix({
      spot: 100, ivPct: 0.1, rPct: -5, spreadPct: 100, perspective: 'sell', dtes: [1, 3650],
    });
    expect(m.columns).toHaveLength(2);
    for (const row of m.rows) {
      for (const cell of row.cells) {
        expect(Number.isFinite(cell.call.mid)).toBe(true);
        expect(Number.isFinite(cell.put.mid)).toBe(true);
        expect(Number.isFinite(cell.call.premium_rate)).toBe(true);
        expect(Number.isFinite(cell.sigma_mult)).toBe(true);
      }
    }
  });
});

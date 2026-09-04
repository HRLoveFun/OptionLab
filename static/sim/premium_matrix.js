// premium_matrix.js — premium-rate matrix engine (strikes × DTE).
//
// Pure, zero I/O (Pages-safe): no network, no DOM, no market data. Every cell
// is priced with Black–Scholes from caller-supplied inputs — the panel is a
// hypothetical-input calculator by design, so no real quote is ever read.
//
// Cell semantics (per spec):
//   call premium rate = (K + P − S) / S   — rally needed to reach breakeven
//   put  premium rate = (S − K + P) / S   — decline needed to reach breakeven
// where P is the FILL price: mid from Black–Scholes, moved off the mid by half
// the bid-ask spread — buy fills at the ask (mid + offset), sell fills at the
// bid (mid − offset), where
//   offset = max(mid × s / 200, MIN_SPREAD_ABS)
// i.e. the spread's dollar effect is floored at one cent (a penny is the
// smallest tick an option trades on), so a cheap wing premium still shows a
// real gap between the two sides. Both perspectives share the same rate
// formulas.
//
// Perf notes (the grid is ~41 rows × 18 columns ≈ 738 cells):
//   - per COLUMN: √T and e^(−rT) are computed once and cached (18×, not 738×)
//   - per ROW:    ln(S/K) is computed once and reused across all columns
//   - per CELL:   only d1/d2 and two normCdf calls; the put comes from
//                 put–call parity (P = C − S + K·e^(−rT)), so 2 normCdf per
//                 cell instead of the ~10 that bsGreeks() spends on call+put
//   - the finished matrix is memoised per input signature, so toggles,
//     hover and re-renders never recompute anything
import { normCdf } from './norm.js';
import { bsGreeks, T_MIN, SIGMA_MIN, SIGMA_MAX } from './black_scholes.js';

// Horizontal axis: 1–90 DTE in 5-day steps (1, 6, 11, … 86).
export const DEFAULT_RANGE_PCT = 0.2;
export const DEFAULT_TARGET_ROWS = 41;
export const MIN_DTE = 1 / 24;
export const MAX_DTE = 3650;
export const MIN_IV_PCT = 0.1;
export const MAX_IV_PCT = 500;
export const MIN_R_PCT = -5;
export const MAX_R_PCT = 50;
export const MIN_SPREAD_PCT = 1;
export const MAX_SPREAD_PCT = 100;
// Bid-ask width as a percent of mid, range 1 - 100. Floor on the spread's
// DOLLAR effect (not on the input): max(mid × spreadPct / 200, MIN_SPREAD_ABS).
// A 6% spread on a 5-cent premium is 0.15 of a cent, which rounds to nothing
// and would make buy and sell print the same number — one cent is the smallest
// real tick.
export const MIN_SPREAD_ABS = 0.01;
export const REF_DTE_DEFAULT = 30;

// Candidate strike steps, coarsest that still keeps the ladder readable.
const _TICKS = [
  0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000,
];

const _CACHE_LIMIT = 24;
const _memo = new Map();       // input signature -> finished matrix
const _ladderCache = new Map(); // (spot|range|target) -> strike ladder
const _columnCache = new Map(); // (dte|r) -> { T, sqrtT, disc }

function _cachePut(map, key, value) {
  if (map.size >= _CACHE_LIMIT) map.delete(map.keys().next().value);
  map.set(key, value);
  return value;
}

function _r(v, digits) {
  const n = Number(v);
  if (!Number.isFinite(n)) return NaN;
  const f = Math.pow(10, digits);
  return Math.round(n * f) / f;
}

/* -- input normalisation --------------------------------------------- */

export function normalizeDtes(values) {
  const raw = Array.isArray(values) ? values : String(values ?? '').split(',');
  const out = [];
  const seen = new Set();
  for (const v of raw) {
    // DTE is fractional (intraday remainder to the 16:00 ET close) — keep the
    // float, only the one-hour floor and the 3650-day cap apply.
    const d = Number(v);
    if (!Number.isFinite(d) || d < MIN_DTE || d > MAX_DTE || seen.has(d)) continue;
    seen.add(d);
    out.push(d);
  }
  return out.sort((a, b) => a - b);
}

/* -- strike ladder ---------------------------------------------------- */

// Rounding precision for a ladder: whole dollars for normal underlyings,
// finer steps for penny stocks so the ladder never collapses to one rung.
function _decimalsFor(spot) {
  if (spot >= 20) return 0;
  if (spot >= 5) return 1;
  return 2;
}

export function buildStrikeLadder(opts) {
  const {
    spot,
    rangePct = DEFAULT_RANGE_PCT,
    targetRows = DEFAULT_TARGET_ROWS,
  } = opts || {};

  const S = Number(spot);
  if (!Number.isFinite(S) || S <= 0) throw new Error('spot must be a positive number');
  const range = Number(rangePct);
  if (!Number.isFinite(range) || range <= 0 || range > 2) {
    throw new Error('rangePct must be a number in (0, 2]');
  }
  const target = Math.min(Math.max(Math.round(Number(targetRows)) || DEFAULT_TARGET_ROWS, 3), 401);

  const key = `${S}|${range}|${target}`;
  const cached = _ladderCache.get(key);
  if (cached) return cached;

  const lo = S * (1 - range);
  const hi = S * (1 + range);
  const span = hi - lo;
  const decimals = _decimalsFor(S);
  const minStep = Math.pow(10, -decimals);

  // Coarsest standard tick that still lands near the requested row count.
  const ideal = span / (target - 1);
  let step = minStep;
  for (const t of _TICKS) {
    if (t < minStep) continue;
    if (t <= ideal) step = t;
    else break;
  }
  // TRADEOFF: never let the ladder balloon past ~1.6× the target row count —
  // a readable matrix beats an exhaustive one.
  if (span / step + 1 > target * 1.6) step = Math.max(minStep, step * 2);

  const seen = new Set();
  const strikes = [];
  const count = Math.floor(span / step + 1e-9);
  for (let i = 0; i <= count; i++) {
    const k = Number((lo + i * step).toFixed(decimals));
    if (k <= 0 || seen.has(k)) continue;   // rounding dedupe enforces the min gap
    seen.add(k);
    strikes.push(k);
  }

  return _cachePut(_ladderCache, key, { strikes, decimals, step });
}

/* -- sigma geometry --------------------------------------------------- */

// Terminal 1σ move of the underlying over `dte` calendar days.
export function sigmaMove(spot, ivDec, dte) {
  const S = Number(spot);
  const iv = Number(ivDec);
  const d = Number(dte);
  if (!(S > 0) || !(iv > 0) || !(d > 0)) return NaN;
  return S * iv * Math.sqrt(d / 365);
}

// Moneyness expressed in standard deviations: (K − S) / (S·σ·√T).
export function sigmaMultiple(spot, strike, ivDec, dte) {
  const move = sigmaMove(spot, ivDec, dte);
  if (!(move > 0)) return NaN;
  return (Number(strike) - Number(spot)) / move;
}

/* -- pricing helpers -------------------------------------------------- */

export function fillPrice(mid, spreadPct, perspective) {
  const m = Number(mid);
  if (!Number.isFinite(m)) return NaN;
  const s = Math.min(Math.max(Number(spreadPct) || 0, MIN_SPREAD_PCT), MAX_SPREAD_PCT);
  // Spread is a PERCENT of mid and half of it moves the fill; the dollar
  // result is then floored at one cent (see MIN_SPREAD_ABS).
  const offset = Math.max((m * s) / 200, MIN_SPREAD_ABS);
  const fill = perspective === 'sell' ? m - offset : m + offset;
  return Math.max(fill, 0);
}

export function premiumRate(spot, strike, price, type) {
  const S = Number(spot);
  const K = Number(strike);
  const P = Number(price);
  if (!(S > 0) || !Number.isFinite(K) || !Number.isFinite(P)) return NaN;
  return type === 'put' ? (S - K + P) / S : (K + P - S) / S;
}

/* -- pricing hot path ------------------------------------------------- */

function _columnMeta(dte, r) {
  const key = `${dte}|${r}`;
  const cached = _columnCache.get(key);
  if (cached) return cached;
  const T = dte / 365;
  return _cachePut(_columnCache, key, { T, sqrtT: Math.sqrt(T), disc: Math.exp(-r * T) });
}

// Black–Scholes call with the per-row / per-column invariants already folded
// out. Mirrors black_scholes.js::bsGreeks; parity is asserted in unit tests.
function _bsCallFast(S, K, T, r, sigma, lnSK, sqrtT, disc) {
  if (!(sigma >= SIGMA_MIN && sigma <= SIGMA_MAX) || !(T >= T_MIN) || !(S > 0) || !(K > 0)) {
    return NaN;
  }
  const vol = sigma * sqrtT;
  const d1 = (lnSK + (r + 0.5 * sigma * sigma) * T) / vol;
  const d2 = d1 - vol;
  return S * normCdf(d1) - K * disc * normCdf(d2);
}

/* -- matrix assembly -------------------------------------------------- */

export function buildPremiumMatrix(opts) {
  const {
    spot,
    ivPct = 25,
    rPct = 3,
    spreadPct = 0,
    perspective = 'buy',
    dtes = null,
    expirations = null,
    rangePct = DEFAULT_RANGE_PCT,
    targetRows = DEFAULT_TARGET_ROWS,
    putViaParity = true,
  } = opts || {};

  const S = Number(spot);
  if (!Number.isFinite(S) || S <= 0) throw new Error('spot must be a positive number');

  const ivPctN = Number(ivPct);
  if (!Number.isFinite(ivPctN) || ivPctN < MIN_IV_PCT || ivPctN > MAX_IV_PCT) {
    throw new Error(`ivPct must be a number between ${MIN_IV_PCT} and ${MAX_IV_PCT}`);
  }
  const rPctN = Number(rPct);
  if (!Number.isFinite(rPctN) || rPctN < MIN_R_PCT || rPctN > MAX_R_PCT) {
    throw new Error(`rPct must be a number between ${MIN_R_PCT} and ${MAX_R_PCT}`);
  }
  const spreadN = Math.min(Math.max(Number(spreadPct) || 0, MIN_SPREAD_PCT), MAX_SPREAD_PCT);
  const side = perspective === 'sell' ? 'sell' : 'buy';
  const rawDtes = expirations ? expirations.map((e) => e.dte) : dtes;
  const dteList = normalizeDtes(rawDtes);
  if (!dteList.length) {
    throw new Error(`at least one DTE above ${MIN_DTE} and up to ${MAX_DTE} is required`);
  }

  const iv = ivPctN / 100;
  const r = rPctN / 100;
  const range = Number(rangePct) || DEFAULT_RANGE_PCT;
  const target = Math.round(Number(targetRows)) || DEFAULT_TARGET_ROWS;

  // Carry any per-expiration metadata (date / kind / cycle) onto the columns so
  // the UI can label standard vs daily series. Keyed by dte for O(1) lookup.
  const metaByDte = new Map();
  if (expirations) {
    for (const e of expirations) {
      // Keyed by the exact (fractional) dte — same number the calendar emitted.
      const d = Number(e.dte);
      if (Number.isFinite(d)) metaByDte.set(d, e);
    }
  }

  const signature = [
    S, ivPctN, rPctN, spreadN, side, range, target, putViaParity ? 1 : 0,
    expirations ? 'E' : '', dteList.join(','),
  ].join('|');
  const hit = _memo.get(signature);
  if (hit) return hit;

  const ladder = buildStrikeLadder({ spot: S, rangePct: range, targetRows: target });
  const strikes = ladder.strikes;
  if (strikes.length < 2) {
    throw new Error('strike ladder collapsed to a single rung — widen the strike range');
  }

  const columns = dteList.map((dte) => {
    const meta = _columnMeta(dte, r);
    const ex = metaByDte.get(dte) || {};
    return {
      dte,
      date: ex.date ?? null,
      kind: ex.kind ?? null,
      cycle: ex.cycle ?? null,
      sigma_move: _r(S * iv * meta.sqrtT, 6),
      sigma_pct: _r(iv * meta.sqrtT, 8),
    };
  });

  let atmIndex = 0;
  let atmGap = Infinity;
  const rows = strikes.map((K, i) => {
    const gap = Math.abs(K - S);
    if (gap < atmGap) { atmGap = gap; atmIndex = i; }
    const lnSK = Math.log(S / K);
    const cells = columns.map((col) => {
      const meta = _columnMeta(col.dte, r);
      const callMid = putViaParity
        ? _bsCallFast(S, K, meta.T, r, iv, lnSK, meta.sqrtT, meta.disc)
        : bsGreeks(S, K, meta.T, r, iv, 'call').bs_price;
      // Put–call parity: P = C − S + K·e^(−rT). Saves a second normCdf pair.
      const putMid = putViaParity
        ? callMid - S + K * meta.disc
        : bsGreeks(S, K, meta.T, r, iv, 'put').bs_price;
      const callFill = fillPrice(callMid, spreadN, side);
      const putFill = fillPrice(putMid, spreadN, side);
      return {
        dte: col.dte,
        sigma_mult: _r(sigmaMultiple(S, K, iv, col.dte), 4),
        call: {
          mid: _r(callMid, 6),
          fill: _r(callFill, 6),
          premium_rate: _r(premiumRate(S, K, callFill, 'call'), 8),
        },
        put: {
          mid: _r(putMid, 6),
          fill: _r(putFill, 6),
          premium_rate: _r(premiumRate(S, K, putFill, 'put'), 8),
        },
      };
    });
    return { strike: K, moneyness_pct: _r(K / S - 1, 8), cells };
  });

  let refIndex = 0;
  let refGap = Infinity;
  columns.forEach((col, i) => {
    const gap = Math.abs(col.dte - REF_DTE_DEFAULT);
    if (gap < refGap) { refGap = gap; refIndex = i; }
  });

  const result = {
    spot: S,
    iv_pct: ivPctN,
    r_pct: rPctN,
    spread_pct: spreadN,
    perspective: side,
    range_pct: range,
    target_rows: target,
    decimals: ladder.decimals,
    strike_step: ladder.step,
    columns,
    rows,
    atm_index: atmIndex,
    ref_column_index: refIndex,
  };

  return _cachePut(_memo, signature, result);
}

// Expose for the dashboard tab (classic script) and the standalone Pages site.
if (typeof window !== 'undefined') {
  window.PremiumMatrix = {
    buildPremiumMatrix,
    buildStrikeLadder,
    normalizeDtes,
    sigmaMove,
    sigmaMultiple,
    fillPrice,
    premiumRate,
    DEFAULT_RANGE_PCT,
    DEFAULT_TARGET_ROWS,
    REF_DTE_DEFAULT,
  };
}

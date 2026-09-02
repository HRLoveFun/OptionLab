// grid.js — client-side mirror of core/options/simulation/expiry.py::simulate_expiry.
//
// Produces the EXACT payload shape that static/simulation.js renders (so the
// existing dashboard tab runs with zero backend), and adds Decision B: a
// separate forward-vol dimension (entry IV prices the premium; forward IV drives
// the distribution / PoP / E[P&L]). When forward IVs are omitted the two are
// linked (IV fairly priced), matching the backend's historical behaviour.
//
// Pure, dependency-free, zero I/O — Pages-safe. Reuses the Phase-1 modules.
import { bsGreeks } from './black_scholes.js';
import { normCdf } from './norm.js';
import { probProfit, expectedPnl } from './stats.js';

export const SIM_MIN_DTE = 1;
export const SIM_MAX_DTE = 3650;
export const SIM_MIN_IV = 0.001;
export const SIM_MAX_IV = 5.0;
const ISO_RE = /^\d{4}-\d{2}-\d{2}$/;

function _parseList(str, fallback) {
  if (!str || !String(str).trim()) return fallback;
  const out = String(str)
    .split(',')
    .map((s) => parseFloat(s.trim()))
    .filter((v) => Number.isFinite(v));
  return out.length ? out : fallback;
}

function _defaultLadder(spot) {
  const moneys = [0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15];
  return moneys.map((m) => Math.round(spot * m * 100) / 100);
}

function _midnight(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function parseExpiries(values) {
  if (typeof values === 'string') values = values.split(',');
  const today = _midnight(new Date());
  const out = [];
  const seen = new Set();
  for (const raw of values || []) {
    const token = String(raw).trim();
    if (!token) continue;
    let date;
    if (ISO_RE.test(token)) {
      date = new Date(token + 'T00:00:00');
      if (isNaN(date.getTime())) continue;
    } else {
      const days = parseInt(token, 10);
      if (isNaN(days) || days < SIM_MIN_DTE || days > SIM_MAX_DTE) continue;
      date = new Date(today.getTime() + days * 86400000);
    }
    const dte = Math.round((_midnight(date) - today) / 86400000);
    if (dte < SIM_MIN_DTE || dte > SIM_MAX_DTE) continue;
    const iso = date.toISOString().slice(0, 10);
    if (seen.has(iso)) continue;
    seen.add(iso);
    out.push({ dte, date: iso, label: `${iso} (${dte}D)` });
  }
  out.sort((a, b) => a.dte - b.dte);
  return out;
}

function _priceGrid(spot, strikes, rangePct, nPoints) {
  const span = Math.max(rangePct, 0.05);
  const lo = Math.min(spot * (1 - span), Math.min(...strikes) * 0.97);
  const hi = Math.max(spot * (1 + span), Math.max(...strikes) * 1.03);
  const loClamped = Math.max(lo, 0.01);
  const hiClamped = hi <= loClamped ? loClamped * 1.5 : hi;
  const n = Math.max(parseInt(nPoints, 10), 21);
  const prices = [];
  for (let i = 0; i < n; i++) prices.push(loClamped + ((hiClamped - loClamped) * i) / (n - 1));
  return prices;
}

// Mirrors simulate_expiry(); returns the dashboard payload + per-cell E[P&L].
export function simulateExpiry(opts) {
  const {
    spot,
    strikes,
    expiries,
    ivs,
    forwardIvs = null,
    optionType = 'call',
    side = 'long',
    r_pct = 5,
    qty = 1,
    multiplier = 100,
    nPoints = 101,
    rangePct = 0.35,
  } = opts || {};

  const S = parseFloat(spot);
  if (!Number.isFinite(S) || S <= 0) throw new Error('spot must be a positive finite number');
  if (optionType !== 'call' && optionType !== 'put') throw new Error("option_type must be 'call' or 'put'");
  if (side !== 'long' && side !== 'short') throw new Error("side must be 'long' or 'short'");

  const KS = [...new Set(_parseList(strikes, _defaultLadder(S)).map((k) => parseFloat(k)).filter((k) => k > 0))].sort(
    (a, b) => a - b,
  );
  if (!KS.length) throw new Error('at least one positive strike is required');

  const exps = parseExpiries(expiries);
  if (!exps.length) throw new Error('at least one valid expiry is required');

  // UI/route contract: IVs arrive as PERCENT (e.g. "20, 30, 45"). Convert to
  // decimal for the math, then clamp to [0.001, 5.0].
  const _toDecimal = (arr) => arr.map((v) => v / 100);
  const entryIvs = _toDecimal(_parseList(ivs, [20, 30, 45])).filter(
    (v) => v >= SIM_MIN_IV && v <= SIM_MAX_IV,
  );
  if (!entryIvs.length) throw new Error('implied vols must be between 0.1% and 500%');
  const fwdIvs = forwardIvs
    ? _toDecimal(_parseList(forwardIvs, entryIvs.map((v) => v * 100)))
    : entryIvs;

  const r = parseFloat(r_pct) / 100;
  const unit = parseFloat(qty) * parseFloat(multiplier);
  const sign = side === 'long' ? 1 : -1;
  const isCall = optionType === 'call';

  const prices = _priceGrid(S, KS, rangePct, nPoints);

  // Combos: maturity × entry IV. Each combo carries a forward IV (entry if linked).
  const combos = [];
  for (const exp of exps) {
    for (let i = 0; i < entryIvs.length; i++) {
      const entryIv = entryIvs[i];
      const fwdIv = fwdIvs[Math.min(i, fwdIvs.length - 1)];
      combos.push({
        dte: exp.dte,
        expiry: exp.date,
        iv_pct: Math.round(entryIv * 100 * 10000) / 10000,
        label: `${exp.dte}D · ${entryIv * 100}g% IV`,
        entry_iv_pct: Math.round(entryIv * 100 * 10000) / 10000,
        forward_iv_pct: Math.round(fwdIv * 100 * 10000) / 10000,
      });
    }
  }

  const intrinsicAt = (p, k) => (isCall ? Math.max(p - k, 0) : Math.max(k - p, 0));
  const intrinsicSpot = intrinsicAt(S, 0); // placeholder, set per-strike below

  const results = [];
  for (const K of KS) {
    const cells = [];
    const intrSpot = isCall ? Math.max(S - K, 0) : Math.max(K - S, 0);
    for (let j = 0; j < combos.length; j++) {
      const combo = combos[j];
      // combo.entry_iv_pct / forward_iv_pct are PERCENT (e.g. 30 for 30%); divide
      // by 100 to get the decimal IV used by Black–Scholes.
      const entryIv = combo.entry_iv_pct / 100;
      const fwdIv = combo.forward_iv_pct / 100;
      const T = combo.dte / 365;

      const g = bsGreeks(S, K, T, r, entryIv, optionType);
      let premium = g.bs_price;
      let delta = g.delta;
      if (!Number.isFinite(premium)) premium = 0;
      if (!Number.isFinite(delta)) delta = 0;

      const pnl = prices.map((p) => sign * unit * (intrinsicAt(p, K) - premium));
      const breakeven = isCall ? K + premium : K - premium;

      // PoP = risk-neutral P(pnl > 0 at expiry). Mirrors core/options/simulation/
      // expiry.py::_prob_above exactly (analytic Φ(d2)) so it matches the Python
      // backend and the dashboard KPI. Uses the FORWARD vol (IV fairly priced when
      // the two are linked) — this is Decision B.
      let pop;
      if (fwdIv > 0 && combo.dte > 0 && S > 0) {
        const T = combo.dte / 365;
        const d2 = (Math.log(S / breakeven) + (r - 0.5 * fwdIv * fwdIv) * T) / (fwdIv * Math.sqrt(T));
        const pAbove = isCall ? normCdf(d2) : 1 - normCdf(d2);
        pop = side === 'long' ? pAbove : 1 - pAbove;
      } else {
        pop = 0;
      }
      const epl = expectedPnl(prices, pnl, S, fwdIv, combo.dte, r);

      let maxProfit, maxLoss, unbProfit, unbLoss;
      if (isCall) {
        if (side === 'long') {
          unbProfit = true; unbLoss = false;
          maxProfit = null; maxLoss = -premium * unit;
        } else {
          unbProfit = false; unbLoss = true;
          maxProfit = premium * unit; maxLoss = null;
        }
      } else {
        unbProfit = false; unbLoss = false;
        if (side === 'long') {
          maxProfit = (K - premium) * unit; maxLoss = -premium * unit;
        } else {
          maxProfit = premium * unit; maxLoss = -(K - premium) * unit;
        }
      }

      cells.push({
        dte: combo.dte,
        expiry: combo.expiry,
        iv_pct: combo.iv_pct,
        label: combo.label,
        entry_iv_pct: combo.entry_iv_pct,
        forward_iv_pct: combo.forward_iv_pct,
        premium: Math.round(premium * 1e4) / 1e4,
        delta: Math.round(delta * 1e4) / 1e4,
        breakeven: Math.round(breakeven * 1e4) / 1e4,
        pop: Math.round(pop * 1e4) / 1e4,
        expected_pnl: Number.isFinite(epl) ? Math.round(epl * 100) / 100 : null,
        max_profit: unbProfit ? null : Math.round(maxProfit * 100) / 100,
        max_loss: unbLoss ? null : Math.round(maxLoss * 100) / 100,
        unbounded_profit: unbProfit,
        unbounded_loss: unbLoss,
        pnl_at_spot: Math.round(sign * unit * (intrSpot - premium) * 100) / 100,
        pnl: pnl.map((v) => Math.round(v * 100) / 100),
      });
    }
    results.push({ strike: Math.round(K * 1e4) / 1e4, cells });
  }

  return {
    spot: Math.round(S * 1e4) / 1e4,
    option_type: optionType,
    side,
    r_pct: Math.round(r * 10000) / 10000,
    qty: parseInt(qty, 10),
    multiplier: parseInt(multiplier, 10),
    prices: prices.map((p) => Math.round(p * 1e4) / 1e4),
    strikes: KS.map((k) => Math.round(k * 1e4) / 1e4),
    combos,
    results,
  };
}

// Expose for the dashboard tab (and the standalone Pages site).
if (typeof window !== 'undefined') {
  window.SimEngine = { simulateExpiry, parseExpiries, SIM_MIN_DTE, SIM_MAX_DTE, SIM_MIN_IV, SIM_MAX_IV };
}

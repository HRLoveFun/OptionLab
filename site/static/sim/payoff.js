// payoff.js — expiry payoff, net premium, breakevens.
//
// Port of core/strategies/payoff.py. Per-share (no contract multiplier) to keep
// numeric parity with the backend; apply any multiplier only at the display
// layer.
//
// A `leg` is a plain object: { side:'long'|'short', optionType:'call'|'put',
// strike, premium, qty=1, dte=30, iv=0.25 }. sign: long = +1, short = -1.

function _sign(leg) {
  return leg.side === 'long' ? 1 : -1;
}

export function payoffAtExpiration(legs, prices) {
  const pnl = prices.map(() => 0);
  for (const leg of legs) {
    const s = _sign(leg);
    const q = leg.qty ?? 1;
    for (let i = 0; i < prices.length; i++) {
      const S = prices[i];
      const intrinsic =
        leg.optionType === 'call' ? Math.max(S - leg.strike, 0) : Math.max(leg.strike - S, 0);
      pnl[i] += s * q * (intrinsic - leg.premium);
    }
  }
  return pnl;
}

export function netPremium(legs) {
  let total = 0;
  for (const leg of legs) {
    total += -_sign(leg) * (leg.qty ?? 1) * leg.premium;
  }
  return total; // negative = debit paid, positive = credit received
}

// Linear-interpolation breakevens, mirroring find_breakevens().
export function findBreakevens(prices, pnl) {
  const out = [];
  for (let i = 0; i < pnl.length - 1; i++) {
    const y0 = pnl[i];
    const y1 = pnl[i + 1];
    if (Math.sign(y1) === Math.sign(y0)) continue; // np.diff(sign) != 0
    if (y1 === y0) continue;
    const x0 = prices[i];
    const x1 = prices[i + 1];
    const be = x0 - y0 * (x1 - x0) / (y1 - y0);
    out.push(Math.round(be * 1e4) / 1e4);
  }
  return out;
}

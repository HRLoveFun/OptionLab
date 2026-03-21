"""
Put Option Selection — Quantitative Decision Process.

Implements Modules 0–7 from option_decision_process.md:
  - Build candidate option matrix from live chain data
  - Enrich with derived metrics (delta_per_dollar, payoff, vega/theta ratio)
  - Compute subjective expected value
  - Filter and rank by EV, vol efficiency, and DTE window

All functions accept scalar inputs and return plain dicts/lists suitable
for JSON serialisation in the service layer.
"""

import logging
import math
from typing import Optional

import numpy as np
import pandas as pd

from core.options_chain_analyzer import OptionsChainAnalyzer, _dte
from core.options_greeks import greeks_vectorized

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (Module 0)
# ---------------------------------------------------------------------------
CANDIDATE_DELTAS: list[float] = [-0.25, -0.40, -0.55, -0.70]
CANDIDATE_DTES: list[int] = [21, 45, 60, 90]
MIN_EV_THRESHOLD: float = 0.0
MIN_VEGA_THETA: float = 2.0
RISK_FREE_RATE: float = 0.05


# ---------------------------------------------------------------------------
# Module 1 — Market data helpers
# ---------------------------------------------------------------------------

def _atm_iv_for_expiry(puts: pd.DataFrame, spot: float) -> Optional[float]:
    """Return ATM implied volatility (as %) for a puts DataFrame."""
    valid = puts.dropna(subset=['impliedVolatility'])
    if valid.empty:
        return None
    idx = (valid['strike'] - spot).abs().idxmin()
    return float(valid.loc[idx, 'impliedVolatility']) * 100


def get_term_structure(analyzer: OptionsChainAnalyzer) -> dict[int, float]:
    """Extract {dte: atm_iv_pct} term structure from the analyzer."""
    ts: dict[int, float] = {}
    for exp in analyzer.expiries:
        if exp not in analyzer.chain:
            continue
        puts = analyzer.chain[exp]['puts']
        atm_iv = _atm_iv_for_expiry(puts, analyzer.spot)
        if atm_iv is not None:
            ts[_dte(exp)] = atm_iv
    return ts


def calculate_iv_rank(term_structure: dict[int, float]) -> Optional[float]:
    """IV rank (0–100) from term structure ATM IVs."""
    ivs = list(term_structure.values())
    if len(ivs) < 2:
        return None
    lo, hi = min(ivs), max(ivs)
    if hi == lo:
        return 50.0
    current = ivs[0]  # nearest-expiry as proxy for "current" IV
    return round((current - lo) / (hi - lo) * 100, 1)


def calculate_iv_percentile(term_structure: dict[int, float]) -> Optional[float]:
    """IV percentile (0–100): % of expiries whose ATM IV < current."""
    ivs = list(term_structure.values())
    if len(ivs) < 2:
        return None
    current = ivs[0]
    below = sum(1 for v in ivs if v < current)
    return round(below / len(ivs) * 100, 1)


def fetch_market_data(ticker: str) -> dict:
    """Module 1: fetch live market snapshot via OptionsChainAnalyzer."""
    analyzer = OptionsChainAnalyzer(ticker)
    ts = get_term_structure(analyzer)
    return {
        'spot_price': analyzer.spot,
        'iv_rank': calculate_iv_rank(ts),
        'iv_pct': calculate_iv_percentile(ts),
        'term_structure': ts,
        'analyzer': analyzer,
    }


# ---------------------------------------------------------------------------
# Module 2 — Build candidate matrix
# ---------------------------------------------------------------------------

def _find_put_by_delta(puts_df: pd.DataFrame, target_delta: float,
                       spot: float) -> Optional[pd.Series]:
    """Find the put row whose BS-delta is closest to *target_delta*."""
    if puts_df is None or puts_df.empty:
        return None

    # Try using Greeks computed from IV + strike
    valid = puts_df.dropna(subset=['impliedVolatility', 'strike'])
    valid = valid[valid['impliedVolatility'] > 0]
    if valid.empty:
        return None

    # Vectorized BS delta for all strikes
    strikes = valid['strike'].values
    ivs = valid['impliedVolatility'].values  # decimal
    # Approximate DTE from first row (all same expiry)
    T = 30 / 365  # will be overridden by caller context if needed
    g = greeks_vectorized(S=spot, K=strikes, T=T, r=RISK_FREE_RATE,
                          sigma=ivs, option_type='put')
    deltas = np.asarray(g['delta'], dtype=float)

    # Find closest to target
    diffs = np.abs(deltas - target_delta)
    best_idx = np.nanargmin(diffs)
    return valid.iloc[best_idx]


def build_candidate_matrix(analyzer: OptionsChainAnalyzer,
                           candidate_deltas: list[float] | None = None,
                           candidate_dtes: list[int] | None = None) -> list[dict]:
    """Module 2: build the NxM delta×DTE candidate option matrix."""
    if candidate_deltas is None:
        candidate_deltas = CANDIDATE_DELTAS
    if candidate_dtes is None:
        candidate_dtes = CANDIDATE_DTES

    spot = analyzer.spot
    matrix: list[dict] = []

    for target_dte in candidate_dtes:
        # Find expiry closest to target DTE
        closest_exp = None
        closest_diff = float('inf')
        for exp in analyzer.expiries:
            d = _dte(exp)
            diff = abs(d - target_dte)
            if diff < closest_diff:
                closest_diff = diff
                closest_exp = exp

        if closest_exp is None or closest_exp not in analyzer.chain:
            continue

        actual_dte = _dte(closest_exp)
        puts_df = analyzer.chain[closest_exp]['puts']
        T = max(actual_dte, 1) / 365

        for target_delta in candidate_deltas:
            # Find put closest to target delta via BS
            valid = puts_df.dropna(subset=['impliedVolatility', 'strike'])
            valid = valid[valid['impliedVolatility'] > 0]
            if valid.empty:
                continue

            strikes = valid['strike'].values
            ivs = valid['impliedVolatility'].values
            g = greeks_vectorized(S=spot, K=strikes, T=T, r=RISK_FREE_RATE,
                                  sigma=ivs, option_type='put')
            deltas = np.asarray(g['delta'], dtype=float)
            diffs = np.abs(deltas - target_delta)
            best_idx = np.nanargmin(diffs)
            row = valid.iloc[best_idx]

            bid = float(row.get('bid', 0) or 0)
            ask = float(row.get('ask', 0) or 0)
            last_price = float(row.get('lastPrice', 0) or 0)
            mid = (bid + ask) / 2 if bid > 0 and ask > 0 else last_price

            # Compute Greeks at this strike
            iv = float(row['impliedVolatility'])
            strike = float(row['strike'])
            greeks = greeks_vectorized(S=spot, K=strike, T=T, r=RISK_FREE_RATE,
                                       sigma=iv, option_type='put')

            contract = {
                'strike': strike,
                'dte': actual_dte,
                'expiry': closest_exp,
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'last_price': round(last_price, 2),
                'mid_price': round(mid, 2),
                'delta': round(float(greeks['delta']), 4),
                'gamma': round(float(greeks['gamma']), 6),
                'theta': round(float(greeks['theta']), 4),
                'vega': round(float(greeks['vega']), 4),
                'iv': round(iv * 100, 2),
            }
            matrix.append(contract)

    return matrix


# ---------------------------------------------------------------------------
# Module 3 — Derived metrics
# ---------------------------------------------------------------------------

def enrich_contract(contract: dict, budget: float, spot_price: float,
                    target_move_pct: float) -> Optional[dict]:
    """Module 3: compute derived metrics for a single contract."""
    mid = contract['mid_price']
    if mid <= 0:
        return None

    contracts_n = int(budget / (mid * 100))
    if contracts_n == 0:
        return None

    delta = contract['delta']
    delta_per_dollar = abs(delta) / mid

    target_price = spot_price * (1 + target_move_pct)
    intrinsic_at_target = max(contract['strike'] - target_price, 0)
    payoff_at_target = intrinsic_at_target - mid
    total_payoff = payoff_at_target * 100 * contracts_n
    odds_ratio = total_payoff / budget if budget > 0 else 0.0

    theta = contract['theta']
    vega = contract['vega']
    vega_theta_ratio = (abs(vega) / abs(theta)) if theta != 0 else float('inf')
    vega_per_dollar = abs(vega) / mid

    implied_win_rate = abs(delta)

    contract['derived'] = {
        'contracts_n': contracts_n,
        'delta_per_dollar': round(delta_per_dollar, 4),
        'target_price': round(target_price, 2),
        'payoff_at_target': round(payoff_at_target, 2),
        'total_payoff': round(total_payoff, 2),
        'odds_ratio': round(odds_ratio, 2),
        'vega_theta_ratio': round(vega_theta_ratio, 2) if math.isfinite(vega_theta_ratio) else 999.99,
        'vega_per_dollar': round(vega_per_dollar, 4),
        'implied_win_rate': round(implied_win_rate, 4),
    }
    return contract


# ---------------------------------------------------------------------------
# Module 4 — Subjective expected value
# ---------------------------------------------------------------------------

def compute_ev(contract: dict, directional_conviction: float,
               vol_conviction: float, budget: float,
               time_horizon_days: int) -> dict:
    """Module 4: blend user convictions into an EV estimate."""
    p_direction = directional_conviction

    # IV expansion uplift scaled by vol_conviction
    iv_expansion_gain = (contract['derived']['vega_per_dollar']
                         * vol_conviction * 5.0)

    adjusted_payoff = (contract['derived']['payoff_at_target']
                       + contract['mid_price'] * iv_expansion_gain)
    adjusted_total = adjusted_payoff * 100 * contract['derived']['contracts_n']

    theta_drag = (abs(contract['theta']) * time_horizon_days
                  * 100 * contract['derived']['contracts_n'])

    net_if_right = adjusted_total - theta_drag
    loss_if_wrong = budget

    ev = p_direction * net_if_right - (1 - p_direction) * loss_if_wrong
    ev_ratio = ev / budget if budget > 0 else 0.0

    contract['ev'] = round(ev, 2)
    contract['ev_ratio'] = round(ev_ratio, 4)
    return contract


# ---------------------------------------------------------------------------
# Module 5 — DTE selector
# ---------------------------------------------------------------------------

def select_dte_range(vol_timing: str, time_horizon_days: int) -> tuple[int, int]:
    """Module 5: narrow DTE window based on vol-timing conviction."""
    vol_timing = vol_timing.upper()
    if vol_timing == 'FAST':
        return (time_horizon_days, time_horizon_days + 14)
    elif vol_timing == 'MEDIUM':
        return (time_horizon_days, time_horizon_days + 30)
    else:  # SLOW
        return (time_horizon_days + 14, time_horizon_days + 60)


# ---------------------------------------------------------------------------
# Module 6 — Filter & rank
# ---------------------------------------------------------------------------

def filter_and_rank(enriched: list[dict], min_dte: int, max_dte: int,
                    min_ev: float = MIN_EV_THRESHOLD,
                    min_vt: float = MIN_VEGA_THETA) -> list[dict]:
    """Module 6: apply gates and sort by EV ratio then vega/theta."""
    filtered = []
    for c in enriched:
        if not (min_dte <= c['dte'] <= max_dte):
            continue
        if c.get('ev', -1) < min_ev:
            continue
        if c['derived']['vega_theta_ratio'] < min_vt:
            continue
        if c['derived']['contracts_n'] < 1:
            continue
        filtered.append(c)

    filtered.sort(key=lambda c: (-c.get('ev_ratio', 0),
                                  -c['derived']['vega_theta_ratio']))
    return filtered


# ---------------------------------------------------------------------------
# Module 7 — Decision heuristics
# ---------------------------------------------------------------------------

def get_heuristic_notes(directional_conviction: float,
                        vol_conviction: float,
                        vol_timing: str,
                        iv_rank: Optional[float]) -> list[str]:
    """Return readable heuristic insights from the Appendix rules."""
    notes: list[str] = []

    if directional_conviction > vol_conviction:
        notes.append('Directional conviction dominates → prefer higher |delta| '
                     '(0.50–0.70) and shorter DTE.')
    elif vol_conviction > directional_conviction:
        notes.append('Vol conviction dominates → prefer ATM (delta 0.40–0.50), '
                     'longer DTE, high vega/theta ratio.')

    if vol_timing.upper() == 'FAST' and iv_rank is not None and iv_rank < 30:
        notes.append('Vol is cheap + fast timing → lean OTM / short DTE for '
                     'cheap convexity.')

    if iv_rank is not None and iv_rank > 70:
        notes.append('IV Rank > 70 — vol is expensive; require higher EV ratio '
                     'before entering.')

    return notes


# ---------------------------------------------------------------------------
# Module 8 — Orchestrator
# ---------------------------------------------------------------------------

def run_decision_process(ticker: str, budget: float,
                         target_move_pct: float,
                         time_horizon_days: int,
                         directional_conviction: float,
                         vol_conviction: float,
                         vol_timing: str) -> dict:
    """Full pipeline: fetch → build → enrich → EV → filter → report.

    Returns a JSON-serialisable dict with all results needed by the UI.
    """
    # Step 1 — market data
    mkt = fetch_market_data(ticker)
    analyzer = mkt['analyzer']

    # Step 2 — candidate matrix
    raw_matrix = build_candidate_matrix(analyzer)

    # Step 3 — enrich + EV
    enriched: list[dict] = []
    for c in raw_matrix:
        c = enrich_contract(c, budget, mkt['spot_price'], target_move_pct)
        if c is None:
            continue
        c = compute_ev(c, directional_conviction, vol_conviction,
                       budget, time_horizon_days)
        enriched.append(c)

    # Step 4 — DTE window
    min_dte, max_dte = select_dte_range(vol_timing, time_horizon_days)

    # Step 5 — filter & rank
    ranked = filter_and_rank(enriched, min_dte, max_dte)

    # Heuristic notes
    heuristics = get_heuristic_notes(
        directional_conviction, vol_conviction,
        vol_timing, mkt['iv_rank'],
    )

    # Build JSON-safe result (strip analyzer)
    return {
        'spot_price': round(mkt['spot_price'], 2),
        'iv_rank': mkt['iv_rank'],
        'iv_pct': mkt['iv_pct'],
        'term_structure': {str(k): v for k, v in mkt['term_structure'].items()},
        'dte_window': {'min': min_dte, 'max': max_dte},
        'candidates_total': len(raw_matrix),
        'candidates_enriched': len(enriched),
        'candidates_passed': len(ranked),
        'ranked': ranked[:10],  # top 10
        'heuristics': heuristics,
    }

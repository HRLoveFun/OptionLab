# Put Option Selection: Quantitative Decision Process
> Pseudocode for AI execution using project functions.
> Scenario: Bearish directional view + rising volatility conviction, fixed cash budget.

---

## Module 0: Configuration & Inputs

```
INPUTS:
  ticker          : string          # e.g. "US.AAPL" (futu format) or "AAPL" (yfinance)
  budget          : float           # total cash outlay in dollars
  target_move_pct : float           # expected % decline, e.g. -0.08 for -8%
  time_horizon_days: int            # how many days until view resolves, e.g. 21
  directional_conviction : float    # subjective [0.0 – 1.0], e.g. 0.70
  vol_conviction  : float           # subjective [0.0 – 1.0], e.g. 0.65
  vol_timing      : enum            # "FAST" (<2 wks) | "MEDIUM" (2–6 wks) | "SLOW" (>6 wks)

CONSTANTS:
  CANDIDATE_DELTAS : list[float]    # [-0.25, -0.40, -0.55, -0.70]
  CANDIDATE_DTES   : list[int]      # [21, 45, 60, 90]
  MIN_EV_THRESHOLD : float          # 0.0  (reject negative-EV trades)
  MIN_VEGA_THETA   : float          # 2.0  (minimum acceptable vol efficiency)
```

---

## Module 1: Market Data Fetch

```
FUNCTION fetch_market_data(ticker):

  # Use OptionsChainAnalyzer to get spot price and option chain data
  from core.options_chain_analyzer import OptionsChainAnalyzer

  analyzer = OptionsChainAnalyzer(ticker)
  spot_price = analyzer.spot

  # Calculate IV Rank and Percentile from available chain data
  # (Project doesn't have direct get_iv_rank/get_iv_percentile functions)
  iv_rank = _calculate_iv_rank(analyzer)          # 0–100 percentile
  iv_pct = _calculate_iv_percentile(analyzer)     # current IV vs 52-wk range
  term_structure = _get_term_structure(analyzer)   # {dte: iv} dict

  RETURN {spot_price, iv_rank, iv_pct, term_structure, analyzer}

# Helper: Extract term structure from analyzer
FUNCTION _get_term_structure(analyzer):
  from core.options_chain_analyzer import _dte

  term_structure = {}
  for exp in analyzer.expiries:
    if exp in analyzer.chain:
      puts = analyzer.chain[exp]['puts'].dropna(subset=['impliedVolatility'])
      if not puts.empty:
        idx = (puts['strike'] - analyzer.spot).abs().idxmin()
        atm_iv = float(puts.loc[idx, 'impliedVolatility']) * 100  # Convert to %
        dte = _dte(exp)
        term_structure[dte] = atm_iv
  RETURN term_structure
```

---

## Module 2: Build Candidate Option Matrix

```
FUNCTION build_candidate_matrix(analyzer, spot_price, CANDIDATE_DELTAS, CANDIDATE_DTES):

  from core.options_chain_analyzer import _dte

  matrix = []

  FOR each target_dte IN CANDIDATE_DTES:
    # Find expiry closest to target DTE
    closest_exp = None
    closest_dte_diff = float('inf')

    FOR exp IN analyzer.expiries:
      dte = _dte(exp)
      IF ABS(dte - target_dte) < closest_dte_diff:
        closest_dte_diff = ABS(dte - target_dte)
        closest_exp = exp

    IF closest_exp IS None OR closest_exp NOT IN analyzer.chain:
      CONTINUE

    puts_df = analyzer.chain[closest_exp]['puts']

    FOR each target_delta IN CANDIDATE_DELTAS:
      # Find put with delta closest to target_delta
      # Note: Delta available in futu data as 'delta' column after subscribing
      put_row = _find_put_by_delta(puts_df, target_delta)

      IF put_row IS None:
        CONTINUE

      # Build contract dict matching project data structure
      contract = {
        'strike': float(put_row['strike']),
        'dte': _dte(closest_exp),
        'expiry': closest_exp,
        'bid': float(put_row.get('bid', 0) or 0),
        'ask': float(put_row.get('ask', 0) or 0),
        'last_price': float(put_row.get('lastPrice', 0) or 0),
        'mid_price': (float(put_row.get('bid', 0) or 0) + float(put_row.get('ask', 0) or 0)) / 2
                     IF put_row.get('bid') and put_row.get('ask')
                     ELSE float(put_row.get('lastPrice', 0) or 0),
        'delta': float(put_row.get('delta', target_delta)),  # Use target as fallback
        'gamma': float(put_row.get('gamma', 0)),
        'theta': float(put_row.get('theta', 0)),
        'vega': float(put_row.get('vega', 0)),
        'iv': float(put_row.get('impliedVolatility', 0)) * 100,  # Convert to %
      }

      matrix.append(contract)

  RETURN matrix   # list of contract dicts

# Helper: Find put option closest to target delta
FUNCTION _find_put_by_delta(puts_df, target_delta):
  IF puts_df IS None OR puts_df.empty:
    RETURN None

  # If delta column exists, find closest
  IF 'delta' IN puts_df.columns AND puts_df['delta'].notna().any():
    valid_puts = puts_df.dropna(subset=['delta'])
    IF NOT valid_puts.empty:
      idx = (valid_puts['delta'] - target_delta).abs().idxmin()
      RETURN valid_puts.loc[idx]

  # Fallback: approximate by strike distance from ATM
  # OTM puts have strikes < spot, so filter for those
  # This is a simplified approximation
  RETURN puts_df.iloc[len(puts_df) // 4]  # Rough approximation for OTM puts
```

---

## Module 3: Compute Derived Metrics per Contract

```
FUNCTION enrich_contract(contract, budget, spot_price, target_move_pct):

  mid_price   = contract['mid_price']

  # Handle zero or invalid mid_price
  IF mid_price <= 0:
    RETURN None

  contracts_n = FLOOR(budget / (mid_price * 100))   # whole contracts only

  IF contracts_n == 0:
    RETURN None   # contract too expensive for budget; discard

  # --- Directional metrics ---
  delta_per_dollar = ABS(contract['delta']) / mid_price
    # how much delta exposure per $1 of premium

  target_price      = spot_price * (1 + target_move_pct)   # target_move_pct < 0
  intrinsic_at_target = MAX(contract['strike'] - target_price, 0)
  payoff_at_target    = intrinsic_at_target - mid_price     # per share
  total_payoff        = payoff_at_target * 100 * contracts_n

  odds_ratio = total_payoff / budget   # gross multiple on budget if right

  # --- Volatility metrics ---
  vega_theta_ratio = ABS(contract['vega']) / ABS(contract['theta'])
                     IF contract['theta'] != 0 ELSE float('inf')
    # vol sensitivity per $1/day of time decay

  vega_per_dollar  = ABS(contract['vega']) / mid_price

  # --- Win-rate proxy (market-implied) ---
  implied_win_rate = ABS(contract['delta'])   # rough proxy: P(ITM at expiry)

  contract['derived'] = {
    'contracts_n': contracts_n,
    'delta_per_dollar': delta_per_dollar,
    'target_price': target_price,
    'payoff_at_target': payoff_at_target,
    'total_payoff': total_payoff,
    'odds_ratio': odds_ratio,
    'vega_theta_ratio': vega_theta_ratio,
    'vega_per_dollar': vega_per_dollar,
    'implied_win_rate': implied_win_rate
  }

  RETURN contract
```

---

## Module 4: Compute Subjective Expected Value

```
FUNCTION compute_ev(contract, directional_conviction, vol_conviction,
                    budget, time_horizon_days):

  # Blend: directional conviction drives win-rate estimate
  # Vol conviction adds premium via vega pathway (IV expansion benefit)

  p_direction  = directional_conviction   # P(stock reaches target)

  # Estimate IV expansion uplift: if vol_conviction is high,
  # option price may increase before target is reached
  iv_expansion_gain = contract['derived']['vega_per_dollar'] \
                      * vol_conviction \
                      * 5.0   # assume +5 vol points if vol_conviction = 1.0
                              # scale linearly with conviction

  # Adjusted payoff per contract incorporates vol mark-up
  adjusted_payoff_per_share = contract['derived']['payoff_at_target'] \
                              + (contract['mid_price'] * iv_expansion_gain)
  adjusted_total_payoff     = adjusted_payoff_per_share \
                              * 100 * contract['derived']['contracts_n']

  # Theta drag over holding period
  theta_drag = ABS(contract['theta']) * time_horizon_days \
               * 100 * contract['derived']['contracts_n']

  net_payoff_if_right  = adjusted_total_payoff - theta_drag
  loss_if_wrong        = budget   # full premium loss

  ev = (p_direction * net_payoff_if_right) \
       - ((1 - p_direction) * loss_if_wrong)

  contract['ev']        = ev
  contract['ev_ratio']  = ev / budget   # normalised EV per dollar risked

  RETURN contract
```

---

## Module 5: DTE Selector

```
FUNCTION select_dte_range(vol_timing, time_horizon_days):
  # Narrows viable DTE candidates based on vol timing conviction

  IF vol_timing == "FAST":
    # Vol expected to spike quickly; buy cheap near-term vol
    min_dte = time_horizon_days
    max_dte = time_horizon_days + 14

  ELSE IF vol_timing == "MEDIUM":
    min_dte = time_horizon_days
    max_dte = time_horizon_days + 30

  ELSE:   # "SLOW"
    # Vol timing uncertain; extend DTE to reduce theta drag
    min_dte = time_horizon_days + 14
    max_dte = time_horizon_days + 60

  RETURN (min_dte, max_dte)
```

---

## Module 6: Filter & Rank Candidates

```
FUNCTION filter_and_rank(enriched_matrix, min_dte, max_dte,
                         MIN_EV_THRESHOLD, MIN_VEGA_THETA):

  filtered = []

  FOR each contract IN enriched_matrix:

    # Gate 1: DTE within acceptable window
    IF NOT (min_dte <= contract['dte'] <= max_dte):
      CONTINUE

    # Gate 2: Positive or zero expected value
    IF contract['ev'] < MIN_EV_THRESHOLD:
      CONTINUE

    # Gate 3: Minimum vol efficiency
    IF contract['derived']['vega_theta_ratio'] < MIN_VEGA_THETA:
      CONTINUE

    # Gate 4: Must afford at least 1 contract
    IF contract['derived']['contracts_n'] < 1:
      CONTINUE

    filtered.append(contract)

  # Primary sort: EV ratio descending
  # Tiebreak: vega_theta_ratio descending
  ranked = SORT(filtered,
                key = (contract['ev_ratio'] DESC,
                       contract['derived']['vega_theta_ratio'] DESC))

  RETURN ranked
```

---

## Module 7: Output Report

```
FUNCTION generate_report(ranked_contracts, market_data, inputs):

  IF ranked_contracts IS EMPTY:
    PRINT "No candidates pass all filters. Consider:"
    PRINT "  - Relaxing MIN_VEGA_THETA"
    PRINT "  - Increasing budget"
    PRINT "  - Revising directional / vol conviction inputs"
    RETURN

  top3 = ranked_contracts[0:3]

  FOR rank, contract IN ENUMERATE(top3):

    PRINT "--- Rank", rank + 1, "---"
    PRINT "Strike / DTE       :", contract['strike'], "/", contract['dte'], "days"
    PRINT "Delta / IV         :", contract['delta'], "/", contract['iv']
    PRINT "Mid Price          : $", contract['mid_price']
    PRINT "Contracts (budget) :", contract['derived']['contracts_n']
    PRINT "Vega / Theta ratio :", ROUND(contract['derived']['vega_theta_ratio'], 2)
    PRINT "Odds Ratio         :", ROUND(contract['derived']['odds_ratio'], 2), "x"
    PRINT "Implied Win Rate   :", ROUND(contract['derived']['implied_win_rate'] * 100, 1), "%"
    PRINT "Subjective EV      : $", ROUND(contract['ev'], 2)
    PRINT "EV / Dollar Risked :", ROUND(contract['ev_ratio'], 3)
    PRINT ""

  PRINT "Market Context:"
  PRINT "  Spot Price   :", market_data.spot_price
  PRINT "  IV Rank      :", market_data.iv_rank
  PRINT "  IV Percentile:", market_data.iv_pct
```

---

## Module 8: Main Orchestrator

```
FUNCTION main():

  # Step 1 — Fetch live market data
  market_data = fetch_market_data(ticker)
  IF market_data.analyzer IS None:
    PRINT "Failed to fetch market data for", ticker
    RETURN

  # Step 2 — Build all candidate contracts
  raw_matrix = build_candidate_matrix(
                 market_data.analyzer,
                 market_data.spot_price,
                 CANDIDATE_DELTAS, CANDIDATE_DTES
               )

  # Step 3 — Enrich each candidate with derived metrics
  enriched_matrix = []
  FOR each contract IN raw_matrix:
    enriched = enrich_contract(contract, budget,
                               market_data.spot_price, target_move_pct)
    IF enriched IS NOT None:
      enriched = compute_ev(enriched, directional_conviction,
                            vol_conviction, budget, time_horizon_days)
      enriched_matrix.append(enriched)

  # Step 4 — Determine acceptable DTE window
  (min_dte, max_dte) = select_dte_range(vol_timing, time_horizon_days)

  # Step 5 — Filter and rank
  ranked = filter_and_rank(enriched_matrix, min_dte, max_dte,
                           MIN_EV_THRESHOLD, MIN_VEGA_THETA)

  # Step 6 — Print decision report
  generate_report(ranked, market_data, inputs)


CALL main()
```

---

## Appendix: Project Function Reference

| Function | Module | Arguments | Returns |
|---|---|---|---|
| `OptionsChainAnalyzer` | `core.options_chain_analyzer` | ticker: str | Class instance with `.spot`, `.expiries`, `.chain` |
| `_dte(expiry_str)` | `core.options_chain_analyzer` | expiry_str: str | int (days to expiry) |
| `get_odds_with_vol_context()` | `core.options_chain_analyzer` | spot, target_pct, chain, expiries | dict |

### OptionsChainAnalyzer Data Structure
```python
{
  'spot': float,                    # Current stock price
  'expiries': ['2026-03-20', ...],  # Expiration dates (str)
  'chain': {
    '2026-03-20': {
      'calls': pd.DataFrame,        # With columns: strike, bid, ask, lastPrice, impliedVolatility, volume, openInterest, delta, gamma, theta, vega
      'puts': pd.DataFrame          # Same columns
    }
  }
}
```

### Key Differences from Original Pseudocode

| Aspect | Original | Corrected |
|---|---|---|
| API prefix | `optionview.*` | Direct imports from `core.options_chain_analyzer` |
| IV metrics | `get_iv_rank()`, `get_iv_percentile()` | Must calculate from `OptionsChainAnalyzer` data |
| Strike selection | `get_strike_by_delta()` | `_find_put_by_delta()` helper using analyzer data |
| Option type | `"put"` / `"call"` | `"PUT"` / `"CALL"` (uppercase) |
| Expiry format | `expiry_dte: int` | `exp: str` (e.g., `"2026-03-20"`) with `_dte()` helper |
| Contract access | Direct function call | Via `analyzer.chain[exp]['puts']` DataFrame |

---

## Key Decision Heuristics (for AI reasoning layer)

```
IF directional_conviction > vol_conviction:
  prefer higher |delta| strikes (0.50–0.70), shorter DTE

IF vol_conviction > directional_conviction:
  prefer ATM strikes (0.40–0.50), longer DTE, high vega_theta_ratio

IF vol_timing == "FAST" AND iv_rank < 30:
  vol is cheap; lean OTM, short DTE — capture cheap convexity

IF iv_rank > 70:
  vol is expensive; require higher ev_ratio threshold before entering

IF odds_ratio < 1.5:
  trade does not offer sufficient payoff multiple; skip regardless of EV sign
```

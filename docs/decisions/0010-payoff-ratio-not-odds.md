# 0010. "Expiry Odds" renamed to "Payoff Ratio"

- **Status**: Accepted
- **Date**: 2026-09-10
- **Deciders**: project author

## Context

Tab 7 ("Expiry Odds") drew one curve per expiration whose y-axis was labelled
`Odd`, computed client-side in `static/option-chain.js` as

```
odd = (max(intrinsic_at_target, 0) − premium) / premium
```

conditional on the underlying landing exactly at `spot × (1 ± estMove%)` at
expiration.

Forces at play:

- The label **"odds" implies a probability-weighted quantity**. This number is
  not: there is no distribution over terminal prices, only a single assumed
  point. Readers took a high value on a cheap far-OTM strike as a good bet,
  when a high value there exists *precisely because* the probability of the
  underlying reaching the target is low. `core/decision/ev.py` already holds a
  real probability-weighted expected-value framework; this tab never used it.
- The `(payoff − premium) / premium` form produces negative multiples
  (`-1.0x` when the option expires worthless) which read poorly against an
  `x` suffix, and `1.5x` invites the "multiply your money by 1.5" misreading
  when it means "+150% net".
- The token `payoff` is already taken by the Simulation strategy-payoff chart
  (`static/components/payoff_chart.js`, `core/strategies/payoff.py`,
  `tests/unit/payoff_chart.test.js`), so a bare `payoff` rename would collide.
- A second, dormant code path — `POST /api/odds_with_vol` →
  `get_odds_with_vol_context` — computes a genuine **probability of touch**
  (`2·(1−Φ(|z|))`). Its DOM container (`odds-vol-context`) is not present in the
  partial, so `_oddsLoadVolContext` returns at its first line. "odds" there is
  defensible, but "probability" is clearer.

## Options Considered

1. **Rename user-facing strings only.** Rejected — leaves `_odds*` functions,
   `odds-*` DOM ids, `oddsChainState`, panel key `'odds'`, and the API route
   contradicting the UI; the misleading term survives in the code.
2. **Rename to `payoff` everywhere.** Rejected — collides with the Simulation
   payoff chart; two unrelated "payoff" charts is worse than the status quo.
3. **Full rename to `payoffRatio` / `pr-` + gross formula + split the
   probability path to `expiry_probability`.** **Chosen.**

## Decision

- **Feature name**: "Payoff Ratio" (UI: tab title, y-axis `Payoff ratio
  (× premium)`, panel description).
- **Formula → gross multiple**: `ratio = max(intrinsic_at_target, 0) / premium`.
  `0x` = worthless at expiry (whole premium lost), `1x` = breakeven,
  `2.5x` = 2.5× the premium back. A dashed `Breakeven 1.0x` reference line is
  drawn at `y = 1` (mirroring the existing Spot vertical line).
- **Code token**: `payoffRatio` for the `appState` key and public
  `loadPayoffRatioData`; `_pr*` for the module-internal functions (matching the
  sibling `_oc*` option-chain convention in the same file); `pr-` for DOM ids
  and CSS classes; `payoff_ratio` for the Flask panel key, tabFlags key, and
  Pages slug (`payoff-ratio/index.html`; the old `odds/` slug is kept as a
  legacy redirect). `core/decision/enrich.py::odds_ratio` → `payoff_ratio`
  (same misname, no consumers).
- **Probability path**: `POST /api/odds_with_vol` → `POST /api/expiry_probability`,
  `OptionsChainService.odds_with_vol` → `.expiry_probability`,
  `get_odds_with_vol_context` → `get_expiry_probability_context`, response key
  `"odds"` → `"metrics"`, fixture `odds_with_vol.nvda.json` →
  `expiry_probability.nvda.json`, payload key `odds_by_expiry` →
  `probability_by_expiry`. Still dormant (no DOM container) — the rename just
  keeps the semantics honest for a future revival.

## Consequences

- **Positive**: term no longer implies probability; `x` multiples are all
  non-negative with an explicit breakeven line; the probability-of-touch code
  is now clearly named for what it is; `payoffRatio` does not collide with the
  Simulation payoff chart.
- **Negative / accepted trade-offs**: the gross formula shifts every historical
  curve up by 1.0 — anyone used to the old scale must recalibrate. The metric
  is still a single-point scenario return, **not** probability-weighted; the
  chart should not be used alone to pick strikes. Adding a P(ITM)/`√T`-scaled
  expected-move overlay is deferred.
- **Follow-up actions**: if the probability context table is revived, add a
  `pr-probability-context` container to `templates/partials/tab_payoff_ratio.html`
  and have `get_expiry_probability_context` return the `vol_context` /
  `probability_by_expiry` shape the frontend renders.

## References

- Related code: `static/option-chain.js` (`_prRenderCharts`),
  `templates/partials/tab_payoff_ratio.html`,
  `static/state/payoffRatioState.js`,
  `routes/options.py` (`POST /api/expiry_probability`),
  `core/options/chain/analyzer.py` (`get_expiry_probability_context`),
  `core/decision/enrich.py`
- Related ADR: 0006 (vanilla-JS frontend), 0007 (public GitHub Pages)
- External: `docs/glossary.md` (Payoff Ratio), `docs/guides/USER_GUIDE.md` §7

# 0008. Server-Side Options Expiry Simulation

- **Status**: Accepted
- **Date**: 2026-09-02
- **Deciders**: project author

## Context

The dashboard needs an "expiry payoff simulation" capability: given a spot
price, a set of strikes, maturities (DTE integers or ISO dates), and implied
volatilities, compute the expiration P&L surface for a single option
(call/put, long/short) swept across a strike × maturity × IV grid, with
per-cell breakeven, probability-of-profit (PoP), entry premium, delta, and
max profit/loss. It is exposed via a new `POST /api/simulate_expiry` endpoint.

Forces at play:

- The same math must also serve as the **golden oracle** for the client-side
  simulator described in `docs/plans/simulation_tab.md` (which depends on
  ADR 0007 for a public GitHub Pages deploy). Both hosts must agree to 1e-6,
  so the computation must be deterministic and pure (no network).
- It must reuse the existing vectorised Black–Scholes in
  `core/options/greeks/black_scholes.greeks_vectorized` rather than
  re-implementing pricing.
- A single request must not be allowed to ask for an unbounded
  strike × maturity × IV grid (a 5000-cell sweep would block a worker thread).
- It must honour the same degenerate-input clamps used elsewhere in
  `core/options` (`_T_MIN`, `_SIGMA_MIN/_MAX` from `docs/constraints.md` §5).

## Options Considered

1. **Inline math in the route handler.** Rejected — violates the one-way
   `routes → services → core` layering and import-direction invariant (ADR 0001);
   routes must not contain pandas/numpy work, and would also make the logic
   untestable as a golden oracle.
2. **Fold simulation into `core/strategies/`** (reuse `payoff.py`). Rejected —
   `core/strategies` models a *multi-leg portfolio payoff at one expiration*,
   whereas this feature is a *single-leg* payoff swept across a 3-D grid. Mixing
   the two concerns would bloat `analyze_strategy` and break its return shape.
3. **New `core/options/simulation/` package** with pure `simulate_expiry` +
   `parse_expiries`, plus a thin validation/bounding layer in
   `services/options/simulation.py`. **Chosen.**

## Decision

Implement expiry-payoff simulation as a pure `core/` module, kept free of Flask
and network:

- **`core/options/simulation/expiry.py`**
  - `parse_expiries(values, today=None) -> list[dict]` — normalises DTE integers
    and ISO dates into `[{dte, date, label}]`; drops tokens that fail to parse
    or resolve to a date outside `[_MIN_DTE=1, _MAX_DTE=3650]`.
  - `simulate_expiry(spot, strikes, expiries, ivs, option_type, side, r, qty,
    multiplier, n_points, range_pct) -> dict` — returns
    `{spot, option_type, side, r_pct, qty, multiplier, prices, strikes,
    combos, results}` where `results[i].cells` is parallel to `combos`. It
    prices entry premium + delta via `greeks_vectorized`, builds the
    terminal-price axis with `_price_grid`, and computes PoP via `_prob_above`
    (risk-neutral GBM). IVs are clamped to `[_MIN_IV=0.001, _MAX_IV=5.0]`.
    Unbounded P&L is encoded as `max_profit`/`max_loss = None` plus
    `unbounded_profit`/`unbounded_loss` flags (mirroring the `±inf` logic the
    plan preserves for the JS port at T5).
- **`services/options/simulation.py`**
  - `run_simulation(payload) -> dict` — validates the JSON body, resolves the
    spot (explicit `spot` override wins; otherwise `data_pipeline/yf_client.
    fetch_spot`, which is the only yfinance chokepoint, ADR 0005), enforces grid
    caps (`MAX_STRIKES=15, MAX_EXPIRIES=6, MAX_IVS=5, MAX_CELLS=300,
    MAX_POINTS=201`), and delegates to `simulate_expiry`. All Flask/`ApiError`
    concerns stay here, out of `core/`.

The route `routes/options.py::simulate_expiry_route` does nothing but parse the
JSON body and return `jsonify(run_simulation(data))`.

## Consequences

- **Positive**: the module is pure and trivially unit-testable, and reusable as
  the parity oracle for the JS port; respects the layering invariant; grid caps
  protect the server; entry pricing reuses `greeks_vectorized` (no drift from
  the rest of the app).
- **Negative / accepted trade-offs**: single-leg only — the multi-leg
  strike×DTE **matrix** view from the plan is a client-side `static/sim/grid.js`
  concern (plan T12), not part of this Python path. GBM-based PoP assumes
  European exercise and no dividends, consistent with the Greeks note in
  `docs/glossary.md`. `resolve_spot` still hits yfinance in the no-override
  case, so it must route through `yf_client` (throttled, ADR 0005) — not a
  direct call.
- **Follow-up actions**: keep `core/options/simulation` and the future
  `static/sim/*` aligned via golden tests (`scripts/gen_sim_golden.py`, plan T6);
  the standalone Pages tab is tracked separately under
  `docs/plans/simulation_tab.md` and ADR 0007; the pre-existing `±inf` JSON
  serialisation bug in `services/options/strategies.py` (plan T19) is out of scope
  for this ADR.

## References

- Related code: `core/options/simulation/expiry.py`,
  `services/options/simulation.py`,
  `routes/options.py` (`POST /api/simulate_expiry`),
  `core/options/greeks/black_scholes.py`
- Related ADR: 0007 (public Pages + client-side sim), 0001 (three-layer
  architecture / import direction), 0005 (token-bucket yfinance throttle)
- External: `docs/plans/simulation_tab.md`, `docs/constraints.md` §5,
  `docs/glossary.md` (Greeks)

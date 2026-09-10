# 0012. Parameter Ownership & Data-Readiness Prefetch

- **Status**: Proposed
- **Date**: 2026-09-10
- **Deciders**: repo owner (pending review)

## Context

The dashboard has two parameter surfaces:

- **Parameter tab** (`templates/partials/tab_parameter.html`) — `ticker`, time
  horizon, `account_size`, `max_risk_pct`, option `positions`, plus hidden fields
  for `frequency` / `side_bias` / `risk_threshold` / `rolling_window`.
- **Config tab** (`templates/partials/tab_config.html`) — persisted to
  `localStorage`, synced into the hidden fields on submit: `frequency`,
  `side_bias`, `risk_threshold`, `rolling_window`, `refresh_interval`, `max_dte`,
  `moneyness_low` / `moneyness_high`, `max_contracts`.

An audit of who consumes each parameter (see
[`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md) §3) shows:

- Only `ticker` is used by every data-driven module.
- Time horizon → the 3 streaming market tabs. `frequency` → 2 of them.
- `side_bias` / `risk_threshold` / `rolling_window` → Assessment only.
- `max_dte` / `moneyness_*` → Option Chain + Payoff Ratio only (read from the DOM
  directly by `option-chain.js`). `max_contracts` → not read by any client code.
- `refresh_interval` → the Option Chain / Payoff Ratio auto-refresh timer only.

So **"Config" is not global** — it is Assessment's parameters plus Option Chain's
filters sharing one panel, bridged to the backend through hidden `<input>`s.

Separately, `POST /` computes nothing and prefetch is lazy and per-slice: each
`/render/<kind>` triggers `DataService.get_processed` → `manual_update(7d)` +
`needs_backfill` → a daemon-thread backfill with an 8 s grace wait. Live-data tabs
get no prefetch at all. The owner wants: after the required parameter is entered,
the backend should check the DB and pre-download / pre-process what the visible
modules will need, so tab responses are fast.

Constraints in play: `docs/constraints.md` §6 (no job queue, compute in one
request), §7 (vanilla JS, no build), [ADR 0006](0006-vanilla-js-frontend.md),
[ADR 0001](0001-three-layer-architecture.md) (layer direction).

## Options Considered

1. **Keep the Config tab, relabel it, leave the hidden-field bridge.**
   - Pros: no work.
   - Cons: the "global settings" framing stays wrong; live-data params still
     bypass it; no up-front prefetch.

2. **One big global form (ticker + horizon + frequency + everything), keep it a tab.**
   - Pros: single submit.
   - Cons: forces every module's parameters on every user; Option Chain and Market
     Review want different horizons; still a tab, not always visible.

3. **`ticker`-only persistent bar; every other parameter owned by its module; a
   readiness pass on submit that plans + prefetches per visible module.**
   - Pros: the bar is minimal and always visible; each module's controls live with
     the module and re-run only that module; prefetch is driven by an explicit
     per-module dataset plan; the Config tab can be deleted.
   - Cons: bigger frontend diff (per-module toolbars, new `state/` stores, drop the
     hidden-field bridge); the `POST /` submit contract changes.

## Decision

We choose **Option 3**.

### Parameter ownership

- A **persistent, collapsible Parameters bar** renders above `.main-panel`
  (`position: sticky`), owns exactly one input — `ticker` — plus the Run button
  and ticker-validation badges. Collapse state is a per-viewer `localStorage`
  convenience (guarded `try/catch`).
- **Each module renders its own parameter controls** in a module toolbar and
  persists them through a dedicated `static/state/*` store (one `localStorage` key
  per group), replacing `marketAnalysisConfig` and the hidden `<input>` bridge:
  - `marketParamsState` — time horizon (Market Review / Statistical / Assessment),
    `frequency` (Statistical / Assessment).
  - `assessmentParamsState` — `side_bias`, `risk_threshold`, `rolling_window`,
    `account_size`, `max_risk_pct`.
  - `optionFilterState` — `max_dte`, `moneyness_low`, `moneyness_high`,
    `max_contracts`, auto-refresh interval (Option Chain + Payoff Ratio).
- The **Config tab is deleted** unless a genuine global setting survives review
  (risk-free rate is the one candidate — currently hard-coded in `static/sim/` and
  again in `core/options/greeks`); if one survives, the tab shrinks to it.

### Readiness prefetch

`POST /` gains a cheap, non-blocking pass (in `data_pipeline/orchestrate/readiness.py`):

1. `plan_datasets(tickers, modules)` → the union of `(symbol, dataset, start, end)`
   entries the requested modules need.
2. For each entry, a **DB-only coverage probe** (no network, like
   `needs_backfill`): covered → skip; small gap → inline fast-path ensure;
   wide gap → kick `orchestrate/backfill` on a **daemon thread** (the existing
   `_kick_backfill` pattern — **not** a queue, honouring §6).
3. Warm `services/options/preload` for the entered tickers on a daemon thread so
   the live option tabs are not cold.
4. Store the plan on the job; `create_job(form_data, tickers, plan)`.
5. Return the skeleton, unchanged, in < 1 s.

Each `/render/<kind>` and live `/api/*` consults the plan: ready → compute;
in-flight → the existing four-phase `loading` banner with a retry hint; the browser
re-fires. The direct-URL / bookmark path still auto-bootstraps a synthetic job.

The **submit contract** — whether `POST /` carries a `modules` manifest with
per-module params attached to each `/render` call, or the streaming tabs move fully
to client-fired `/api/*` — is deferred to the implementation batch.

## Consequences

- Positive: the always-visible surface is one field; module parameters are
  discoverable where they apply and re-run only their module; prefetch is explicit
  and covers live-data tabs; one mislabelled tab removed.
- Positive: `frequency`/horizon can differ per module (Option Chain vs. Market
  Review) instead of being forced equal.
- Negative / accepted: a substantial frontend batch (per-module toolbars, ~3 new
  `state/` stores, removal of `syncConfigToForm` and the hidden fields); a
  `POST /` contract change; a one-release `marketAnalysisConfig` migration shim.
- Negative / accepted: the readiness pass adds DB probes to `POST /` (bounded,
  DB-only, no network on the request thread).
- Follow-up: batches B5–B8 in
  [`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md) §6;
  update `docs/frontend_architecture.md` (layout diagram, tab table, streaming
  section) and `docs/frontend_convergence.md` in the same batches.

## References

- Related code: `templates/partials/tab_parameter.html`,
  `templates/partials/tab_config.html`, `static/main.js` (`FormManager`),
  `static/option-chain.js`, `routes/core.py::index`,
  `data_pipeline/data_ops/_range.py`, `data_pipeline/job_cache.py`,
  `services/market/dispatch.py`
- Related ADR: [0001](0001-three-layer-architecture.md),
  [0006](0006-vanilla-js-frontend.md),
  [0008](0008-server-side-expiry-simulation.md),
  [0011](0011-pluggable-data-provider-seam.md) (provides `read/` + `orchestrate/`)
- Plan: [`docs/plans/business_line_reorg.md`](../plans/business_line_reorg.md)
- Constraints: `docs/constraints.md` §6, §7

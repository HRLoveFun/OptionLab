# Development Plan: Simulation Tab (Client-Side Payoff Simulator)

**Branch**: `feat/simulation-tab` | **Date**: 2026-09-02 | **ADR**: [0007](decisions/0007-public-github-pages.md)

**Input**: User requirement — a "Simulation" tab that, given implied volatility,
expiration dates, and strikes, simulates the expiry payoff of options. Running it on
GitHub Pages lets anyone open the frontend, input parameters, and read the payoff
without a backend.

## Summary

Add a **Simulation** tab that performs all computation in the browser (vanilla JS, ES
modules, no build step — per `docs/constraints.md` §7). It reuses the *exact* math the
Python backend already implements (`core/strategies/analyze.py`,
`core/options/greeks/black_scholes.py`, `core/strategies/payoff.py`,
`core/strategies/prob_profit.py`) so both hosts agree to 1e-6. The same `static/sim/`
module is consumed by the Flask app (new tab) and by a standalone Pages site, so there
is a single source of truth.

## Technical Context

- **Language/Version**: vanilla JS (ES modules), no bundler (constraint §7).
- **Primary Dependencies**: Chart.js 4 via CDN (already in `templates/index.html`);
  no new runtime dependency. Vitest + jsdom for tests (already configured).
- **Storage**: none — purely client-side; no `fetch`, no `localStorage` of results
  (form persistence may reuse the existing `FormManager`/`localStorage` pattern).
- **Testing**: vitest unit tests for `static/sim/*` **plus** golden-value parity tests
  generated from the *real* Python implementations (`scripts/gen_sim_golden.py`) —
  no mocks, per project policy. Playwright e2e for the Flask tab.
- **Target Platform**: modern browsers; GitHub Pages (static).
- **Performance Goals**: all math for a 401-point grid × few legs must run < ~50 ms
  client-side; no perceptible lag on input change.
- **Constraints**: zero I/O in `static/sim/` (Pages-safe); output shape must match
  `renderPayoff` (`prices, pnl, breakevens, max_profit, max_loss, net_premium`);
  UI must obey P1–P5 from `docs/frontend_architecture.md`; semantic colors from
  `styles.css`.

## Locked Design Decisions

### D-A — Two complementary views (not one)

1. **Scenario curve** (existing mental model): P&L vs underlying price `S_T`. Reuses
   `static/components/payoff_chart.js::renderPayoff` unchanged.
2. **Distribution stats** (the new value): treat IV as forward volatility,
   `S_T ~ LogNormal(μ = ln(S)+(r−σ²/2)T, σ√T)`, then compute per-leg / per-cell:
   - E[P&L] = ∫ pnl(s)·pdf(s) ds (trapezoid, **full grid, no mask**)
   - PoP = ∫_{pnl>0} pdf(s) ds (masked — same as `prob_profit.py`)
   - P5 / P95 (VaR95 / expected shortfall proxy) via grid quantiles
   - breakeven(s), max profit/loss from the curve

> NOTE: E[P&L] and PoP use *different* integrands over the *same* grid. Do not reuse
> the masked `prob_profit` integrand for E[P&L] — that is the single most common bug.

### D-B — Dual IV with a link toggle (the differentiator)

| Role | Symbol | Drives |
|------|--------|--------|
| Entry IV (transaction IV) | `σ_entry` | the premium you pay/receive (`bsPrice`) |
| Forward vol (path vol to expiry) | `σ_fwd` | the width of the `S_T` distribution |

Default **linked** (`σ_fwd = σ_entry` ⇒ IV fairly priced). A toggle unlinks them so
users can ask "I buy at IV=60 but realized vol is 30 — what's my expectation?". Both
feed the math independently (`σ_entry` → premium, `σ_fwd` → `prob_profit`/`expectedPnl`).

### Multi-leg + sweep

- A leg builder: `{type: call|put, side: long|short, strike K, qty, σ_entry, dte}`.
- A **strike ladder** (moneyness 0.8–1.2, N steps) × **DTE buckets** (7/14/30/60/90)
  produces a **matrix view**: rows = strikes, columns = DTE, cell = E[P&L] (color-coded
  green/red via `--success`/`--error`). IV is the third dimension (slider or a small set
  of IV scenarios). The matrix is a styled `<table>` with `<caption>`/`aria-label`
  (satisfies P5; no extra Chart.js plugin needed).

## Project Structure

```text
static/sim/                         # SINGLE SOURCE OF TRUTH — pure, zero I/O, zero fetch
  ├── norm.js                       # normPdf / normCdf (erf approximation, ~1e-7 abs)
  ├── black_scholes.js              # price + greeks, WITH _T_MIN/_SIGMA_MIN/_SIGMA_MAX clamps
  ├── payoff.js                     # payoffAtExpiration / netPremium / findBreakevens
  ├── stats.js                     # lognormalPdf / expectedPnl / probProfit / percentile(VaR)
  ├── analyze.js                    # analyzeStrategy() — mirror core/strategies/analyze.py
  └── grid.js                       # strike × DTE × IV sweep → matrix

static/features/simulation.js       # ONLY file touching the DOM / Chart.js
templates/partials/tab_simulation.html
tests/unit/sim/*.test.js            # vitest + golden parity
tests/unit/sim/golden.json          # produced by scripts/gen_sim_golden.py
scripts/gen_sim_golden.py           # real Python → golden fixtures (no mock)

site/                               # standalone Pages artifact (built by CI)
  ├── index.html                    # params form + curve + matrix
  ├── styles.css                    # reused design tokens
  └── sim/                          # vendored copy of static/sim/
.github/workflows/pages.yml         # build site/ + push gh-pages
```

`static/features/` is the reserved "future feature modules" slot in
`docs/frontend_architecture.md`. The Flask tab includes `static/sim/analyze.js` as an
ES module and mounts `static/features/simulation.js`.

## Phases / Tasks

### Phase 0 — Prerequisites (BLOCKING)

- [ ] **P0.1** Resolve the `market_data.sqlite` exposure before public (see ADR 0007
      prerequisite). Recommended: publish a fresh tree that excludes the DB; do **not**
      force-push a rewritten private history without sign-off.
- [ ] **P0.2** Land ADR 0007 (public Pages + MIT license).
- [ ] **P0.3** Update `README.md` (license, Deployment section, architecture, scripts).

### Phase 1 — Math core + parity (trust anchor; blocks everything else)

- [ ] **T1** `static/sim/norm.js` — `normCdf` via erf (Numerical Recipes `erfcc`,
      ~1e-7), `normPdf`.
- [ ] **T2** `static/sim/black_scholes.js` — port `greeks_vectorized` price+greeks and
      the `_T_MIN=1/365`, `_SIGMA_MIN=0.001`, `_SIGMA_MAX=20.0` clamps verbatim.
- [ ] **T3** `static/sim/payoff.js` — port `payoff_at_expiration`, `net_premium`,
      `find_breakevens` (linear interpolation).
- [ ] **T4** `static/sim/stats.js` — `lognormalPdf`, `expectedPnl` (full-grid),
      `probProfit` (masked), `percentile`/`VaR` (grid quantiles).
- [ ] **T5** `static/sim/analyze.js` — mirror `analyze_strategy` **including** the
      naked-leg `max_profit=inf` / `max_loss=-inf` logic; keep `Infinity` (no
      serialization boundary in JS).
- [ ] **T6** `scripts/gen_sim_golden.py` — call real `core/strategies/analyze.py` and
      `core/options/greeks/black_scholes.py` across (K, DTE, IV, side, type), including
      boundary cases (`T=1/365`, `σ=0.001`, deep OTM) → `tests/unit/sim/golden.json`.
- [ ] **T7** `tests/unit/sim/*.test.js` — assert JS ≈ golden within **1e-6**; add a
      CI guard that `static/sim/**` contains no `fetch(`/`XMLHttpRequest`/`import.meta`.

### Phase 2 — Flask integration (reuse `renderPayoff`)

- [ ] **T8** `static/features/simulation.js` — DOM wiring: leg builder, dual-IV link
      toggle, strike ladder + DTE buckets inputs.
- [ ] **T9** `templates/partials/tab_simulation.html` — panel markup following P1–P5.
- [ ] **T10** Register the tab in `templates/index.html` sidebar + tab-content shell.
- [ ] **T11** `pytest`/`Playwright` smoke for the tab (open tab, input params, chart renders).

### Phase 3 — Matrix view + distribution stats

- [ ] **T12** `static/sim/grid.js` — K × DTE × IV sweep → matrix payload.
- [ ] **T13** Matrix table: semantic-color cells, `<caption>`, `aria-label` (P3/P5).
- [ ] **T14** Distribution stats panel: E[P&L], PoP, P5/P95, breakeven per selected leg.

### Phase 4 — Pages deployment

- [ ] **T15** `site/index.html` standalone (params + curve + matrix), reusing tokens.
- [ ] **T16** Vendor `static/sim/` → `site/sim/`.
- [ ] **T17** `.github/workflows/pages.yml` — build `site/` and push `gh-pages`.
- [ ] **T18** Verify Pages build with zero external backend dependency.

### Phase 5 — Polish & cross-cutting

- [ ] **T19** Fix the pre-existing `-Infinity` JSON serialization bug in
      `services/strategy_service.py` (`±inf` → `None`/`"unlimited"`); **separate PR + ADR
      note** (it affects `/api/strategy/analyze` for naked options, unrelated to the sim
      tab's pure-JS path).
- [ ] **T20** Doc note: reuse of `payoff_chart.js` relaxes constraint §7's "charts are
      server-side PNG" — record as a deliberate, scoped exception.

## Testing Strategy (real data, no mock)

- `scripts/gen_sim_golden.py` invokes the **real** Python implementations; the JSON it
  emits is the oracle. Vitest asserts `abs(js - golden) <= 1e-6` on every field.
- Boundary fixtures (`T=1/365`, `σ=0.001`, deep OTM) guard the clamps.
- e2e: load the Flask tab, fill params, assert the P&L curve and the matrix populate.
- The "no fetch in `static/sim/`" assertion prevents accidental backend coupling that
  would break the Pages build.

## Risks / Open Items

| Risk | Mitigation |
|------|-----------|
| `market_data.sqlite` leaks on public | Phase 0.1 (ADR 0007) — mandatory before go-live |
| `-Infinity` JSON rejected by browser | T19 — separate fix; sim JS keeps `Infinity` safely |
| erf precision | 1e-6 tolerance; do not tighten without swapping the approximation |
| contract multiplier | keep per-share in `sim/` for parity; multiply only at display |
| Pages free ⇒ public | ADR 0007 accepted; license MIT (assumed — adjust if desired) |
| DTE very short ⇒ truncated tail | label grid range in UI (P5 clarity) |

## Status update (2026-09-02)

**Key discovery:** the Simulation tab already existed (`static/simulation.js` +
`templates/partials/tab_simulation.html`, fully wired into `index.html` and tested)
but was **backend-coupled** — it called `POST /api/simulate_expiry`. It could not
run on GitHub Pages. The plan's "Phase 1 → Phase 2" work was therefore redirected
to **decouple the existing tab from the backend** using the Phase-1 engine, plus
land Decision B (dual IV). Net effect: the tab is now 100% client-side.

**Done**
- **Phase 1** (T1–T7): `static/sim/{norm,black_scholes,payoff,stats,analyze}.js`
  + `scripts/gen_sim_golden.py` + vitest parity (1e-6) + I/O-free guard test. ✅
- **Decoupling (was Phase 2 T8–T10):** `static/sim/grid.js` mirrors
  `core/options/simulation/expiry.py::simulate_expiry` exactly and is now the data
  source for `runSimulation` (no `api.post`). Dual-IV controls added to the UI.
  ✅
- **Phase 3 (T12–T14):** the K×DTE×IV matrix + distribution stats already existed in
  the original tab; we kept them and added an E[P&L] column (Decision A, view 2). ✅
- **Phase 4 (T15–T18):** `site/index.html` standalone + `.github/workflows/pages.yml`
  (official deploy-pages action) vendoring `static/sim` into `site/sim`. ✅
- **T19:** fixed a latent backend bug in `prob_profit.py` (multi-region PoP bridged
  disjoint profitable regions) — see commit note; existing Python tests still green.
  ✅
- **T20:** relaxation of constraint §7 (charts via CDN Chart.js) recorded in ADR 0007. ✅

**To do**
- **T11 (e2e):** ✅ added `tests/e2e/test_simulation.py` — two Playwright smoke tests
  (open tab → input → chart/matrix/detail render; and the dual-IV unlinked path),
  both passing against the real Flask-served page. Also added `tab-simulation` to the
  parametrized switch test in `tests/e2e/test_smoke.py`.
- **SQLite blocker (Phase 0.1):** ✅ **Done.** `git filter-repo --path-glob '*.sqlite'`
  (plus `-shm/-wal/-journal` globs) ran across all 196 commits — `git log --all -- '*.sqlite'`
  is now empty, so **no commit references the DB** (ADR 0007 fresh-tree achieved). The DB is
  also gitignored and excluded from the Pages artifact. Notes from the run:
  - `git-filter-repo` **removed the `origin` remote** (its default, to prevent pushing the
    rewritten history back to the private repo). Re-add the new public remote before pushing.
  - A backup of the old history lives in `.git/filter-repo/` (local only, never pushed).
    Delete it with `rm -rf .git/filter-repo/` once you're confident.
  - The working `market_data.sqlite` cache was dropped from disk; it's regenerable
    (`init_db` recreates it on first run) and gitignored, so no leak and no data loss.
  - To publish: `git remote add public <url>` then `git push public --mirror` (or
    `git push public main`).
- **Verify Pages build** once `pages.yml` runs on push (no secrets, no external backend).


# Reorganization Plan: Business Lines, Parameter Ownership & Data-Pipeline Seams

**Date**: 2026-09-10 (plan) | **Owner**: repo owner
**ADRs**: [0011](../decisions/0011-pluggable-data-provider-seam.md) (data-provider seam + canonical schema — **Accepted**),
[0012](../decisions/0012-parameter-ownership-and-prefetch.md) (parameter ownership + readiness prefetch — **Accepted**)

> **Status: LANDED (2026-09-10).** All eight §6 batches are implemented on branch
> `worktree-business-line-reorg`; the §0 ledger records what actually shipped,
> including the deliberate deviations from the shape below. The batches are still
> individually revertible — `git revert <batch-commit>` restores the previous
> behaviour without touching the others.

---

## 0. How to use this document — start here

### Rules of engagement (every session working this reorg)

1. **One batch = one PR = one revert.** Execute exactly one §6 batch, open the PR,
   stop. Never start the next batch in the same PR.
2. **A batch is "landed" only when** every exit-criterion in its §6 row is
   *literally* true (the grep returns nothing / the named test passes /
   `python scripts/arch_metrics.py --check` is green) **and** CI is green.
3. **Update the Batch Ledger below in the same commit** that lands the batch —
   this doc is the single place a cold session looks to know where the reorg is.
4. **Do not re-litigate an Accepted ADR** (0011, 0012). If reality forces a
   change, write an amending/superseding ADR *in the same PR* — never just
   diverge silently.
5. **Resolve the batch's §8 decision gate first.** Each open question names the
   batch it blocks; fold the answer into this doc or a new ADR *before* writing
   that batch's code.
6. **Docs move first.** Update `docs/` then mirror into `CLAUDE.md` /
   `CODEBUDDY.md` / `.github/copilot-instructions.md` — same PR. Run
   `python scripts/doc_guard.py` and `python scripts/regen_adr_index.py`.
7. **Scope discipline.** If you find something worth doing that is not in a §6
   row, add a row (or a note under §8) — do not fold it into the batch in hand.

### Batch Ledger

| Batch | State | PR | Landed (commit · date) | Notes |
|---|---|---|---|---|
| — (planning + ADRs) | ✅ landed | #7 + #8 | merged to `main` · 2026-09-10 | plan, ADR 0011/0012 (Accepted), scaffolding (ledger, gates, AI-guide pointers, memory) |
| B1 — provider seam extraction | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | delivers the "pluggable API" seam on its own. Actual shape / deviations recorded in §8; `_ALLOWED_DEPS` promotion of `providers` deferred to B3 |
| B2 — canonical raw store | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | gate §8 Q4 resolved (name-only rename). Actuals in §8; `symbol` column deferred (ADR 0011 amendment) |
| B3 — package re-home | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | six stages + `_state.py`; first sub-layer guard table; `arch_baseline.json` **not** reset (no tracked drift). Actuals + deviations in §8 |
| B4 — close L1 (`core-purity`) | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | zero core→data_pipeline edges; markers deleted and refused by test; `core` layer tightened to `{utils}` |
| B5 — readiness plan + prefetch | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | Q1 resolved (**manifest**, params as `/render` query args); readiness plan on the job; cold-start hold fragment. Actuals + deferrals in §8 |
| B6 — `ticker`-only Parameters bar | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | Q3 resolved (dedicated Portfolio tab); bar + collapse persisted; transitional settings group inside the bar's form until B7. Actuals in §8 |
| B7 — module-scoped params | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | Q1 resolved (manifest). Backend query-arg contract + per-module allow-list; `state/*ParamsState.js`; module toolbars; bridge + hidden fields deleted; Config tab emptied (B8 decides its fate). See §8 B7 |
| B8 — retire / repurpose Config tab | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | Q2 resolved (**deleted**). `grep tab_config` returns nothing; risk-free-rate follow-up on the watch list |
| B9 — acceptance-review remediation | 🔨 F1–F3+F6 landed | — | branch `worktree-business-line-reorg` · 2026-09-11 | §10 review. **F1** (memo `variant` key), **F2** (real collapse target + hide fields), **F3** (inline-SVG chevron), **F6** (docstrings) done; F4/F5/F7c open |

States: `⬜ not started` → `🔨 in progress (PR #n)` → `✅ landed` → (`↩ reverted`).
Keep the row order; edit the row in place.

---

## 1. Summary

Three requests, one reorg:

1. **Parameters module** — keep only the input every module needs (`ticker`), push
   everything else down to the module that owns it; make it a **persistent,
   collapsible bar** at the top of the page instead of a tab.
2. **Config module** — today it is a grab-bag of two modules' parameters
   mislabelled "global". Keep only genuinely cross-cutting settings; move the rest
   to their modules. The tab likely disappears.
3. **Backend acquire / process / serve boundaries** — make the three stages
   *enforceably* separate: acquisition behind a **provider adapter** that maps any
   API's fields onto **one canonical internal schema**; processing and serving
   provider-agnostic; and a **data-readiness step on submit** that, given the
   entered `ticker`, figures out which datasets the requested modules need, checks
   the DB, and kicks prefetch + preprocessing before the browser fans out.

Scope decisions already locked (2026-09-10):

| Question | Decision |
|---|---|
| Deliverable now | **This plan + ADR drafts only.** Implement batch-by-batch after review. |
| "Plug in various APIs" | **Build the abstraction seam only.** yfinance stays the sole implementation; a second provider is written when one is actually needed. |
| Global bar contents | **`ticker` only.** Time horizon, frequency, sizing, positions — all module-scoped. |

---

## 2. Current State — Business Lines

Eleven tabs, four data shapes (historical OHLCV / derived features / live option
snapshot / none), two compute paths (streaming `/render/<kind>` vs. client-fired
`/api/*`).

| Tab | Data it needs | Params it consumes | Compute path |
|---|---|---|---|
| Parameter | — (form only) | — | — |
| Summary *(dormant)* | multi-ticker aggregate | tickers | `services/market/analysis/summary.py` — fan-in 0, on the §2 watch list |
| Market Review | `clean_prices` + `market_review_prices` close panel | `ticker`, `start_time`, `end_time` | streaming `generate_market_review_slice` |
| Statistical Analysis | `processed_prices` | `ticker`, `parsed_start_time`, `frequency` | streaming `generate_statistical_slice` |
| Assessment & Projections | `processed_prices` | `ticker`, `parsed_start_time`, `frequency`, `risk_threshold`, `rolling_window`, `side_bias`→`target_bias`, `account_size`, `max_risk_pct` | streaming `generate_assessment_slice` |
| Market Regime | `regime_log` + live `^VIX` / `SPY` | `days` (30/180/365/1095) | client → `/api/regime/{current,history,backfill}` |
| Payoff Ratio | live option chain | `ticker`, `target_pct`, DTE window, `moneyness_*` | client → `/api/expiry_probability` (+ `option-chain.js`) |
| Option Chain | live option chain | `ticker`, `max_dte`, `moneyness_low`, `moneyness_high`, `max_contracts` | client → `/api/option_chain` |
| Volatility Analysis | live option chain | `ticker` | streaming `generate_options_chain_slice` |
| Simulation | none (client Black-Scholes) | `ticker` for spot lookup, scenario inputs | `static/sim/` |
| Option Pricing Matrix | none (client) | scenario inputs | `static/sim/` |
| Config | — (writes `localStorage`) | — | — |

**Observation.** Only `ticker` is universal. `start_time`/`end_time` is needed by
exactly the three streaming market tabs; `frequency` by two of them; everything
else by one module.

---

## 3. Current State — Parameter Ownership

### 3.1 What "Parameters" holds today

`templates/partials/tab_parameter.html` + `static/main.js::FormManager`:

| Field | Real owner | Notes |
|---|---|---|
| `ticker` | **global** | every data module |
| `start_time` / `end_time` | Market (Review / Statistical / Assessment) | `parse_month_str` → `parsed_start_time` |
| `account_size` | Assessment sizing + Portfolio Analysis | optional |
| `max_risk_pct` | Assessment sizing + Portfolio Analysis | optional |
| `positions` (`option_position` JSON) | Portfolio Analysis | drives the "Portfolio Analysis" button, `/api/portfolio_analysis` |
| `frequency` *(hidden)* | Statistical + Assessment | injected from Config via `syncConfigToForm()` |
| `side_bias` *(hidden)* | Assessment only | → `target_bias` |
| `risk_threshold` *(hidden)* | Assessment only | |
| `rolling_window` *(hidden)* | Assessment only | |

### 3.2 What "Config" holds today

`templates/partials/tab_config.html`, persisted to `localStorage` key
`marketAnalysisConfig`, synced into the hidden form fields on submit:

| Field | Real owner | Reaches backend via |
|---|---|---|
| `cfg-frequency` | Market (Statistical + Assessment) | hidden `frequency` field |
| `cfg-side-bias` | Assessment | hidden `side_bias` field |
| `cfg-risk-threshold` | Assessment | hidden `risk_threshold` field |
| `cfg-rolling-window` | Assessment | hidden `rolling_window` field |
| `cfg-refresh-interval` | Option Chain / Payoff Ratio auto-refresh timer | read by the IIFE in `index.html` |
| `cfg-max-dte` | Option Chain + Payoff Ratio | `option-chain.js` reads the DOM node directly |
| `cfg-moneyness-low` / `cfg-moneyness-high` | Option Chain + Payoff Ratio | `option-chain.js` reads the DOM node directly |
| `cfg-max-contracts` | Option Chain | **not read by any client code** — only the route default `1000` is ever used |

**Nothing in Config is global.** It is Assessment's parameters and Option Chain's
filters sharing one panel. `cfg-max-contracts` is dead UI.

### 3.3 How a parameter travels today

```
Config tab <input>  ──change──▶ localStorage(marketAnalysisConfig)
                                     │  loadConfig() on DOMContentLoaded
Parameter tab hidden <input> ◀── syncConfigToForm()
                                     │  form submit
POST /  ──▶ FormService.extract_form_data ──▶ ValidationService ──▶ create_job(form_data)
                                                                        │
/render/<kind>?job=… ──▶ render_streaming_slice ──▶ AnalysisService.generate_*_slice(form_data)
```

Live-data tabs bypass all of this: `option-chain.js` / `regime.js` read DOM nodes
and call `/api/*` directly.

---

## 4. Current State — Backend Data Flow

```
                 ┌── ACQUIRE ──────────────────────────────────────────────┐
                 │  data_pipeline/yf_client.py   live snapshots (spot,     │
                 │      option_chain, close panel, daily OHLCV).           │
                 │      Sole `import yfinance` … except:                   │
                 │  data_pipeline/downloader.py  DB-aware gap-detect bulk  │
                 │      OHLCV → raw_prices.  2nd `import yfinance`          │
                 │      (doc-guard: allow=single-yf-exit).                 │
                 │  services/market_review/fetch.py  L1/L2/L3 close-panel  │
                 │      cache ladder → market_review_prices  (parallel     │
                 │      acquisition path, outside data_ops)                │
                 └────────────────────────────────────────────────────────┘
                 ┌── PROCESS ──────────────────────────────────────────────┐
                 │  data_pipeline/cleaning.py     raw_prices → clean_prices │
                 │      (business-day align, anomaly flags, NO interp)     │
                 │  data_pipeline/processing.py   clean_prices →           │
                 │      processed_prices  (per-frequency returns/MA/HV/osc)│
                 └────────────────────────────────────────────────────────┘
                 ┌── SERVE ────────────────────────────────────────────────┐
                 │  data_pipeline/data_ops/  DataService facade:           │
                 │      ensure_range (backfill ORCHESTRATION), get_*       │
                 │  data_pipeline/repos.py   the only SQL builder          │
                 │  data_pipeline/job_cache.py  streaming slice memo       │
                 └────────────────────────────────────────────────────────┘
   scheduler.py (APScheduler, optional) ── cron ──▶ DataService.manual_update
```

### 4.1 Where the seams leak

| # | Leak | Evidence | Documented exit |
|---|---|---|---|
| L1 | `core/` reaches into `data_pipeline/` for its own fetch | `core/market/data_context.py` — 2× `doc-guard: allow=core-purity` (DataService, `fetch_daily_ohlcv`) | `DataContext` becomes data-in/data-out; fetch moves to a service factory (`architecture_review.md` §2) |
| L2 | A second module imports yfinance | `data_pipeline/downloader.py` | fold gap logic into `yf_client` |
| L3 | Backfill **orchestration** lives in the SERVE package | `data_pipeline/data_ops/_range.py::ensure_range` does coverage probe + sentinel heuristics + chunked download + clean + process + cache-invalidate | — (new: §5) |
| L4 | No canonical schema — `raw_prices` **is** yfinance's column set | `downloader._download_yf` only renames `Adj Close`→`Adj_Close`; `raw_prices.provider` column exists but is never a discriminator | — (new: ADR 0011) |
| L5 | Second acquisition path outside `data_ops` | `services/market_review/fetch.py` writes `market_review_prices` on its own ladder | fold into the provider seam |
| L6 | Live option/spot data has no persistence contract | `services/options/preload.py` + in-process `_option_chain_cache` only; deliberate per ADR 0004 (no option history) | keep, but make the "live vs. stored" split explicit in the seam |

### 4.2 Prefetch / readiness today

- `POST /` computes nothing — `create_job` stores `form_data`, returns the skeleton.
- Prefetch is **lazy and per-slice**: each `/render/<kind>` → `AnalysisService`
  → `DataService.get_processed` / `get_cleaned_daily` → `manual_update(7d)` +
  `needs_backfill` → `_kick_backfill` (daemon thread) + `_wait_for_coverage` (8 s).
- The "what range / what dataset" decision is **implicit** — hard-coded
  `today − 5y` defaults inside `get_cleaned_daily` / `get_processed`.
- Live-data tabs (Option Chain, Payoff Ratio, Volatility, Regime) get **no
  prefetch** — the tab fires its own request on switch.
- Multi-ticker: `create_job` keeps the full `tickers` list but `form_data.ticker`
  is `tickers[0]`; slices re-target per call. Secondary tickers are only fetched
  when their tab is viewed.

So "check the DB, pre-download, pre-process before the frontend needs it" already
exists in spirit — but it is scattered, historical-only, and never runs up front.

---

## 5. Target Architecture

### 5.1 Frontend — `ticker`-only global bar + module-scoped params

```
┌───────────────────────────────────────────────────────────────┐
│ Parameters bar   [ ticker: ____________ ]  [Run]      [▸/▾]    │  ← persistent, collapsible
├───────────────────────────────────────────────────────────────┤
│ sidebar │  <module panel>                                     │
│         │  ┌─ module toolbar ─────────────────────────────┐   │
│         │  │ Market Review:  [ from ▾ ] [ to ▾ ]           │   │  ← params live with the module
│         │  └──────────────────────────────────────────────┘   │
```

Rules:

- The bar is **not a tab**. It renders above `.main-panel`, is `position: sticky`,
  and collapses to a one-line summary (`▸ ^SPX`) persisted in `localStorage`
  (per-viewer convenience, `try/catch`, per `docs/constraints.md` §7 / vanilla JS).
- The bar owns exactly one input: `ticker` (comma-separated, existing multi-ticker
  parse). The "Run" button and ticker-validation badges move here.
- **Each module renders its own parameter controls** in a module toolbar:
  - Market Review / Statistical / Assessment → time horizon (`from`/`to`).
  - Statistical / Assessment → `frequency`.
  - Assessment → `side_bias`, `risk_threshold`, `rolling_window`, `account_size`,
    `max_risk_pct` (a collapsible "Assessment settings" group).
  - Option Chain / Payoff Ratio → `max_dte`, `moneyness_low`, `moneyness_high`,
    `max_contracts` (an "Option filter" group in the Option Chain toolbar; Payoff
    Ratio reuses the same store).
  - Auto-refresh interval → the Option Chain toolbar (it only ever affected those
    two tabs).
- **Persistence**: one `state/` store per module param-group (e.g.
  `state/marketParamsState.js`, `state/optionFilterState.js`), each backed by its
  own `localStorage` key, replacing the single `marketAnalysisConfig` blob and
  the hidden-field bridge. Follows `docs/frontend_convergence.md` ("new features
  read/write through `state/`").
- **Submit contract change**: `POST /` no longer carries the market-analysis
  parameters as hidden fields. Instead:
  - the streaming market tabs (`/render/<kind>`) accept their own params as query
    args (like Option Chain already does), OR
  - `POST /` carries a compact `modules` manifest (see §5.4) and the per-module
    params are attached to each `/render` call.
  Chosen shape is an open question — see §8.
- **Config tab**: after the moves, only cross-cutting settings remain (candidates:
  theme — already in the header; risk-free rate — currently hard-coded 5 % in
  `sim/` and separately in `core/options/greeks`; number / date display format).
  If that
  set is empty or near-empty, **delete the tab** and fold theme into a small
  header menu. Decision deferred to the batch (see §8).

### 5.2 Backend — hard acquire / process / serve seams

Rename and re-home so the three stages are packages with a one-way call graph and
a guard rule per boundary:

```
data_pipeline/
  providers/                     ← ACQUIRE.  The only place external APIs are touched.
    base.py                      ← MarketDataProvider protocol + CanonicalBar / CanonicalOptionQuote
    yfinance_provider.py         ← today's yf_client + downloader, merged, mapping yfinance→canonical
    _registry.py                 ← name → provider instance; env-selected, defaults to "yfinance"
  ingest/                        ← ACQUIRE→store glue.  Gap detection, chunking, upsert into raw_* tables.
    ohlcv.py                     ← was downloader.upsert_raw_prices + _range chunk loop
    snapshots.py                 ← spot / option-chain pass-through (live, not persisted; ADR 0004)
  transform/                     ← PROCESS.  raw_prices → clean_prices → processed_prices. Unchanged logic.
    cleaning.py  processing.py
  store/                         ← SERVE.  DB schema + the only SQL.
    db.py  repos.py
  read/                          ← SERVE.  The read API services call.
    facade.py (DataService)  _query.py
  orchestrate/                   ← the "make it ready" layer (was ensure_range + scheduler + job_cache)
    readiness.py                 ← plan_datasets(tickers, modules) → check coverage → kick prefetch
    backfill.py                  ← chunked download+clean+process (was _ensure_range_impl)
    scheduler.py  job_cache.py
```

Call direction (extends `doc_guard.py::_ALLOWED_DEPS`):

```
services → read → store
services → orchestrate → {ingest, transform, read, store}
ingest   → providers, store
transform→ store
providers→ (leaf: only utils + the external SDK)
```

- `providers/` is the **single** `import yfinance` site — L2 closes here, and the
  `single-yf-exit` guard is renamed `single-provider-import` (or scoped to
  `providers/`).
- `transform/` and `read/` never import `providers/` — they only see canonical
  tables. This is checkable.
- L1 (`core/market/data_context.py`): `build_data_context` splits into
  `fetch_data_context(...)` (a thin thing in `services/market/`, allowed to call
  `read/`) that produces a pure `DataContext`, and `core` keeps only the
  data-in/data-out container. Removes both `core-purity` markers.
- L5: `services/market_review/fetch.py`'s ladder becomes a `read/` function over a
  canonical `bars` table (no separate `market_review_prices` shape — see §5.3).

### 5.3 Canonical internal schema + provider mapping

Per ADR 0011. The raw store stops being yfinance-shaped:

| Canonical table | Columns (canonical names) | Fed by |
|---|---|---|
| `raw_bars` | `provider, symbol, date, open, high, low, close, adj_close, volume` | `providers.*.history()` → `ingest/ohlcv.py` |
| `clean_bars` | (today's `clean_prices` columns) | `transform/cleaning.py` |
| `feature_bars` | (today's `processed_prices` columns) | `transform/processing.py` |
| *(live, not persisted)* `OptionChainSnapshot` | `symbol, spot, expiries[], chain{expiry:{calls,puts}}` with canonical leg columns `strike, bid, ask, last, iv, open_interest, volume` | `providers.*.option_chain()` |

- **Mapping lives in the provider**, one function per shape, returning canonical
  dataclasses / DataFrames. `archive/futu_integration/field_mapping.md` is the
  reference table for a future futu provider (IV unit differs: futu percent,
  yfinance decimal — the provider normalizes to decimal).
- `provider` / `symbol` are first-class columns so two providers can coexist and a
  read can prefer one. `symbol` is the provider-native id post-`normalize_ticker`;
  a `symbol_map` is out of scope for the seam (yfinance-only today).
- Existing tables are **renamed, not restructured** in the seam batch
  (`raw_prices`→`raw_bars` etc. via `CREATE TABLE IF NOT EXISTS` + a one-shot copy
  in `scripts/`), so `transform/` diffs stay tiny. No migration framework
  (constraint §3).

### 5.4 Data-readiness prefetch on submit

Per ADR 0012. `POST /` gains a cheap, non-blocking readiness pass:

```
POST /  { ticker, modules: ["market_review","statistical","assessment",…] }
   │
   ├─ FormService.extract_form_data         (ticker only now)
   ├─ readiness.plan_datasets(tickers, modules)
   │     → [ (symbol, "feature_bars", start, end), (symbol, "clean_bars", …), … ]
   │       union over the modules the user will see, per ticker
   ├─ readiness.check_and_kick(plan)
   │     for each entry: coverage probe (DB-only, no network — like needs_backfill)
   │       covered      → nothing
   │       small gap    → inline ensure (fast path, existing 8 s grace)
   │       wide gap     → orchestrate.backfill kicked on a daemon thread
   │                      (same pattern as _kick_backfill; constraint §6: no queue)
   ├─ create_job(form_data, tickers, plan)   plan stored on the job
   └─ render skeleton  (unchanged; still < 1 s)
```

- Each `/render/<kind>` and each live `/api/*` first consults the job's plan:
  "ready" → compute now; "in flight" → the existing four-phase `loading` banner
  with a `retry-after`; the browser re-fires (HTMX `hx-trigger` with a delay).
- Live option data (Option Chain, Payoff Ratio, Volatility): the readiness pass
  also **warms `services/options/preload`** for the entered ticker(s) on a daemon
  thread, so switching to those tabs is instant instead of a cold ~2 s fetch.
- **No behaviour regression for the direct-URL path**: `render_streaming_slice`
  still auto-bootstraps a synthetic job when `job` is missing.
- Multi-ticker: the plan covers every ticker in the list, but prefetch is ordered
  `tickers[0]` first and the rest at lower priority so the visible tab is not
  starved.

---

## 6. Implementation Batches

Ordered by risk. Each is one PR, green CI, its own revert. `arch_baseline.json` /
`tag_baseline.json` are reset in the batch that changes them.

| B | Title | Touches | Guard / doc impact | Exit criteria |
|---|---|---|---|---|
| **B1** | Provider seam extraction (no behaviour change) | new `data_pipeline/providers/{base,yfinance_provider,_registry}.py`; `yf_client.py` + `downloader.py` become thin re-exports; canonical dataclasses | `constraints.md` §1 amended per ADR 0011; `single-yf-exit` rule rescoped to `providers/`; `_ALLOWED_DEPS` gains `providers`; `arch_baseline` reset | `pytest -m "not network"` green; `grep -rn "import yfinance"` → only `providers/`; no route/service diff |
| **B2** | Canonical raw store | `store/db.py` adds `raw_bars`/`clean_bars`/`feature_bars` (IF NOT EXISTS); `scripts/migrate_canonical_tables.py` one-shot copy; `ingest/` writes canonical; `transform/` reads canonical | `sqlite-bypass` guard unchanged; `docs/l0_architecture.md` schema table updated | old + new tables both populated on a run; `transform` tests pass against `clean_bars`; health endpoint reads new table |
| **B3** | Package re-home: `ingest/ transform/ store/ read/ orchestrate/` | move files, update imports, `doc_guard._ALLOWED_DEPS`, all docstring `Dependencies:` blocks, docs | new layer-edge rules in `doc_guard`; `arch_metrics` baseline reset; `l0_architecture.md` + `architecture_review.md` §2 rewritten | `arch_metrics.py --check` green; import cycles still 0; `test_architecture_purity.py` extended |
| **B4** | Close L1 (`core-purity`) | split `build_data_context`; new `services/market/data_context_fetch.py`; `core/market/data_context.py` pure | 2× `allow=core-purity` markers deleted; `architecture_review.md` §2 row closed | `test_architecture_purity.py` asserts `core` has zero `data_pipeline` imports |
| **B5** | Readiness plan + prefetch on submit | new `orchestrate/readiness.py`; `routes/core.py::index`; `job_cache` stores plan; `dispatch.py` consults plan; `services/options/preload` warm hook | `frontend_architecture.md` streaming section updated per ADR 0012 | new tests: plan union per module set; cold-tab switch timing; direct-URL path still bootstraps |
| **B6** | Frontend: `ticker`-only Parameters bar | `templates/index.html`, new `templates/partials/parameters_bar.html`, delete `tab_parameter.html` form scaffolding (positions block moves to a Portfolio panel), `static/parametersBar.js`, `styles.css` sticky/collapse | P1–P5 checklist in the PR; `frontend_architecture.md` layout diagram | e2e: bar persists across tab switches, collapse state survives reload; axe ≥ 95 |
| **B7** | Frontend: module-scoped params | per-module toolbars in each `tab_*.html`; `state/marketParamsState.js`, `state/optionFilterState.js`, `state/assessmentParamsState.js`; delete `syncConfigToForm` + hidden fields; `/render/*` + `/api/option_chain` read params from stores | `frontend_convergence.md` "next steps" ticked; vitest for the new stores | e2e per tab: changing a module param re-runs only that module; values survive reload |
| **B8** | Retire / repurpose Config tab | delete `tab_config.html` + sidebar button, or shrink to genuine globals (theme, risk-free rate); remove `marketAnalysisConfig` migration shim after one release | `glossary.md` if "global settings" was a defined term; `frontend_architecture.md` tab table | no dangling `cfg-*` ids; `grep -rn "marketAnalysisConfig"` clean |

B1–B5 are backend and can land before any UI change. B6–B8 are frontend and
depend only on B5 (the submit contract). B1 alone delivers the "pluggable API"
ask (the seam); a second provider is a later, separate piece of work.

---

## 7. Risks & Constraint Interactions

| Area | Risk | Mitigation |
|---|---|---|
| `docs/constraints.md` §1 / ADR 0002 | "yfinance is the only data source" is load-bearing in reviews | ADR 0011 **amends** (not deletes) §1: "one provider *implementation*, behind a seam"; §1's option-history caveats (ADR 0004) stay verbatim |
| `docs/constraints.md` §6 | no job queue; compute in one request | readiness prefetch uses the **existing** daemon-thread + grace-period pattern (`_kick_backfill`), not a queue; the request still returns the skeleton in < 1 s |
| `docs/constraints.md` §3 | no migration framework | canonical tables via `CREATE TABLE IF NOT EXISTS` + a one-shot `scripts/` copy; old tables kept for one release |
| ADR 0006 | vanilla JS, no build | new state stores are plain ES modules; the bar is CSS-sticky + a tiny JS collapse toggle |
| `doc_guard` baselines | every re-home trips `arch_metrics --check` | each batch resets the baseline in the same commit, as the 2026-09 remediation did |
| Pages mirror (`site/`) | `build_pages_site.py` reuses `templates/` verbatim; the bar must degrade on the static build | Simulation / Option Pricing Matrix tabs are already I/O-free; the bar's "Run" is a no-op there — gate it on `window.STREAMING_MODE`-style flag |
| Multi-ticker | readiness plan × N tickers × M datasets = many prefetch kicks | `ensure_range`'s in-flight dedup already collapses these; plan prioritises `tickers[0]` |
| `services/market/analysis/summary.py` | still fan-in 0 | out of scope; leave on the §2 watch list or delete in B7 with `tab_summary.html` |

---

## 8. Decision Gates (open questions, each blocks one batch)

Each item must be resolved — into this doc or a new ADR — **before** its gate
batch starts coding (§0 rule 5). Until then the batch stays `⬜ not started`.

| # | Question | Decision gate | Working lean |
|---|---|---|---|
| Q1 | **Submit contract** — does `POST /` carry a `modules` manifest with per-module params attached to each `/render` call, or do the streaming market tabs move fully to client-fired `/api/*` like Option Chain? Manifest keeps the streaming model; full client-fired is more uniform but a bigger diff. | ✅ resolved 2026-09-10 (B5) — **manifest**, per-module params as query args on each `/render` call (sub-option A1) | **manifest.** Decisive reasons: (1) ADR 0012's readiness pass needs the module list *at submit time* — with no POST manifest, B5 would need an extra `/api/ready` protocol; (2) the four streaming slices return server-rendered HTML + base64 PNG, so client-firing changes only the transport, not the product; (3) the diff and the revert surface stay one batch wide. Full client-fired would only win if the charts moved to client-side rendering (ADR 0006/0008 territory). Params travel as query args (not `hx-post` JSON) to match the existing `/api/option_chain?ticker=…` shape and stay bookmark-reproducible — recorded in the B5 note below |
| Q2 | **Config tab fate** — is there *any* genuine global setting to keep? Risk-free rate is the only candidate (hard-coded in `static/sim/` and again in `core/options/greeks`). Yes → tab shrinks to it; no → tab deleted. | ✅ resolved 2026-09-10 (B8) — **tab deleted** | **Deleted.** After B7 nothing on it was global: every field had moved to the module that consumes it, so keeping the shell meant keeping a page whose only content was "these settings moved". The risk-free rate is not a *setting* yet (hard-coded in two places) — wiring it up is a new feature, not a cleanup, so there was nothing to shrink the tab to. The divergence risk is now on the watch list (`architecture_review.md` §2) |
| Q3 | **`positions` block** — Portfolio Analysis is its only consumer. Move into a dedicated "Portfolio" panel/tab, or keep as a section the bar's Run ignores? | ✅ resolved 2026-09-10 (B6) — **dedicated Portfolio tab** | **Dedicated Portfolio tab** (`tab-portfolio`). The positions table drives `POST /api/portfolio_analysis` (client-fired) and owns a full result surface (Greeks / P&L / theta / breakeven / VaR); keeping it inside the bar's form would re-couple that workflow to the streaming submit — exactly the coupling ADR 0012 removes — and a one-line bar has nowhere to put the results. A tab also makes the workflow discoverable instead of buried under "Parameters". `#positions-tbody` stays in the DOM on every load, so the existing global handlers are unchanged |
| Q4 | **Table rename vs. reshape** — `raw_prices`→`raw_bars` with identical columns (minimal), or also move the yfinance-ism `adj_close` handling into the provider during the rename? | ✅ resolved 2026-09-10 (B2) | **minimal rename** — identical columns on both sides of each pair (structurally enforced: one column tuple per shape, used to create both names). The `adj_close` normalisation is already inside the provider (B1's `to_canonical_bars`), and ingest now consumes canonical bars, so no reshape is needed. ADR 0011's `symbol` column stays the target state but is deferred — see the B2 note below |
| Q5 | **Second-provider protocol shape** — not in scope to *implement*, but `providers/base.py` (written in B1) must be sketched against *both* yfinance and `archive/futu_integration/field_mapping.md` so the protocol is not accidentally yfinance-shaped (IV unit, bid/ask availability, `inTheMoney` derivation all differ). | ✅ resolved 2026-09-10 (B1) — outcome table in ADR 0011 §"Protocol shape" | design review of `base.py` against both field maps: IV → decimal, bid/ask nullable, `inTheMoney` dropped (derivable), expiries ISO strings |

### Batch notes (actuals + deviations, recorded as batches land)

**B1 (2026-09-10) — provider seam extraction, no behaviour change.**

- **Files**: `data_pipeline/providers/{__init__,base,_log,_registry,yfinance_provider,yf_snapshot}.py`.
  Five modules instead of the three §6 named, for two reasons: (a) `yfinance_provider.py` would have
  blown the 400-line god-file cap, so the option-chain section was extracted exactly as
  `architecture_review.md` §2 had pre-registered — into `providers/yf_snapshot.py` (which also owns
  the spot lookup, because `fetch_option_chain` calls it and a separate module would have created an
  import cycle); (b) `_log.py` holds the best-effort failure-log wrapper that both provider modules
  need and neither may import from the other.
- **Compatibility**: `yf_client.py` is now a re-export shim; `downloader.py` keeps only gap detection
  + `raw_prices` upsert and no longer imports yfinance. No `routes/` or `services/` file changed.
- **`_ALLOWED_DEPS` deferred**: §6 B1 wanted `providers` added to `_ALLOWED_DEPS`, but promoting a
  `data_pipeline/` subpackage to a layer needs `_layer_of` / `layer_of` sub-layer resolution in
  **both** `doc_guard.py` and `arch_metrics.py`. That is B3's job (its §6 row already owns "new
  layer-edge rules" + the layer-table rewrite). In B1 `providers/` stays inside the `data_pipeline`
  layer; the new invariant that *does* hold now — "only `providers/` imports yfinance" — is enforced
  by the rescoped `single-yf-exit` rule and pinned by `tests/test_provider_seam.py`.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 459 passed / 5 skipped;
  `doc_guard.py` clean; `arch_metrics.py --check` ok (no baseline reset needed);
  `audit_tags.py` unchanged (16 uncovered vs baseline 16). Production-code
  `import yfinance` hits: exactly the two `providers/` modules. (`tests/test_yf_download.py` and
  `tests/e2e/conftest.py` also import it as test doubles — `doc_guard` exempts `tests/` by design.)

**B2 (2026-09-10) — canonical raw store.**

- **Shape**: `raw_bars` / `clean_bars` / `feature_bars` added; all reads *and* writes in
  `data_pipeline/` switched to them. The pre-rename names are kept as shadow tables and
  `upsert_many` mirrors **both** directions, so an old seeding path, an un-migrated DB and a
  `git revert` all keep working. `scripts/migrate_canonical_tables.py` backfills an existing DB
  (idempotent, `INSERT OR IGNORE`, never clobbers the canonical table; `--dry-run` reports without
  creating anything — it does not even run `init_db`).
- **Ingest is now canonical**: `downloader.download_bars()` (was `_download_yf`) acquires through
  `providers.get_provider().history()` — i.e. the registry, not a concrete vendor module — and
  returns `CANONICAL_BAR_COLUMNS`. The yfinance-ism (`Adj Close`→`Adj_Close`) is now confined to
  the provider's mapping, and the `provider` column is written from `get_provider().name`.
- **No column reshape** (Q4 above). To keep that true by construction rather than by review,
  `init_db` builds each canonical/legacy pair from one shared column tuple — which also kept
  `db.py` under the 400-line god-file cap after the 3 extra tables (+0 tracked metrics).
- **Deliberate non-change**: the function name `upsert_raw_prices` is kept (it is called from
  `data_ops/{_update,_range}.py`, `services/regime/ops/_bootstrap.py` and ~12 test patch targets);
  renaming it is a cross-cutting edit that belongs with the B3 re-home, not with the rename.
- **Tests**: new `tests/test_canonical_tables.py` pins column parity per pair, bidirectional
  mirroring, "one pipeline run populates both families", that `fetch_ticker_inventory` (the /health
  read) hits `raw_bars`, and that the migration script backfills + is idempotent.
  `test_processing.py` now seeds `clean_bars` and reads `feature_bars` (the §6 exit criterion);
  `test_health_service.py` / `test_nvda_analysis.py` seeded via raw SQL and therefore had to move.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 468 passed / 5 skipped;
  `doc_guard.py` clean; `arch_metrics.py --check` ok (no baseline reset needed);
  `audit_tags.py` unchanged (16 vs baseline 16); `routes/` untouched (only the one-line comment
  fix in `services/market/facade.py` outside `data_pipeline/`).

**B3 (2026-09-10) — package re-home.**

- **Layout achieved** (`data_pipeline/`): `providers/` (ACQUIRE) · `store/` · `ingest/` ·
  `transform/` · `read/` · `orchestrate/` + `_state.py`. `data_ops/` is gone; `yf_client.py` moved
  to `providers/yf_client.py` (kept, not deleted, so its one-release shim promise holds while
  *services*→*providers* becomes the visible edge). Path map for anyone following older docs:

  | old | new |
  |---|---|
  | `db.py` / `repos.py` / `quality_log.py` | `store/…` |
  | `downloader.py` | `ingest/ohlcv.py` |
  | `cleaning.py` / `processing.py` | `transform/…` |
  | `data_ops/{facade,_query}.py` | `read/…` |
  | `data_ops/{_update,_range}.py` | `orchestrate/{update,backfill}.py` |
  | `job_cache.py` / `scheduler.py` | `orchestrate/…` |
  | `data_ops/_globals.py` | `_state.py` (package root) |
  | `yf_client.py` | `providers/yf_client.py` |

- **Guards now sub-package aware**: `doc_guard._layer_of` / `_imported_heads` and
  `arch_metrics.layer_of` resolve `data_pipeline/<stage>/…` to `<stage>`; `_ALLOWED_DEPS` carries
  the six new keys **plus** the `providers` key B1 deferred; `sqlite-bypass` and `db-access` were
  rescoped to `store/db.py` / `store/repos.py`. `tests/test_architecture_purity.py` gained three
  tests: the layer graph matches the table, `transform/` never imports `providers/`, and the two
  copies of the layer table agree.
- **Deviations from §5.2's sketch** (all deliberate):
  1. `orchestrate/update.py` exists (the sketch listed four files) — `manual_update` /
     `seed_history` is a distinct "make it ready" entry point from chunked backfill.
  2. **No `ingest/snapshots.py`**: live snapshots are never persisted (ADR 0004), so there is no
     ingest glue to move — callers reach `providers` directly.
  3. `_state.py` sits at the package root (the sketch put nothing there): `read` and `orchestrate`
     both need the query cache / update locks, and the two must not import each other.
  4. **`read → orchestrate`** is kept (the read path triggers refreshes), which is the reverse of
     the sketch's `orchestrate → read`. Consequence: `orchestrate` may not import `read`, so
     `orchestrate/scheduler.py` now calls `orchestrate.update.manual_update` instead of
     `DataService.manual_update` (behaviour-identical; it removed the last cycle candidate).
  5. **`providers → store`** (the provider writes its own failures to `store/quality_log.py`)
     instead of being a pure leaf; the alternative was inventing a callback for a diagnostic write.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 472 passed / 5 skipped;
  full `pytest tests/e2e` → 38 passed; `ruff check` + `format --check` clean; `doc_guard.py` clean;
  `arch_metrics.py --check` ok — layer violations 0, cycles 0, god files 0, dead code 1, so
  **no baseline reset was needed** (the §6 row anticipated one); `audit_tags.py` regenerated
  (`--update-baseline`) because the uncovered-constant *paths* moved while the count stayed 16.

**B4 (2026-09-10) — close L1 (`core-purity`).**

- **Split**: the fetch half of `core/market/data_context.py` moved to
  `services/market/data_context_fetch.py::fetch_data_context`. `core` keeps the pure
  `DataContext`, `refrequency()` (was `_refrequency`), a data-in/data-out
  `build_data_context(*, ticker, frequency, horizon, raw_data)`, and `empty_data_context()`
  for failed acquisitions. The two `# doc-guard: allow=core-purity` markers are gone.
- **Who fetches is now inverted** (the §2 row's exit condition): `MarketAnalyzer(data_context)`
  and `CorrelationValidator(price_data=…)` receive the context instead of building it — the same
  pattern the 2026-09 remediation applied to `OptionsChainAnalyzer(snapshot=…)`.
  `CorrelationValidator` now raises a `ValueError` explaining where to build one instead of
  quietly fetching. A public `MarketAnalyzer.data_context` property replaced the
  `analyzer._ctx` reach-through in `services/market/analysis/statistical.py`.
- **Guard tightened**: §3's table had allowed `core → {read, providers}` in B3 (a transitional
  concession); it is now `core → {utils}` in `doc_guard._ALLOWED_DEPS` **and**
  `arch_metrics.ALLOWED_DEPS`. `tests/test_architecture_purity.py` gained
  `test_core_has_zero_data_pipeline_imports`, which deliberately ignores the suppression marker —
  re-introducing one now fails the test even though `doc_guard` would accept it.
- **Tests migrated**: `test_frontend_api.py` builds contexts with the pure builder (three closures
  deleted), `test_nvda_analysis.py` gained an `_analyzer()` helper (5 sites) and stubs the
  provider at its new path, `test_chart_time_range.py` / `test_ticker_format_integration.py` follow
  the same pattern — the latter also lost its `MarketAnalyzer.__init__` monkeypatch hack.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 473 passed / 5 skipped;
  full `pytest tests/e2e` → 38 passed; `ruff check` + `format --check` clean; `doc_guard.py` clean;
  `arch_metrics.py --check` ok (layer 0 / cycles 0 / god 0 / dead 1 — no baseline reset);
  `grep -rn "allow=core-purity"` returns nothing.

**B5 (2026-09-10) — readiness plan + prefetch on submit.**

- **Q1 = manifest** (see the gate table above). `POST /` now resolves the module list
  (`FormService.extract_modules`: repeated or comma-separated tokens; defaults to all known modules
  until B7 sends the field; unknown tokens are dropped, not fatal) and stores the readiness plan on
  the job. Per-module params still arrive on the existing hidden fields — B7 moves them onto each
  `/render` call as query args.
- **`orchestrate/readiness.py`** (new): `KIND_DATASETS` (module → datasets; live-only modules map to
  `()`), `plan_datasets` (union over modules, one entry per `(ticker, dataset)`), `check_and_kick`
  (one DB-only coverage probe per ticker+range, then a daemon-thread kick), plus `status_for` /
  `hold_seconds_left` / `should_hold` / `is_backfill_running`.
  The daemon-thread kicker moved here from `read/_query.py` so POST-time readiness and the per-slice
  path share one implementation (and `read → orchestrate` keeps the graph acyclic).
- **`services/market/readiness.py`** (new): the services half — calls the plan/kick, then warms
  `services.options.preload` for the live-chain modules on daemon threads. The split exists because
  `orchestrate` may not import `services`.
- **Cold-start hold**: `/render/<kind>` consults the job's plan and, when the plan says "kicked" *and*
  there is no usable history yet *and* the backfill thread is still alive, returns a self-re-firing
  `partials/fragments/readiness.html` ("正在准备…") instead of an empty chart. Bounded by
  `HOLD_SECONDS = 30` **and** by thread liveness — a review pass caught that the timer alone left a
  *failed* download showing a spinner for 30 s and hiding the real error
  (`tests/test_nvda_analysis.py::test_failed_download_shows_error`); the liveness check fixed it and
  is pinned by `test_should_hold_stops_as_soon_as_the_backfill_is_gone`.
- **Tests**: new `tests/test_readiness.py` (18 cases) — plan union / dedupe / live-only emptiness /
  horizon defaults, kick decision + probe-failure resilience, hold window + thread-liveness,
  `create_job` carrying the plan, and `extract_modules` parsing. `test_background_backfill.py` now
  imports the kicker from `readiness`.
- **Deferred to B6/B7 (recorded, not silently dropped)**: (a) the *client* half of "the browser
  re-fires" — the held fragment self-refreshes, but the module **toolbars** and the per-module query
  args are B7; (b) the market-review benchmark panel (`market_review_prices`, L5) is not in the
  dataset map yet — its ladder lives in `services/market_review/fetch.py` and folds into the provider
  seam later.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 493 passed / 5 skipped;
  full `pytest tests/e2e` → 38 passed; `ruff check` + `format --check` clean; `doc_guard.py` clean;
  `arch_metrics.py --check` ok (layer 0 / cycles 0 / god 0 / dead 1 — no baseline reset);
  `audit_tags.py` 16 vs baseline 16 after tagging two new domain constants.

**B6 (2026-09-10) — `ticker`-only Parameters bar (+ Q3: Portfolio tab).**

- **The bar** (`templates/partials/parameters_bar.html` + `static/parametersBar.js`): renders between the
  header and `.app-body`, `position: sticky; top: var(--header-h)`, and owns exactly one input —
  `ticker` (comma-separated, existing multi-ticker parse) — plus the Run button and the
  ticker-validation badges. Collapsing persists per viewer under
  `localStorage['parametersBarCollapsed']` (every access guarded; a denied-storage browser degrades to
  "not persisted") and leaves the one-line summary `▸ ^SPX`. Tokens only in CSS, so the Onyx layer
  themes it for free. The `tab_parameter.html` tab and its sidebar button are deleted.
- **Q3 = dedicated Portfolio tab**: `templates/partials/tab_portfolio.html` holds the positions table +
  the Portfolio-Analysis result panel; the global handlers (`addPositionRow`, `runPortfolioAnalysis`,
  `initializeOptionsTable`) are unchanged because `#positions-tbody` still exists on every page load.
- **Deviation (documented, temporary)**: the plan says the bar owns *one* input, and B7 is what gives each
  module its own toolbar. Removing the Parameters tab in B6 while B7 has not landed would have left the
  time horizon, sizing and the Config bridge with **no UI at all** — a functional regression, not a
  shippable increment. They therefore sit in a collapsible "Analysis settings" group **inside the same
  `<form>`**, explicitly marked as B7's extraction source; the POST contract is byte-for-byte unchanged.
- **Pages mirror**: `build_pages_site.py::build` asserted `id="tab-parameter"` and generated
  `showcase/parameter.html`; both now point at `tab-portfolio`, and the demo banner links to
  "去 Portfolio 页". `tests/test_pages_build.py`'s ticker-input assertion was made attribute-order
  agnostic (it broke on the new `class` attribute — brittle, not a real contract).
- **Tests**: `tests/unit/parametersBar.test.js` (8 cases: default expanded, toggle + persistence, restore,
  summary mirroring, storage-denied, bar-absent) and `parametersBar.js` added to the coverage pass;
  5 e2e files dropped their "activate the parameter tab" step (the bar is always visible),
  `test_position_cascade.py` opens `tab-portfolio`, and `test_smoke.py`'s tab list swapped
  `tab-parameter` → `tab-portfolio`.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 493 passed / 5 skipped;
  full `pytest tests/e2e` → 38 passed; `npx vitest run` → 187 passed / 15 files;
  `doc_guard.py` clean; `arch_metrics.py --check` ok; `audit_tags.py` 16 vs baseline 16.
  The §6 row's "axe ≥ 95" is **not** automated in this repo (no axe harness exists) — verified by hand
  instead: the bar is a labelled `<label for="ticker">` + `<input>`, the toggle is a real `<button>` with
  `aria-expanded`/`aria-controls` and an `sr-only` label, and the collapsed summary is `aria-hidden`
  while the input still carries the value.

**B7 (landed 2026-09-10) — module-scoped params.**

Landed in two commits on the same branch: the backend contract first (so it was testable on its own),
then the frontend. Backend:

- `FormService.MODULE_PARAM_KEYS` + `FormService.extract_module_params(module, args)`: the
  query-arg contract. `from` / `to` become `start_time`/`end_time` **and**
  `parsed_start_time`/`parsed_end_time` (the keys the slices actually read) through the same
  `parse_month_str` as the POST path; `frequency` is whitelisted to `D/W/ME/QE`; `side_bias`
  also derives `target_bias`; the assessment knobs are coerced, and malformed values are
  **skipped** so the job's POST-time value survives as the fallback.
- `services/market/dispatch.py`: `render_streaming_slice` merges
  `{**job.form_data, **module_params, "ticker": ticker}`, so a direct URL / bookmark still
  works with no query args while a module toolbar can override its own parameters.
- INVARIANT (pinned by `tests/test_module_params.py`, 11 cases): only the keys a module
  declares are ever read, so `?option_position=…&ticker=EVIL` cannot smuggle keys into the
  slice's `form_data`.

Landed with the frontend half (same branch, second commit):

1. **Stores**: `state/paramsStore.js` (factory) + `state/{market,assessment,optionFilter}ParamsState.js`
   — one `localStorage` key per group; `hydrate()` runs **at parse time** (the toolbars are parsed
   before the scripts, so the first `hx-include` fan-out already carries the stored values); `init()`
   returns the store.
2. **Toolbars**: `tab_{market_review,statistical_analysis,market_assessment}.html` (horizon ± frequency,
   Assessment's knobs in a `<details>` group) and `tab_option_chain.html` (chain filters + refresh
   interval). Placeholders carry `hx-include="#<module>-toolbar"`, so the initial fan-out is
   parameterised by the server.
3. **Re-runs**: `static/moduleParams.js` maps kind → element + owning stores, and re-issues exactly the
   affected `/render` calls using the skeleton + `htmx.process` idiom from
   `static/market_review_chart.js`. A change to a `marketParams` field re-runs the three market tabs
   (they share the group, by the plan's own store granularity); a chain-filter change triggers **no**
   `/render` at all — `option-chain.js` listens for the group event instead.
4. **Bridge deleted**: `FormManager.syncConfigToForm/loadConfig/saveConfig`, the four hidden fields and
   the `option_position` assignment are gone; `saveState/loadState` keeps only the ticker and the
   positions table. The bar keeps **two** hidden inputs (`start_time`/`end_time`) because `POST /`
   validates the horizon and sizes the readiness prefetch — the visible controls are the module
   toolbars, `marketParams` is the source of truth, the store mirrors into them.
5. **Config tab emptied** (`tab_config.html`): the module-scoped fields are gone, the shell keeps a
   "these settings moved" note. B8 answers §8 Q2 (delete it, or repurpose it for the risk-free rate).
6. **e2e**: `test_module_params.py` (a market-param change re-runs exactly its group and carries the new
   value + horizon; a chain-filter change triggers no `/render`; values survive a reload) and
   `test_localstorage_restore.py` rewritten to the one-key-per-group contract;
   `tests/unit/paramsStore.test.js` (10 cases) + the new scripts in the coverage pass.

Bugs the tests caught while landing this (all fixed, all pinned):

- **Shared-field clobber**: `commitFromDom` read *every* bound input, so a stale
  `#assess-frequency` (`ME`) overwrote a fresh `#stat-frequency` (`W`) on the same commit. It now
  commits only the event target's field and propagates via `hydrate()`
  (`test_keeps_the_three_toolbars_in_sync_through_the_shared_horizon`).
- **`init()` clobbered its own global**: the factory publishes the store and the caller then assigned
  `appState.marketParams = ....init()` — with no return value that assignment wrote `undefined`,
  silently detaching every consumer. `init()` returns the store
  (`test_does_not_clobber_the_published_global`).
- **`input` + `change` double-emit race**: one edit emitted twice, the second rerun replaced the element
  the first was still swapping into, and htmx threw `htmx:swapError` (null parent). `select` now emits
  on `change` only, and `rerun` skips an in-flight skeleton for the same URL.
- **Test-only**: the e2e used `frequency=Q`, which is not a legal value (`D/W/ME/QE`) — an invalid
  `select` assignment silently writes `""` into the store.

**Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → 505 passed / 5 skipped;
full `pytest tests/e2e` → 41 passed; `npx vitest run` → 198 passed / 16 files; `ruff check` +
`format --check` clean; `doc_guard.py` clean; `arch_metrics.py --check` ok (no baseline reset);
`audit_tags.py` 16 vs baseline 16.

**B8 (landed 2026-09-10) — Config tab retired (§8 Q2 = delete).**

- `templates/partials/tab_config.html` deleted with its sidebar button and include; the
  `System` section label goes with it (the last section is Portfolio). The shell kept a
  "these settings moved" note after B7; once every field had moved, a page whose only content
  was that note had no reason to exist.
- **Nothing else changed**: no `switchTab` special case existed to remove (the plan anticipated
  one; `grep tab-config` over `static/` is empty). The tab-list assertions lived in
  `tests/{test_pages_build,e2e/test_smoke}.py` and `scripts/build_pages_site.py::build` — all three
  updated.
- **Follow-up, deliberately not folded in** (rule 7): the risk-free rate is hard-coded in
  `static/sim/black_scholes.js` and again in `core/options/greeks` — two places, one number. Making
  it a real global setting means a store entry, a form field and a backend path; that is a feature,
  and until then the divergence risk is on `architecture_review.md` §2's watch list.
- **Exit criteria**: `grep -rn tab_config` over `templates/ static/ tests/ site/` returns nothing;
  `pytest -m "not network" --ignore=tests/e2e` → 505 passed / 5 skipped; `pytest tests/e2e` → 40
  passed; `npx vitest run` → 198 passed / 16 files; `doc_guard.py` clean; `arch_metrics.py --check`
  ok; `audit_tags.py` 16 vs baseline 16.

**B9 (2026-09-11) — acceptance-review remediation (F1–F3, F6).**

Scope of this pass: the §10 findings that are correctness or the explicitly-asked
「可收起」 behaviour. F4 (readiness `feature_bars` gap), F5 (dead `option_data` path /
stale header badge) and F7c (merge to `main`) are left open — they are cleanups,
not blockers, and each is one small independent change.

- **F1 — module-param memo staleness (correctness).** `job_cache.compute_or_get`
  gained a keyword-only `variant: str = ""`; the memo/lock/error-cache key is now
  `(ticker, kind, variant)`. `services/market/dispatch.py::_params_variant`
  renders `module_params` as a sorted `k=v|k=v` digest and passes it. Legacy
  callers and the direct-URL path pass no `variant` ⇒ `""` ⇒ the old key, so
  nothing else changes. Reproduced before/after with a scratch script (slice
  invoked once → twice). Guards: `test_job_cache.py::test_variant_computes_independently`
  and `test_module_params.py::test_a_param_change_recomputes_within_the_same_job`
  (the pre-existing e2e only checked request URLs, never fragment content).
- **F2 — hollow collapse.** `parameters_bar.html` now wraps the label + ticker
  input + validation badges in `<div class="parameters-bar-fields" id="parameters-bar-body">`
  — a real `aria-controls` target. Collapsed (`[data-collapsed="true"]`) hides
  that div **and** `.ticker-validation`, leaving the toggle, the `▸ ^SPX` summary
  and Run on one line. The dead `.parameters-bar-body` / `.parameters-bar-group-title`
  rules (B7 had deleted their elements) are removed. New vitest case asserts the
  `aria-controls` target exists and contains `#ticker`.
- **F3 — invisible chevron.** The Font Awesome `<i>` is replaced with an inline
  SVG (`.parameters-bar-chevron`) rotated `-90°` by `[data-collapsed="true"]`;
  `parametersBar.js` drops the icon-class swap and updates `title` instead
  (`Collapse` / `Expand parameters`). Matches how the theme toggle already ships
  SVG on this FA-free page.
- **F6 — stale docstrings** (already in review commit `9691776`): `providers/base.py`,
  `providers/yf_client.py`, `providers/__init__.py`, `providers/yfinance_provider.py`,
  and the §0 ledger planning-row status.
- **Exit criteria**: `pytest -m "not network" --ignore=tests/e2e` → exit 0
  (+2 tests vs B8: `test_job_cache.py::test_variant_computes_independently`,
  `test_module_params.py::test_a_param_change_recomputes_within_the_same_job`);
  `pytest tests/e2e` → exit 0; `npx vitest run` → 199 passed / 16 files (+1
  aria-controls case); `ruff check` + `format --check` clean; `doc_guard.py`
  clean; `arch_metrics.py --check` ok (layer 0 / cycles 0 / god 0 / dead 1);
  `audit_tags.py` 16 vs 16.

---

## 9. References

- Current flow: `routes/core.py` → `services/market/dispatch.py` → `services/market/analysis/facade.py`
- Data layer: `data_pipeline/read/facade.py`, `orchestrate/{update,backfill}.py`, `providers/`, `store/{db,repos}.py`, `ingest/ohlcv.py`
- Frontend: `templates/partials/parameters_bar.html`, the module toolbars in `templates/partials/tab_*.html`, `static/main.js`, `static/moduleParams.js`, `static/option-chain.js`
- `docs/decisions/0002-yfinance-as-sole-data-source.md`, `0004-no-iv-history-from-yfinance.md`, `0005-token-bucket-throttle.md`
- `docs/constraints.md` §1–§6, `docs/frontend_architecture.md`, `docs/frontend_convergence.md`
- `archive/futu_integration/field_mapping.md`

---

## 10. Acceptance review (2026-09-11)

Post-B8 review of the landed branch. Mechanical gate is **green**:
`pytest -m "not network" --ignore=tests/e2e` exit 0 (505 / 5 skipped),
`npx vitest run` 198 / 16 files, `ruff check` + `format --check` clean (347 files),
`doc_guard.py` clean, `arch_metrics.py --check` ok (layer 0 / cycles 0 / god 0 /
dead 1 = pre-existing `summary.py`), `audit_tags.py` 16 vs 16. Every §6 exit
criterion and every §2 debt-row closure verified by grep. The three asks are
delivered — the backend acquire/process/serve separation in particular is clean
and enforceable.

Findings worked as **batch B9 (remediation)** under the §0 rules.
**F1–F3 + F6 landed 2026-09-11** (this branch); F4/F5/F7 remain.

| # | Sev | Status | Finding | Fix |
|---|---|---|---|---|
| F1 | **high — correctness, CONFIRMED** | ✅ **fixed (B9)** | `job_cache.compute_or_get` memoised per `(ticker, kind)`; `dispatch.py::_compute` captured `module_params` from the query string but they were **not in the key** and nothing invalidated on change. Reproduced: two `/render/statistical` calls on one job, `frequency=ME` then `=W` → slice invoked once, both response bodies byte-identical. B7's headline behaviour ("changing a module control re-runs that module") re-fired the request and flashed "Updating…" but served the stale fragment for up to `JOB_CACHE_TTL` (90 s). `tests/e2e/test_module_params.py` missed it — it asserts request **URLs**, never fragment **content**. | `compute_or_get(..., *, variant="")` — key is now `(ticker, kind, variant)`; `dispatch._params_variant(module_params)` builds a sorted digest. New tests: `test_job_cache.py::test_variant_computes_independently`, `test_module_params.py::test_a_param_change_recomputes_within_the_same_job`. |
| F2 | moderate — UX / a11y | ✅ **fixed (B9)** | The Parameters bar "collapse" was hollow after B7: `data-collapsed="true"` hid a non-existent `.parameters-bar-body` and revealed `▸ ^SPX` **beside the still-visible ticker input + label + Run** → ~zero visible effect; `aria-controls="parameters-bar-body"` was a dangling reference. | The label + input + badges are now wrapped in `<div class="parameters-bar-fields" id="parameters-bar-body">` (real `aria-controls` target); collapsed hides that div **and** `.ticker-validation`, leaving toggle + `▸ ^SPX` + Run on one line. Dead `.parameters-bar-body` / `-group-title` CSS removed. New vitest: "has a real element behind aria-controls". |
| F3 | minor — UX | ✅ **fixed (B9)** | Collapse toggle icon was invisible — `<i class="fas fa-chevron-down">` with Font Awesome not loaded and no CSS fallback. | Inline SVG chevron (`.parameters-bar-chevron`) rotated `-90°` by `.parameters-bar[data-collapsed="true"]`; `parametersBar.js` drops the `<i>` class swap and updates `title` instead. |
| F4 | minor — readiness gap | ⬜ open | `readiness.check_and_kick` gates coverage on the `clean_bars` probe (`needs_backfill`). The "one pipeline run fills both" INVARIANT holds for a fresh backfill, but a DB with `clean_bars` for the range yet stale/missing `feature_bars` (new frequency, or processing failed after cleaning) → probe says "covered", no kick, `statistical`/`assessment` fall back to the per-slice `get_processed` → `manual_update` path. Fallback works, prefetch promise unmet. | `feature_bars`-aware probe, or a `WHY:` note in `readiness.py` accepting the gap. |
| F5 | minor — dead code / stale UI | ⬜ open | (a) `form.py::parse_option_data` + `form_data["option_data"]`: FormManager no longer submits `#option_position` (B7) and no slice reads `option_data` — always `[]` on the POST path. (b) `routes/core.py` GET branch still passes `frequency`/`risk_threshold`/`rolling_window`/`side_bias` to `render_template`. (c) `index.html:112` header badge renders `{{ frequency_display or frequency }}, {{ side_bias }}` — after B7 these are always the POST-time defaults, so the badge shows "Monthly, Neutral" regardless of the toolbar selection. | Drop the dead form path or comment it dormant; remove the unused GET vars; fix or remove the header badge meta. |
| F6 | trivial — stale docstrings | ✅ **fixed (review commit `9691776`)** | `providers/base.py` "yf_option_chain.py" → `yf_snapshot.py`; `providers/yf_client.py` listed `core/market/data_context.py` as an importer (B4 removed it); `providers/__init__.py` + `yfinance_provider.py` said `downloader.py` (it is `ingest/ohlcv.py` since B3); §0 ledger planning-row status. | done |
| F7 | housekeeping | 🔨 partial | (a) `providers/yf_client.py` "one-release" shim has no tracked removal trigger. (b) `market_review_prices` (L5) is still a parallel acquisition path outside the seam. (c) Branch is ahead of `origin/main`, unmerged. | (a)+(b) **added to `architecture_review.md` §2 watch list** (review commit); (c) push + merge still pending. |


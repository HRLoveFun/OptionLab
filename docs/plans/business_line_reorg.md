# Reorganization Plan: Business Lines, Parameter Ownership & Data-Pipeline Seams

**Date**: 2026-09-10 (plan) | **Owner**: repo owner
**ADRs**: [0011](../decisions/0011-pluggable-data-provider-seam.md) (data-provider seam + canonical schema — **Accepted**),
[0012](../decisions/0012-parameter-ownership-and-prefetch.md) (parameter ownership + readiness prefetch — **Accepted**)

> **Status: ACCEPTED TARGET, NOT YET IMPLEMENTED.** The shape below is the agreed
> destination. It ships as the batches in §6 — each one independently shippable
> and independently revertible. Track progress in the §0 ledger.

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
| — (planning + ADRs) | 🔨 in review (PR #7) | #7 | branch `worktree-business-line-reorg` · 2026-09-10 | plan, ADR 0011/0012 (Accepted), scaffolding (ledger, gates, AI-guide pointers, memory) |
| B1 — provider seam extraction | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | delivers the "pluggable API" seam on its own. Actual shape / deviations recorded in §8; `_ALLOWED_DEPS` promotion of `providers` deferred to B3 |
| B2 — canonical raw store | ✅ landed | — | branch `worktree-business-line-reorg` · 2026-09-10 | gate §8 Q4 resolved (name-only rename). Actuals in §8; `symbol` column deferred (ADR 0011 amendment) |
| B3 — package re-home | ⬜ not started | — | — | resets `arch_baseline.json` |
| B4 — close L1 (`core-purity`) | ⬜ not started | — | — | — |
| B5 — readiness plan + prefetch | ⬜ not started | — | — | gate: §8 Q1 |
| B6 — `ticker`-only Parameters bar | ⬜ not started | — | — | gate: §8 Q3; depends on B5 |
| B7 — module-scoped params | ⬜ not started | — | — | gate: §8 Q1; depends on B6 |
| B8 — retire / repurpose Config tab | ⬜ not started | — | — | gate: §8 Q2 |

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
| Q1 | **Submit contract** — does `POST /` carry a `modules` manifest with per-module params attached to each `/render` call, or do the streaming market tabs move fully to client-fired `/api/*` like Option Chain? Manifest keeps the streaming model; full client-fired is more uniform but a bigger diff. | before **B5** (locks how B7 wires params) | manifest |
| Q2 | **Config tab fate** — is there *any* genuine global setting to keep? Risk-free rate is the only candidate (hard-coded in `static/sim/` and again in `core/options/greeks`). Yes → tab shrinks to it; no → tab deleted. | before **B8** | keep risk-free rate, delete the rest |
| Q3 | **`positions` block** — Portfolio Analysis is its only consumer. Move into a dedicated "Portfolio" panel/tab, or keep as a section the bar's Run ignores? | before **B6** | dedicated Portfolio panel |
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
  (idempotent, `INSERT OR IGNORE`, never clobbers the canonical table).
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

---

## 9. References

- Current flow: `routes/core.py` → `services/market/dispatch.py` → `services/market/analysis/facade.py`
- Data layer: `data_pipeline/data_ops/{facade,_range,_query}.py`, `yf_client.py`, `downloader.py`, `db.py`, `repos.py`
- Frontend: `templates/partials/tab_parameter.html`, `tab_config.html`, `static/main.js`, `static/option-chain.js`
- `docs/decisions/0002-yfinance-as-sole-data-source.md`, `0004-no-iv-history-from-yfinance.md`, `0005-token-bucket-throttle.md`
- `docs/constraints.md` §1–§6, `docs/frontend_architecture.md`, `docs/frontend_convergence.md`
- `archive/futu_integration/field_mapping.md`

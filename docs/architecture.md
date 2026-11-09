# Architecture — Layers, Request Flow, Data Stages

> L1 | 权威：运行时分层、依赖方向、streaming 请求流、data_pipeline 六阶段、代码入口速查 | 不权威：逐模块职责清单（见 `docs/module_reference.md`）、进度（见 `STATUS.md`）、决策理由（见 `docs/decisions/`）

OptionLab is a single-process Flask dashboard for equity/options research. It pulls prices and
option chains from **yfinance only**, caches them in **SQLite (WAL)**, and serves a **streaming
HTMX + vanilla-JS** UI where nearly all charts are server-side matplotlib PNGs.

The standing architecture record (scorecard + debt registry) lives in
`docs/architecture_review.md`; the top-level directory skeleton is `docs/l0_architecture.md`.

## Layered dependency flow (one-way, enforced by `doc_guard.py` `import-direction`)

```
app.py → routes/ → services/ → core/ → data_pipeline/ → utils/
```

- **`routes/`** — seven Flask blueprints, no business logic: parse request args and delegate.
- **`services/`** — orchestration. Flask-aware (may raise `ApiError`, read `request`) but does no
  heavy computation. **Packaged by business domain** (`market/`, `options/`, `portfolio/`,
  `regime/`), each exposing a `facade.py` entry point. Cross-domain imports inside `services/`
  are legal; only the *layer* direction is policed.
- **`core/`** — pure computation: no Flask, no DB, no network. Data in → numbers/DataFrames out.
  `core/` and `data_pipeline/` must never import `services/`, `routes/`, or `app.py`;
  `data_pipeline/` must never import `core/`. **`core/` must not import `data_pipeline/` either**
  (closed in batch B4 — enforced by `doc_guard` `import-direction` and
  `tests/test_architecture_purity.py`; acquisition belongs in `services/`).
- **`data_pipeline/`** — owns **every** I/O boundary: yfinance, SQLite, the scheduler.
- **`utils/`** — leaf helpers only.

A new analytical feature is normally: pure function under `core/…` → thin orchestrator in
`services/…` → route. Never put pandas/numpy work in a route.

Same-named modules recur across packages by design (`facade.py`, `models.py`, `greeks.py`, …).
Always reference and import them package-qualified (`from core.options.greeks import …`, never bare `greeks.py`).

## The streaming / lazy-tab model (the key non-obvious flow)

`POST /` computes **nothing**. `routes/core.py::index` normalises the form
(`FormService.extract_form_data` → `ValidationService.validate_input_data`), resolves the requested
modules (`FormService.extract_modules`), runs the **data-readiness pass**
(`services/market/readiness.py` → `data_pipeline/orchestrate/readiness.py`: plan the datasets the
modules need, probe the DB once, kick missing ranges on daemon threads, warm the live option-chain
preload), registers a job via `data_pipeline/orchestrate/job_cache.py::create_job` (TTL default 90 s,
carrying the readiness plan), and renders `templates/index.html` with `streaming_mode=True`. Each tab
shell emits an HTMX placeholder (`hx-get="/render/<kind>?job=…&ticker=…" hx-trigger="load"`), and the
browser fans out parallel requests.

All `/render/<kind>` routes funnel into **`services/market/dispatch.py::render_streaming_slice`**, which:
1. auto-bootstraps a synthetic job with defaults when `job` is missing (direct URL / refresh / bookmark) instead of erroring;
2. consults the job's readiness plan and, on a **cold start** (no usable history yet *and* the backfill still running), returns `partials/fragments/readiness.html` — a self-re-firing "正在准备…" fragment — instead of an empty chart (bounded by `readiness.HOLD_SECONDS` and by thread liveness);
3. dispatches via `_RENDER_KIND_SLICES` (kind → `(AnalysisService method name as a string, fragment template)`), late-bound with `getattr` so test monkey-patches are honoured;
4. memoises per `(job_id, ticker, kind)` through `compute_or_get`;
5. calls `close_thread_conn()` in `finally` to avoid leaking the thread-local SQLite connection.

Failures return `render_error_fragment` — usually **HTTP 200 on purpose** (expired job) so HTMX
swaps a helpful message rather than a browser error toast.

**Adding a tab:** a row in `_RENDER_KIND_SLICES`, a `generate_*_slice` staticmethod on
`services.market.analysis.AnalysisService`, a fragment template under
`templates/partials/fragments/`, and a placeholder in `index.html` — **no new route body**.

`AnalysisService` slice methods follow a "swallow, log, return an `{"error": …}` dict" pattern so
one bad tab never 500s the page. `services/market/analysis/statistical.py` adds a second
chart-level memo keyed by `(ticker, chart name, params)` because PNG encoding is the expensive part.

## `data_pipeline/` specifics

Re-homed in batch B3 of ADR 0011 into six one-way stages; the authoritative layer table is
`docs/architecture_review.md` §3 and is enforced by `doc_guard` + `tests/test_architecture_purity.py`
(the per-directory skeleton is in `docs/l0_architecture.md` §3):

- **`read/` — `DataService` (facade)** is the single read entry point above the package.
  `ensure_range(ticker, start, end)` is DB-first with a memo + in-flight de-duplication + TTL, which
  stops concurrent UI requests from stampeding Yahoo. The facade and `read/_query.py` call the
  `orchestrate` drivers directly (never each other's facade) — `read → orchestrate` is why
  `orchestrate` must not import `read` (no cycle).
- **`providers/`** is the **only** package allowed to call yfinance (the chokepoint moved here from
  `yf_client.py` in batch B1; enforced by `doc_guard` `single-yf-exit`, exceptions registered in
  `docs/architecture_review.md` §2). It owns the mapping from the vendor's fields onto one canonical
  schema (`providers/base.py`) — IV as a decimal, nullable bid/ask, no `inTheMoney`. Every call goes
  through `yf_throttle()` (token bucket, 5 req/s, burst 5). `providers/yf_client.py` is a one-release
  compatibility shim over the package; `_registry.py` is the `MARKET_DATA_PROVIDER` seam.
  **Never** pass `session=requests.Session()` — yfinance ≥0.2.50 uses curl_cffi and silently fails
  (ADR 0005).
- **`store/`** — `db.py` (`init_db()` uses `CREATE TABLE IF NOT EXISTS`; no migration framework),
  `repos.py` (the only place that builds SQL) and `quality_log.py`. Tables are named canonically
  (`raw_bars` / `clean_bars` / `feature_bars`); the pre-rename names (`raw_prices` / `clean_prices` /
  `processed_prices`) are kept as shadows for one release — every `upsert_many` writes both families,
  and `scripts/migrate_canonical_tables.py` backfills an existing DB. `get_conn()` yields a
  **thread-local** WAL connection (`synchronous=NORMAL`, `busy_timeout=5000`) and does **not** close
  on exit.
- **`ingest/ohlcv.py`** — business-day gap detection + `raw_bars` upsert; acquisition goes through
  `providers.get_provider().history()`, so this module never names a vendor.
- **`transform/cleaning.py` / `transform/processing.py`** — align to business days, mark gaps NA with
  **no interpolation** (invented prices are worse than missing ones), then engineer returns/MAs/HV.
  Never imports `providers/` (asserted by a test).
- **`orchestrate/`** — `update.py` (incremental/full drivers), `backfill.py` (chunked coverage
  repair), `job_cache.py` (streaming slice memo), `scheduler.py` (optional APScheduler).
- **`_state.py`** — process-local query cache + update locks, shared by `read` and `orchestrate`.
- No option-chain history exists from yfinance — no IV rank/percentile/backtests; HV percentile is
  the deliberate substitute (ADR 0004).

## Frontend

`static/api.js` is the **only** `fetch` wrapper (owns aborting + `ApiError` normalisation) —
components must not call `fetch` directly. `static/state/` holds tiny observable stores:
`marketParamsState.js` / `assessmentParamsState.js` / `optionFilterState.js` own the module-scoped
parameters (one `localStorage` key per group) and re-run exactly the modules that consume a change;
`panelState.js` enforces the four-phase async contract (`idle → loading → loaded → empty|error`,
no sixth state), `tabFlagsState.js` is the lazy-load guard (a ticker change resets the tabs that
depend on the ticker), and a superseded request is aborted per panel key (`api.js` `key`;
`abortRegistry.js` for raw `fetch`) — the ticker switch itself aborts nothing. Charts are server PNGs
except `static/market_review_chart.js`, `static/components/payoff_chart.js` and `static/optsim.js`
(JSON → Chart.js). The **Simulation** and **Option Pricing Matrix** tabs are pure client-side
(`static/sim/`, zero I/O) and also run standalone on GitHub Pages; the **Position Simulator** tab posts
a position to `POST /api/optsim` (`core/optsim`, ADR 0013) — priced on hypothetical inputs, or in
ticker mode on the header ticker's option chain — so on Pages it only shows a demo notice. Frontend deps are CDN-only —
**no build step**, no React/Vue (ADR 0006). UI changes must
satisfy the P1–P5 contract in `docs/frontend_architecture.md`.

The GitHub Pages mirror (`site/`) reuses `templates/` and `static/` verbatim; only
`site/pages-shim.js` + committed fixtures under `site/fixtures/` and `site/snapshot/` are
Pages-only. Rendered `site/index.html` / `site/static/` are build artefacts — regenerate with
`python scripts/build_pages_site.py`.

## Where to look first

| Question | File |
|---|---|
| How does a request get served? | `routes/core.py` → `services/market/dispatch.py` |
| Where does data come from? | `data_pipeline/read/facade.py`, `orchestrate/backfill.py`, `providers/` |
| Schema / SQL | `data_pipeline/store/db.py` (`init_db`), `store/repos.py` |
| Chart / analysis maths | `core/market/analyzer.py`, `core/options/`, `core/strategies/` |
| Option position simulator (optsim): what exists, what's next? | `docs/plans/optsim.md` → `core/optsim/` |
| Frontend contract | `docs/frontend_architecture.md` |
| Why is this weird? | `docs/constraints.md`, then `docs/decisions/` |

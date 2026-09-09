# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Source of truth for architecture** lives in `docs/`, not here:
> `docs/architecture_review.md` (scorecard + debt registry), `docs/l0_architecture.md`
> (top-level skeleton), `docs/constraints.md` (read before calling anything tech debt),
> `docs/decisions/` (ADRs), `docs/frontend_architecture.md` (UI contract).
> Update `docs/` first, then mirror the summary here. `CODEBUDDY.md` and
> `.github/copilot-instructions.md` are parallel AI-assistant guides kept in sync with this one.

## Commands

### Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Python 3.12+
npm install                              # only for vitest JS tests
cp .env.example .env                     # set YF_PROXY, MARKET_DB_PATH, AUTO_UPDATE_TICKERS
pre-commit install
```
`ruff`, `pytest-playwright`, and `APScheduler` are deliberately **not** in `requirements.txt` —
install them only when needed (CI installs `ruff==0.16.5` in its own step; keep in sync with
`required-version` in `pyproject.toml`).

### Run
```bash
python app.py                                              # dev server, PORT defaults to 5001
gunicorn app:app -b 0.0.0.0:5001 --workers 2 --threads 4   # production
```
`app.py` is a thin adapter: wires `/api/v1/*`→`/api/*` middleware, installs the JSON error
envelope (`utils/api_errors.py::install`) and the in-house per-IP rate limiter
(`utils/rate_limit.py::install`), propagates `YF_PROXY` to curl_cffi, bootstraps the SQLite
schema, and starts APScheduler only on the worker that wins the leader lock. APScheduler is
lazily imported and only required when `AUTO_UPDATE_TICKERS` is set. Tests set `RATE_LIMIT_DISABLED=1`.

### Lint & format
```bash
ruff check .          # E,W,F,I,B,UP; line-length 120; config in pyproject.toml
ruff format --check .  # CI runs both
```

### Python tests
```bash
pytest                                            # whole suite; addopts "-x --tb=short -q" stops at first failure
pytest --maxfail=0                                # override the -x to see everything
pytest tests/test_signals.py::test_hv_window -v   # a single test
pytest -m "not network"                           # skip live-yfinance tests
pytest --ignore=tests/e2e                         # skip Playwright
```
`tests/conftest.py` is autouse: it points `MARKET_DB_PATH` at a per-test tmp file and clears
`DataService`'s process-wide query cache, so tests never touch the real `market_data.sqlite`.

### E2E (Playwright) & JS tests
```bash
pip install pytest-playwright && playwright install chromium
pytest tests/e2e/                     # headless; real Flask server in a daemon thread, /api/* mocked at the browser layer
npx vitest run                        # tests/unit/**/*.test.js (jsdom)
npx vitest run tests/unit/api.test.js
```

### Doc / architecture automation (also run by pre-commit + CI)
```bash
python scripts/doc_guard.py --files a.py b.md    # lint L1 invariants on changed files
python scripts/arch_metrics.py --check           # drift gate vs .github/data/arch_baseline.json
python scripts/regen_adr_index.py                # regenerate docs/decisions/README.md after adding an ADR
python scripts/audit_tags.py                     # comment-tag coverage regression
python scripts/seed_history.py NVDA 5            # one-shot 5-year SQLite backfill
```

## Per-task Git worktree isolation (ADR 0009)

Every dev task runs in its own worktree under `.worktrees/<task-name>/` with its own branch,
`.venv`, and `.env`; the main checkout stays on `main` and clean. **Never edit task code in the
main checkout.** Full flow: `docs/guides/GIT_WORKTREE_WORKFLOW.md`.
```bash
python scripts/worktree.py create <task-name>    # branch + worktree + venv bootstrap
python scripts/worktree.py list                  # worktrees + dirty flags
python scripts/worktree.py remove <task-name>    # guarded delete (refuses dirty/unmerged)
```
Parallel tasks: give each worktree a distinct `PORT`; don't run two schedulers against one DB.

## Architecture

OptionLab is a single-process Flask dashboard for equity/options research. It pulls prices and
option chains from **yfinance only**, caches them in **SQLite (WAL)**, and serves a **streaming
HTMX + vanilla-JS** UI where nearly all charts are server-side matplotlib PNGs.

### Layered dependency flow (one-way, enforced by `doc_guard.py` `import-direction`)

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
  `data_pipeline/` must never import `core/`.
- **`data_pipeline/`** — owns **every** I/O boundary: yfinance, SQLite, the scheduler.
- **`utils/`** — leaf helpers only.

A new analytical feature is normally: pure function under `core/…` → thin orchestrator in
`services/…` → route. Never put pandas/numpy work in a route.

Same-named modules recur across packages by design (`facade.py`, `models.py`, `greeks.py`, …).
Always reference and import them package-qualified (`from core.options.greeks import …`, never bare `greeks.py`).

### The streaming / lazy-tab model (the key non-obvious flow)

`POST /` computes **nothing**. `routes/core.py::index` normalises the form
(`FormService.extract_form_data` → `ValidationService.validate_input_data`), registers a job via
`data_pipeline/job_cache.py::create_job` (TTL default 90 s), and renders `templates/index.html`
with `streaming_mode=True`. Each tab shell emits an HTMX placeholder
(`hx-get="/render/<kind>?job=…&ticker=…" hx-trigger="load"`), and the browser fans out parallel requests.

All `/render/<kind>` routes funnel into **`services/market/dispatch.py::render_streaming_slice`**, which:
1. auto-bootstraps a synthetic job with defaults when `job` is missing (direct URL / refresh / bookmark) instead of erroring;
2. dispatches via `_RENDER_KIND_SLICES` (kind → `(AnalysisService method name as a string, fragment template)`), late-bound with `getattr` so test monkey-patches are honoured;
3. memoises per `(job_id, ticker, kind)` through `compute_or_get`;
4. calls `close_thread_conn()` in `finally` to avoid leaking the thread-local SQLite connection.

Failures return `render_error_fragment` — usually **HTTP 200 on purpose** (expired job) so HTMX
swaps a helpful message rather than a browser error toast.

**Adding a tab:** a row in `_RENDER_KIND_SLICES`, a `generate_*_slice` staticmethod on
`services.market.analysis.AnalysisService`, a fragment template under
`templates/partials/fragments/`, and a placeholder in `index.html` — **no new route body**.

`AnalysisService` slice methods follow a "swallow, log, return an `{"error": …}` dict" pattern so
one bad tab never 500s the page. `services/market/analysis/statistical.py` adds a second
chart-level memo keyed by `(ticker, chart name, params)` because PNG encoding is the expensive part.

### `data_pipeline/` specifics

- **`data_ops/` — `DataService` (facade)** is the single read entry point. `ensure_range(ticker,
  start, end)` is DB-first with a memo + in-flight de-duplication + TTL, which stops concurrent UI
  requests from stampeding Yahoo. `_query.py` calls `_update`/`_range` module functions directly
  (never the facade) to avoid an import cycle.
- **`yf_client.py`** is the **only** module allowed to call yfinance (enforced by `doc_guard`
  `single-yf-exit`; exceptions registered in `docs/architecture_review.md` §2). Every call goes
  through `yf_throttle()` (token bucket, 5 req/s, burst 5). **Never** pass
  `session=requests.Session()` — yfinance ≥0.2.50 uses curl_cffi and silently fails (ADR 0005).
- **`db.py`** — `init_db()` uses `CREATE TABLE IF NOT EXISTS` (no migration framework).
  `get_conn()` yields a **thread-local** WAL connection (`synchronous=NORMAL`,
  `busy_timeout=5000`) and does **not** close on exit. `repos.py` is the only place that builds SQL.
- **`cleaning.py` / `processing.py`** — align to business days, mark gaps NA with **no
  interpolation** (invented prices are worse than missing ones), then engineer returns/MAs/HV.
- No option-chain history exists from yfinance — no IV rank/percentile/backtests; HV percentile is
  the deliberate substitute (ADR 0004).

### Frontend

`static/api.js` is the **only** `fetch` wrapper (owns aborting + `ApiError` normalisation) —
components must not call `fetch` directly. `static/state/` holds tiny observable stores:
`panelState.js` enforces the four-phase async contract (`idle → loading → loaded → empty|error`,
no sixth state), `tabFlagsState.js` is the lazy-load guard, `abortRegistry.js` cancels in-flight
requests on ticker switch. Charts are server PNGs except `static/market_review_chart.js` and
`static/components/payoff_chart.js` (JSON → Chart.js). The **Simulation** and **Option Pricing
Matrix** tabs are pure client-side (`static/sim/`, zero I/O) and also run standalone on GitHub
Pages. Frontend deps are CDN-only — **no build step**, no React/Vue (ADR 0006). UI changes must
satisfy the P1–P5 contract in `docs/frontend_architecture.md`.

The GitHub Pages mirror (`site/`) reuses `templates/` and `static/` verbatim; only
`site/pages-shim.js` + committed fixtures under `site/fixtures/` and `site/snapshot/` are
Pages-only. Rendered `site/index.html` / `site/static/` are build artefacts — regenerate with
`python scripts/build_pages_site.py`.

## Conventions you must respect

- **Comment tags mark already-reviewed code.** `WHY:`, `CONSTRAINT:`, `TRADEOFF:`, `INVARIANT:`,
  `DOMAIN:`, `HACK:`/`WORKAROUND:` — do **not** propose refactors on tagged code unless asked.
  `doc_guard.py` `tag-syntax` keeps the vocabulary canonical.
- **"Magic numbers" in `core/` are domain constants** (MA 10/20/50/200, RSI 14, BB 20, HV 30,
  sigma bounds for Greeks). Read `docs/constraints.md` §5 and `docs/glossary.md` before touching them.
- **Every new module under `core/`, `data_pipeline/`, `services/`, `utils/` needs a top-level
  docstring** (`doc_guard.py` `module-docstring`), in the `Domain: / Context: / Contracts: /
  Dependencies:` shape.
- **Language**: code, comments, logs, identifiers in English; UI strings may be Chinese — do not
  "translate" template Chinese.
- Use `logging.getLogger(__name__)`, never `print()`. Type-hint public signatures.
- Tests use behavioural names (`test_<subject>_<expected_behaviour>`), not bare symbol names.
- **After any code change, update docs in the same response**: new constant → add a tag; new
  external constraint → `docs/constraints.md`; new module boundary/tech → an ADR from
  `docs/decisions/TEMPLATE.md` **and** run `scripts/regen_adr_index.py`; new user-visible term →
  `docs/glossary.md`; new layer exemption → `docs/architecture_review.md` §2. Then self-check
  against `doc_guard.py` and run `python scripts/arch_metrics.py --check`.

## Where to look first

| Question | File |
|---|---|
| How does a request get served? | `routes/core.py` → `services/market/dispatch.py` |
| Where does data come from? | `data_pipeline/data_ops/facade.py`, `_range.py`, `yf_client.py` |
| Schema / SQL | `data_pipeline/db.py` (`init_db`), `repos.py` |
| Chart / analysis maths | `core/market/analyzer.py`, `core/options/`, `core/strategies/` |
| Frontend contract | `docs/frontend_architecture.md` |
| Why is this weird? | `docs/constraints.md`, then `docs/decisions/` |

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

## Commands

### Environment setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # Python 3.12+ required
npm install                         # only for vitest JS tests
cp .env.example .env                # set YF_PROXY, MARKET_DB_PATH, AUTO_UPDATE_TICKERS
pre-commit install --hook-type pre-commit
```
E2E deps are deliberately **not** in `requirements.txt`; install `pytest-playwright` + `playwright install chromium` only when needed.

### Run the app
```bash
python app.py                                              # dev server; PORT defaults to 5001
gunicorn app:app -b 0.0.0.0:5001 --workers 2 --threads 4   # production
```
`app.py` boots the DB schema, propagates `YF_PROXY` to curl_cffi, installs the error envelope and rate limiter, and starts APScheduler only on the worker that wins the leader lock. Set `RATE_LIMIT_DISABLED=1` to disable throttling (tests do).

### Lint & format
```bash
ruff check .          # E,W,F,I,B,UP rules; line-length 120; config in pyproject.toml
ruff format --check . # CI runs both; E501 is ignored in favour of the formatter
ruff format .         # autofix
```
`ruff` is not in `requirements.txt` — CI installs it in a separate step.

### Python tests
```bash
pytest                              # whole suite; addopts are "-x --tb=short -q" → stops at first failure
pytest --maxfail=0                  # override the -x in addopts when you want the full picture
pytest tests/test_signals.py -v     # one file
pytest tests/test_signals.py::test_hv_window -v   # one test
pytest --ignore=tests/e2e           # skip Playwright
pytest -m "not network"             # skip live-yfinance tests (see tests/test_chart_time_range.py)
```
`tests/conftest.py` is autouse: it redirects `MARKET_DB_PATH` to a per-test tmp file and clears `DataService`'s process-wide query cache, so tests never touch `market_data.sqlite`.

### E2E (Playwright)
```bash
pip install pytest-playwright && playwright install chromium
pytest tests/e2e/                    # headless
pytest tests/e2e/test_smoke.py --headed --slowmo 500
pytest tests/e2e/ --tracing retain-on-failure
```
`tests/e2e/conftest.py` runs a real Flask server in a daemon thread and mocks `/api/*` at the **browser** layer (`page.route`), so no network is used.

### JS tests
```bash
npx vitest run                       # tests/unit/**/*.test.js, jsdom
npx vitest run tests/unit/api.test.js
npx vitest --watch
```
Config in `vitest.config.js`; setup file `tests/unit/setup.js`.

### Doc-automation scripts
```bash
python scripts/doc_guard.py                      # all L1 invariants (exit non-zero on violation)
python scripts/doc_guard.py --files a.py b.md    # only changed files (what pre-commit/CI do)
python scripts/doc_guard.py --rule import-direction --json
python scripts/regen_adr_index.py                # regenerate docs/decisions/README.md, then commit
python scripts/audit_tags.py                     # tag-coverage regression vs .github/data/tag_baseline.json
python scripts/audit_tags.py --update-baseline   # accept new uncovered constants
python scripts/seed_history.py NVDA 5            # one-shot 5-year backfill into SQLite
python scripts/perf_regression.py -v --tickers NVDA,AAPL --target 8.0
python scripts/find_drift_candidates.py          # feeds scripts/draft_doc_updates.py (L2 AI drafts)
```

---

## Architecture

OptionLab is a single-process Flask dashboard for equity/options research. It pulls prices and option chains from **yfinance only**, caches them in **SQLite (WAL)**, and serves a **streaming HTMX + vanilla-JS** UI where nearly all charts are server-side matplotlib PNGs.

### Layered dependency flow (one-way, enforced)

```
app.py → routes/ → services/ → core/ → data_pipeline/ → utils/
```

- `app.py` is a **thin adapter**: it only wires middleware (`/api/v1/*` → `/api/*` path rewrite), installs the JSON error envelope (`utils/api_errors.py::install`), mounts `flask-limiter`, and registers the seven blueprints exported from `routes/__init__.py`.
- `routes/` are blueprints with **no business logic** — they parse request args and delegate.
- `services/` **orchestrates**: it is Flask-aware (can raise `ApiError`, read `request`) but performs no heavy computation.
- `core/` is **pure computation**: no Flask, no DB, no network. Data in → numbers/DataFrames out.
- `data_pipeline/` owns **every** I/O boundary: yfinance calls, SQLite, the scheduler.
- Import direction is a hard invariant. `core/` and `data_pipeline/` must never import `services/`, `routes/`, or `app.py`; `data_pipeline/` must never import `core/`. Enforced by `doc_guard.py`'s `import-direction` rule.

Because `core/` is pure, a new analytical feature is normally: add a pure function under `core/…`, add a thin orchestrator in `services/…`, expose a route. Never put pandas/numpy work in a route.

### The streaming / lazy-tab model (the most important non-obvious flow)

`POST /` does **not** compute anything. `routes/core.py::index` normalises the form (`FormService.extract_form_data` → `ValidationService.validate_input_data`), registers a job via `data_pipeline/job_cache.py::create_job`, and immediately renders `templates/index.html` with `streaming_mode=True`.

Each tab shell in the skeleton emits an HTMX placeholder (`hx-get="/render/<kind>?job=…&ticker=…" hx-trigger="load" hx-swap="outerHTML"`). The browser then fans out four parallel requests.

All four `/render/<kind>` routes funnel into **`utils/render_helpers.py::render_streaming_slice`**. It:
1. reads `job`/`ticker` from the query string;
2. **auto-bootstraps a synthetic job** with defaults when `job` is missing (direct URL / refresh / bookmark) instead of erroring;
3. dispatches via the `_RENDER_KIND_SLICES` table, which maps kind → `(AnalysisService method name, fragment template)`. Attribute names are stored as *strings* and late-bound with `getattr` so test monkey-patches are honoured. `options_chain` is special-cased to call `OptionsChainService.generate_options_chain_analysis` directly (it needs no `MarketAnalyzer`);
4. memoises the result per `(job_id, ticker, kind)` through `compute_or_get`, so a re-render is free;
5. calls `close_thread_conn()` in a `finally` to avoid leaking the thread-local SQLite connection;
6. merges `{**form_data, "ticker": …, **slice_result}` and renders `templates/partials/fragments/<kind>.html`.

Failures return `render_error_fragment`, which is usually **HTTP 200** on purpose (expired job) so HTMX swaps a helpful message rather than showing a browser error toast.

Consequence for contributors: a new tab needs a row in `_RENDER_KIND_SLICES`, a `generate_*_slice` staticmethod on `services/market_analysis.AnalysisService`, a fragment template, and a placeholder in `index.html` — but **no new route body**.

### `services/market_analysis/` — the slice factory

`AnalysisService` (`_service.py`) is the facade. `_build_analyzer_or_error` constructs a `core.market.analyzer.MarketAnalyzer` from form data and returns an `{"error": …}` dict instead of raising when data is unusable — every slice method follows the same "swallow, log, return an error dict" pattern so one bad tab never 500s the page. `generate_market_review_slice` delegates to `MarketService.generate_market_review`; `generate_statistical_slice` / `generate_assessment_slice` call the private builders in `_statistical.py` / `_assessment.py` inside a `try/finally: gc.collect()`. `_summary.py::generate_summary_analysis` does multi-ticker aggregation and `_sizing.py::calculate_position_size` does risk sizing.

`_statistical.py` wraps chart builders in `_cached_or_build(key, builder)` — a second, chart-level memo keyed by `(ticker, chart name, params)` on top of the job cache, because PNG encoding is the expensive part.

### `core/` — computation

- **`core/market/`** — `analyzer.py::MarketAnalyzer` is the workhorse: `generate_scatter_plots`, `generate_volatility_dynamics`, `generate_oscillation_projection`, `analyze_options`. It returns **base64 PNG strings plus feature series**, and `models.py` defines `MarketFeatures`, `Band`, `ProjectionResult` dataclasses. `data_context.py::DataContext` / `build_data_context()` is the read path: DB-first, yfinance fallback, then resample to D/W/M. `price_dynamic.py` is a backward-compat shim over it. `features/` (returns, osc, volatility) and `projections/oscillation.py` hold the primitives; `charts/` holds one matplotlib renderer per chart.
- **`core/options/`** — `chain/analyzer.py::OptionsChainAnalyzer` derives IV smile/skew, OI profile, expected move from a *snapshot* chain; `chain/filters.py` does DTE/moneyness filtering; `chain/{metrics,term_structure,liquidity,html_tables}.py` add max-pain, ATM IV term structure, and pre-rendered HTML tables. `greeks/black_scholes.py::greeks_vectorized` is numpy-vectorised over whole chains (scipy per-contract is ~30× slower, see `docs/constraints.md` §6). `greeks/portfolio.py` aggregates portfolio Greeks and theta-decay paths. `simulation/expiry.py` holds `parse_expiries` + `simulate_expiry` — pure expiry-payoff maths, driven by `services/options_simulation_service.py::run_simulation` (which validates input and bounds the strike × expiry × IV grid).
- **`core/strategies/`** — `models.py::Leg` is the universal unit. `factories.py` builds multi-leg templates (spreads, straddles, iron condor, butterfly, calendar…); `payoff.py`, `greeks.py`, `prob_profit.py`, `analyze.py` aggregate them. `services/strategy_builder.py` picks *real* strikes off the live chain to instantiate a template.
- **`core/{signals,regime,market_review,portfolio,decision}/`** — pure OHLCV signals (HV/RSI/Bollinger), regime classification, cross-ticker summary tables, P&L attribution, and the put-selling candidate scorer.

### `data_pipeline/` — I/O, caching, persistence

- **`data_pipeline/data_ops/` — `DataService` (facade)** — `DataService` in `_service.py` delegates to `_query.py`, `_range.py`, `_update.py`, `_globals.py`. This is the **single read entry point** for the rest of the app. `ensure_range(ticker, start, end)` is DB-first with a memo + in-flight de-duplication and a TTL, which is what stops concurrent UI requests from stampeding Yahoo. `get_cleaned_daily`, `get_processed`, `get_latest_spot` are the common reads.
- **`yf_client.py`** is the **only** module allowed to call yfinance. Every call goes through `yf_throttle()` (token bucket, 5 req/s, burst 5). Never call `yf.download` elsewhere, and never pass `session=requests.Session()` — yfinance ≥0.2.50 uses curl_cffi and silently fails (ADR 0005, `docs/constraints.md` §2).
- **`db.py`** — `init_db()` creates the schema with `CREATE TABLE IF NOT EXISTS` (no migration framework). `get_conn()` is a context manager yielding a **thread-local** connection with WAL + `synchronous=NORMAL` + `busy_timeout=5000` applied once per thread; it does **not** close on exit. Tables: `raw_prices`, `clean_prices`, `processed_prices`, `market_review_prices`, `regime_log`, `data_quality_log`, `tracked_strategies`.
- **`repos.py`** is the only place that builds SQL. Go through it rather than hand-writing queries.
- **`cleaning.py` / `processing.py`** — align to business days and mark gaps as NA with **no interpolation** (the machine isn't 24/7; invented prices are worse than missing ones), then engineer returns/MAs/HV.
- **`scheduler.py`** — APScheduler daily backfill + monthly correlation refresh, gated by a leader-lock file so only one gunicorn worker schedules. **`job_cache.py`** — TTL'd (default 90 s) in-process job store backing `/render/*`. **`quality_log.py`** — persists fetch anomalies surfaced by `/health/data`.

### Frontend

`templates/index.html` is the skeleton; `templates/partials/fragments/*.html` are the HTMX-swapped fragments. `static/main.js` bootstraps form + tab management; `static/api.js` is the **only** `fetch` wrapper (owns aborting and error normalisation — components must not call `fetch` directly). `static/state/` holds the tiny observable stores: `panelState.js` implements the mandatory four-phase contract (`idle → loading → loaded → empty|error`), `tabFlagsState.js` is the lazy-load guard, `abortRegistry.js` cancels in-flight requests on ticker switch (this is what `tests/e2e/test_tab_race.py` protects). `static/eventBus.js` is cross-component pub/sub; `static/cache.js` is a versioned `localStorage` wrapper. Charts are server PNGs except `static/market_review_chart.js` and `static/components/payoff_chart.js`, which stream JSON to Chart.js. Frontend deps are CDN-only (Chart.js 4, Alpine, Font Awesome) — there is **no build step** and no React/Vue (ADR 0006).

UI changes must satisfy the P1–P5 contract in `docs/frontend_architecture.md` (hero metric at 24–32px/700, four-phase async states, locked semantic colour tokens, one button spec, WCAG AA/axe ≥95).

### Conventions you must respect

- **Comment tags mark justified code.** `WHY:`, `CONSTRAINT:`, `TRADEOFF:`, `INVARIANT:`, `DOMAIN:`, `HACK:`/`WORKAROUND:` — treat tagged code as already-reviewed and do **not** propose refactors unless asked. `doc_guard.py`'s `tag-syntax` rule keeps the vocabulary canonical.
- **"Magic numbers" in `core/` are domain constants** (MA 10/20/50/200, RSI 14, BB 20, HV 30, sigma bounds for Greeks). Read `docs/constraints.md` §5 and `docs/glossary.md` before "cleaning them up".
- **No option-chain history exists** from yfinance — no IV rank/percentile/backtests. HV percentile is the deliberate substitute (ADR 0004).
- **Every new module under `core/`, `data_pipeline/`, or `services/` needs a top-level docstring** (`doc_guard.py` `module-docstring`), preferably in the `Domain: / Context: / Contracts: / Dependencies:` shape used by e.g. `utils/render_helpers.py`.
- **Language**: code, comments, logs, identifiers in English; UI strings may be Chinese — do not "translate" template Chinese.
- Use `logging.getLogger(__name__)`, never `print()`; type-hint public signatures.
- **After any code change, update the docs in the same response**: new non-obvious constant → add a tag; new constraint → `docs/constraints.md`; new module boundary/tech → an ADR from `docs/decisions/TEMPLATE.md` **and** run `scripts/regen_adr_index.py`; new user-visible term → `docs/glossary.md`. Then self-check against `doc_guard.py`'s rules (`tag-syntax`, `yfinance-throttle`, `yfinance-session-kwarg`, `sqlite-bypass`, `import-direction`, `module-docstring`, `adr-link-integrity`, `adr-index-fresh`).
- Tests use behavioural names (`test_<subject>_<expected_behaviour>`), not bare symbol names.

### Where to look first

| Question | File |
|---|---|
| How does a request get served? | `routes/core.py` → `utils/render_helpers.py` |
| Where does data come from? | `data_pipeline/data_ops/_service.py`, `_range.py`, `yf_client.py` |
| Schema / SQL | `data_pipeline/db.py` (`init_db`), `repos.py` |
| Chart/analysis maths | `core/market/analyzer.py`, `core/options/`, `core/strategies/` |
| Frontend contract | `docs/frontend_architecture.md` |
| Why is this weird? | `docs/constraints.md`, then `docs/decisions/` |

---

## Module-by-module navigation

Use the high-level map above for orientation; this section is the per-module "where do I actually put code" companion.

### Frontend state machine — `static/state/`

Load order is fixed in `templates/index.html`: `eventBus.js → api.js → state/store.js → state/* → features`. `state/store.js` bootstraps a single `window.appState` namespace and throws if the event bus isn't present. Every other state module attaches itself to `appState` and emits `state:<key>` events on `static/eventBus.js`.

- **`panelState.js`** — the mandatory async contract. `appState.panels.set(id, phase, {message, data})` (also `.get(id)`) emits `panel:<id>`; valid phases are `idle | loading | loaded | error | empty` (no sixth state). `window.panelState(id, initialPhase)` is the Alpine `x-data` factory that subscribes to that event — feature scripts drive the DOM by calling `set(...)` without touching elements. All async panels (option chain, regime, market-review chart) must go through this.
- **`tabFlagsState.js`** — `appState.tabFlags.isLoaded/markLoaded/reset/resetAll(tab)`. Known tabs: `market_review`, `option_chain`, `odds`, `regime`. The lazy-load guard that stops a tab from re-firing `/render/<kind>` once its fragment is in the DOM; `reset(tab)` runs on ticker switch.
- **`abortRegistry.js`** — `appState.aborts.begin(key) → AbortSignal`, `.abort(key)`, `.abortAll()`. Keyed `AbortController` for **raw `fetch()`** call sites not yet migrated to `api.js`.
- **`optionChainState.js`** — `appState.optionChain.getData/setData/getActiveExp/setActiveExp/beginRequest/abort/reset`. Emits `option_chain:loaded|cleared|exp_changed`. `chainCacheState.js` / `oddsChainState.js` follow the same accessor+event pattern.
- **`api.js`** — the **only** sanctioned `fetch` wrapper. `api.get/post/put/delete/request(url, {body, key, signal, timeoutMs, parse})`; all errors throw a normalised `ApiError {ok, status, code, message, detail}`, and `AbortError` is preserved so callers can tell user-cancel from failure. Per-key abort via `api.abort(key)`. Components must not call `fetch` directly. Per-tab logic lives in `main.js`, `option-chain.js`, `position.js`, `market_review.js`, `regime.js`.

### `core/options/chain/` — option-chain analytics

- **`analyzer.py`** — `OptionsChainAnalyzer(ticker, snapshot=None)`; pass a pre-fetched snapshot (preferred) to avoid a network call. Public: `get_snapshot_summary()`, `plot_iv_smile(expiry)`, `plot_iv_term_structure()`, `plot_iv_surface()`, `plot_skew_analysis(expiry)`, `plot_oi_volume_profile(expiry)`, `plot_pcr_summary()`, `get_expected_move_table()`, `get_key_metrics_table()` — all return base64 PNG `str|None` / HTML `str|None`. Module fn `get_odds_with_vol_context(spot, target_pct, chain, expiries) → dict`.
- **`filters.py`** — `filter_option_chain(result, max_dte=60, moneyness_low=0.7, moneyness_high=1.3, max_contracts=1000)` applies the DTE filter, then moneyness filter, then **iteratively narrows** the moneyness band by ±0.05 if contract count exceeds `max_contracts`. Plus `filter_by_moneyness`, `_filter_expirations_by_dte`.
- **`metrics.py`** — `max_pain(calls, puts)`, `expected_move(calls, puts, spot)` (ATM straddle proxy), `skew_25d(puts, calls, spot)`.
- **`term_structure.py`** — `atm_iv_for_expiry(puts, spot)` (in **%**), `iv_rank(term_structure)`, `iv_percentile(term_structure)`, `calc_implied_realized_vol(move_pct, dte)`.
- **`liquidity.py`** — `liquidity_score(strike, bid, ask, last, oi, volume, spot) → (label, reason)` classifying `GOOD|FAIR|AVOID`.
- **`html_tables.py`** — `expected_move_table(chain, expiries, spot)`, `key_metrics_table(...)` → HTML strings.

### `core/options/greeks/`

- **`black_scholes.py`** — `greeks_vectorized(S, K, T, r, sigma, option_type="call")` operates on NumPy arrays (whole-chain, vectorised); `_safe_inputs(S, K, T, sigma)` clamps to the `_SIGMA_MIN/_SIGMA_MAX`/`_T_MIN` bounds from `docs/constraints.md` §5.
- **`portfolio.py`** — `portfolio_greeks_table(positions, spot, r=0.05)`, `theta_decay_path(positions, spot, r=0.05)` → tuples.

### `core/options/simulation/` — expiry-payoff simulator (ADR 0008)

Pure, network-free single-option payoff sweep across strike × maturity × IV. Reuses `greeks_vectorized` for entry premium/delta, so it doubles as the golden oracle for the client-side JS port (see `docs/plans/simulation_tab.md`, ADR 0007).

- **`expiry.py`** — `parse_expiries(values, today=None) → list[{"dte","date","label"}]` normalises DTE integers / ISO dates (drops past/out-of-range). `simulate_expiry(spot, strikes, expiries, ivs, option_type, side, r, qty, multiplier, n_points, range_pct) → dict` returns `{spot, prices, strikes, combos, results}` where `results[i].cells` is parallel to `combos`; each cell carries `premium`, `delta`, `breakeven`, `pop`, `max_profit/max_loss` (unbounded → `None` + `unbounded_*` flags). Clamps via `_MIN_DTE=1`, `_MAX_DTE=3650`, `_MIN_IV=0.001`, `_MAX_IV=5.0`. Served by `POST /api/simulate_expiry` → `services/options_simulation_service.run_simulation` (which validates the grid caps before calling in).

### `core/strategies/`

- **`models.py`** — `Leg` dataclass (strike, premium, qty, option_type, side, expiry, …) is the universal unit.
- **`factories.py`** — `long_call/long_put/short_call/short_put`, `bull_call_spread`, `bear_put_spread`, `bear_call_spread`, `bull_put_spread`, `long_straddle/strangle`, `short_straddle/strangle`, `iron_condor`, `long_butterfly`, `calendar_spread` → `list[Leg]`.
- **`payoff.py`** — `payoff_at_expiration(legs, prices)`, `net_premium(legs)`, `find_breakevens(prices, pnl)`. **`greeks.py`** — `net_greeks(legs, spot, r=0.05)`. **`prob_profit.py`** — `prob_profit(prices, pnl, spot, sigma, dte, r=0.05)`. **`analyze.py`** — `analyze_strategy(...)`.

### `services/options_*` — option orchestration

- **`options_chain_service.py`** — `OptionsChainService.fetch_records(ticker)` returns JSON rows (each with a `liq_score`/`liq_reason` from `liquidity_score`); `fetch_records_filtered(...)` runs `filter_option_chain`; `generate_options_chain_analysis(ticker)` returns a dict of `oc_*` keys (snapshot, iv_smile, iv_term_structure, iv_surface, skew_analysis, oi_volume, pcr_summary, expected_move, key_metrics, vol_premium) where **each chart step is wrapped in its own try/except** so one failure doesn't blank the tab.
- **`options_simulation_service.py`** — `run_simulation(payload)` validates the request and bounds the grid (`MAX_STRIKES=15, MAX_EXPIRIES=6, MAX_IVS=5, MAX_CELLS=300, MAX_POINTS=201`), then hands off to `core.options.simulation.expiry.simulate_expiry` / `parse_expiries`. `resolve_spot(ticker, override)` prefers an explicit spot, else Yahoo.

### `core/market/analyzer.py`

`MarketAnalyzer(ticker, start_date, frequency, end_date)`, `is_data_valid()`, and the chart builders `generate_scatter_plots`, `generate_high_low_scatter`, `generate_return_osc_high_low_chart`, `generate_volatility_dynamics`, `generate_oscillation_projection`, `analyze_options`. Each returns base64 PNG strings plus feature series/DataFrames; it is the workhorse behind the statistical, assessment and market-review slices.

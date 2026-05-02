# OptionLab — Market Analysis Dashboard

Flask-based market analysis dashboard with options strategy tools.
Pulls historical prices and option chains via [yfinance](https://github.com/ranaroussi/yfinance),
caches them in SQLite, and renders a streaming HTMX UI with vanilla JS state
management on top of Chart.js / Alpine.js.

---

## Architecture

```
app.py                       Flask entry point — registers blueprints, middleware, scheduler
└── routes/                  Thin HTTP routing layer (blueprints only, no business logic)
    ├── core.py                /, /render/*, form handling
    ├── data.py                /api/data/*, /health/*
    ├── market.py              /api/signals, /api/market_review_ts
    ├── options.py             /api/option_chain, /api/options_chart/*, /api/odds_with_vol
    ├── portfolio.py           /api/portfolio_analysis, /api/portfolio/positions
    ├── regime.py              /api/regime/*
    └── strategies.py          /api/strategies, /api/strategy/*
└── services/                Orchestration layer (Flask-aware, no heavy computation)
    ├── market_analysis/       Statistical & assessment slice generation
    ├── market_service.py      Ticker validation + market review
    ├── options_chain_service.py  Chain fetch, filter, chart generation
    ├── portfolio_service.py   Tracked-position CRUD
    ├── portfolio_analysis_service.py  Multi-leg portfolio analytics
    ├── strategy_builder.py    Strategy instantiation from live chain
    ├── chart_service.py       Matplotlib → base64 PNG rendering
    ├── form_service.py        POST form normalisation
    ├── health_service.py      DB freshness metrics
    ├── regime_service.py      Regime labelling & persistence
    ├── signals_service.py     OHLCV signal vectors
    ├── strategy_service.py    Strategy catalogue & analytics
    └── validation_service.py  Pure form-value validation
└── core/                    Pure computation (no Flask, no I/O)
    ├── market/
    │   ├── analyzer.py          Master OHLCV → features + charts pipeline
    │   ├── data_context.py      Data fetch & resample (DB first, yfinance fallback)
    │   ├── price_dynamic.py     Backward-compat shim over DataContext
    │   ├── charts/              Matplotlib renderers (scatter, volatility, projection, …)
    │   ├── features/            Oscillation, returns, volatility primitives
    │   └── projections/         Oscillation projection logic
    ├── options/
    │   ├── chain/               IV metrics, liquidity, term structure, filters
    │   ├── charts/              IV smile, surface, skew, OI/volume, PCR renderers
    │   └── greeks/              Black–Scholes Greeks (vectorised) + portfolio theta
    ├── strategies/              Multi-leg strategy definitions + payoff/Greek aggregation
    ├── portfolio/               P&L attribution & Greek aggregation across legs
    ├── market_review/           Cross-ticker summary table + time-series
    ├── signals/                 HV, RSI, Bollinger, bundle
    ├── regime/                  Volatility / direction regime classification
    ├── decision/                Put-selling candidate scoring pipeline
    ├── correlation_validator.py Rolling pairwise correlations
    └── _shared/                 Plotting helpers, types, validators
└── data_pipeline/           Download · clean · process · persist
    ├── data_ops/              DataService facade (DB-first cache, 60 s freshness)
    ├── db.py                  SQLite context manager (WAL, synchronous=NORMAL)
    ├── repos.py               SQL builders (prices, regime, positions, …)
    ├── yf_client.py           Single chokepoint for yfinance (token-bucket throttle, proxy)
    ├── downloader.py          Raw bar / chain fetch with gap detection
    ├── cleaning.py            Time-series alignment & anomaly repair
    ├── processing.py          Feature engineering (returns, MAs, HV)
    ├── scheduler.py           APScheduler daily + monthly correlation refresh
    ├── job_cache.py           In-process TTL cache for /render/<kind> payloads
    └── quality_log.py         Pipeline anomaly persistence
└── utils/                   Shared helpers (ticker normalisation, error envelopes, …)
    ├── constants.py           Domain defaults (DEFAULT_TICKER, FREQUENCY_DISPLAY, …)
    ├── date_helpers.py        parse_month_str, exclusive_month_end
    ├── network.py             init_yf_proxy, yf_throttle (token-bucket rate limiter)
    ├── api_errors.py          ApiError + unified Flask JSON error envelope
    ├── data_utils.py          Small numeric helpers
    ├── ticker_utils.py        Yahoo ↔ Futu ticker normalisation
    ├── render_helpers.py      Streaming slice renderers for HTMX
    └── rate_limit.py          Rate-limit utilities
└── static/                  Vanilla JS modules + state machines
└── templates/               Jinja2 skeleton + HTMX fragments
```

**Import direction is one-way:** `app.py → routes/ → services/ → core/ → data_pipeline/`.
`core/` and `data_pipeline/` must not reach back into `services/`, `routes/` or `app.py`.

The frontend uses a **lazy / streaming tab** model: `POST /` returns a
skeleton in well under a second; each tab partial then fetches its slice
from `/render/<kind>?job=…&ticker=…` in parallel. See
[`docs/frontend_architecture.md`](docs/frontend_architecture.md) for the full
contract (state machine, tab flags, P1–P5 design principles).

---

## Module reference

### `app.py`
Flask entry point. Registers blueprints, installs the unified error envelope
and `/api/v1` alias middleware, mounts `flask-limiter`, propagates `YF_PROXY`
to `curl_cffi`, initialises the SQLite schema, and (for one elected worker)
starts the APScheduler daily/monthly jobs.

### `routes/` — HTTP blueprints (thin, no business logic)

| Blueprint | File | Endpoints |
|---|---|---|
| `core_bp` | [`routes/core.py`](routes/core.py) | `GET /`, `POST /`, `/render/*` |
| `data_bp` | [`routes/data.py`](routes/data.py) | `/api/data/seed`, `/health/*` |
| `market_bp` | [`routes/market.py`](routes/market.py) | `/api/signals`, `/api/market_review_ts` |
| `options_bp` | [`routes/options.py`](routes/options.py) | `/api/option_chain`, `/api/options_chart/*`, `/api/odds_with_vol` |
| `portfolio_bp` | [`routes/portfolio.py`](routes/portfolio.py) | `/api/portfolio_analysis`, `/api/portfolio/positions` |
| `regime_bp` | [`routes/regime.py`](routes/regime.py) | `/api/regime/*` |
| `strategies_bp` | [`routes/strategies.py`](routes/strategies.py) | `/api/strategies`, `/api/strategy/*` |

### `services/` — orchestration (Flask-aware, no computation)

| File | Role | Pulls from |
|---|---|---|
| [`services/market_analysis/_service.py`](services/market_analysis/_service.py) | Top-level "run a full market analysis" facade for `/render/statistical` and `/render/assessment`. | `core/market.analyzer`, `core/correlation_validator`, `data_pipeline/data_ops` |
| [`services/chart_service.py`](services/chart_service.py) | Builds matplotlib figures and returns base64 PNGs; caches by `(ticker, kind, params)`. | `core/*`, `data_pipeline/data_ops` |
| [`services/form_service.py`](services/form_service.py) | Extracts and normalises POST form fields, applying defaults from `utils/constants.py`. | `utils/constants`, `utils/date_helpers` |
| [`services/health_service.py`](services/health_service.py) | Aggregates DB freshness / row-count / NaN metrics for `/health/*`. | `data_pipeline/db`, `data_pipeline/repos` |
| [`services/market_service.py`](services/market_service.py) | Ticker validation + market-review summary for `/api/validate_*` and `/render/market_review`. | `core/market_review`, `core/market.data_context` |
| [`services/options_chain_service.py`](services/options_chain_service.py) | Drives `/render/options_chain` and `/api/option_chain`: fetches live chain, applies DTE/moneyness filters, generates charts/tables. | `core/options/chain/analyzer`, `core/options/chain/filters` |
| [`services/options_chain_preload.py`](services/options_chain_preload.py) | Pre-loads option chain for Position module dropdowns with in-memory caching. | `data_pipeline/yf_client` |
| [`services/portfolio_service.py`](services/portfolio_service.py) | CRUD for tracked positions in SQLite; computes live P&L via `data_pipeline/repos`. | `core/portfolio`, `data_pipeline/repos` |
| [`services/portfolio_analysis_service.py`](services/portfolio_analysis_service.py) | Stateless "analyse this basket of legs" endpoint backing `/api/portfolio_analysis`. | `core/options/greeks/portfolio`, `core/strategies` |
| [`services/regime_service.py`](services/regime_service.py) | Labels & persists market regimes; serves `/api/regime/*`. | `core/regime`, `data_pipeline/repos` |
| [`services/signals_service.py`](services/signals_service.py) | Wraps `core/signals` over DB-cached daily bars for `/api/signals`. | `core/signals`, `data_pipeline/data_ops` |
| [`services/strategy_service.py`](services/strategy_service.py) | API layer over `core/strategies` multi-leg analytics. | `core/strategies` |
| [`services/strategy_builder.py`](services/strategy_builder.py) | Picks real strikes from the live chain to instantiate a strategy template. | `core/strategies`, `core/options/chain/analyzer` |
| [`services/validation_service.py`](services/validation_service.py) | Pure form-value validation rules (date ranges, frequency, …). | (none) |

### `core/` — pure computation (no Flask, no I/O)

| File | Role |
|---|---|
| [`core/market/analyzer.py`](core/market/analyzer.py) | Master "analyse OHLCV → features + chart specs" pipeline; the workhorse used by the statistical & assessment tabs. |
| [`core/market/data_context.py`](core/market/data_context.py) | Encapsulates data fetching & resampling (DB first, yfinance fallback). Returns plain DataFrames. |
| [`core/market/price_dynamic.py`](core/market/price_dynamic.py) | Backward-compat wrapper over `DataContext` for legacy callers. |
| [`core/market_review/`](core/market_review/) | Cross-ticker summary table (`compute.py`), fetch helpers (`fetch.py`), time-series (`timeseries.py`). |
| [`core/signals/`](core/signals/) | Pure-OHLCV signals: HV (`hv.py`), RSI (`rsi.py`), Bollinger (`bollinger.py`), bundle (`bundle.py`). |
| [`core/regime/`](core/regime/) | Volatility / direction → discrete regime label (`classify.py`, `series.py`, `models.py`). |
| [`core/options/chain/analyzer.py`](core/options/chain/analyzer.py) | IV smile, skew, OI profile, expected move from a snapshot chain. |
| [`core/options/chain/filters.py`](core/options/chain/filters.py) | DTE / moneyness / contract-count filtering over option-chain records. |
| [`core/options/greeks/black_scholes.py`](core/options/greeks/black_scholes.py) | Vectorised Black–Scholes Greeks for whole chains. |
| [`core/options/greeks/portfolio.py`](core/options/greeks/portfolio.py) | Portfolio-level Greek aggregation + theta-decay path. |
| [`core/strategies/`](core/strategies/) | Multi-leg strategy definitions (`factories.py`), payoff/Greek aggregation (`analyze.py`, `payoff.py`, `greeks.py`). |
| [`core/portfolio/`](core/portfolio/) | P&L attribution (`attribution.py`) and Greek aggregation (`greeks.py`) across tracked legs. |
| [`core/decision/`](core/decision/) | Quant scoring/ranking flow for put-selling candidates. |
| [`core/correlation_validator.py`](core/correlation_validator.py) | Rolling pairwise correlations across feature columns. |

### `data_pipeline/` — download / cache / persist

| File | Role |
|---|---|
| [`data_pipeline/yf_client.py`](data_pipeline/yf_client.py) | Single chokepoint for `yfinance` calls: token-bucket throttle, proxy probe, error mapping. |
| [`data_pipeline/downloader.py`](data_pipeline/downloader.py) | Uses `yf_client` to fetch raw bars / option chains, with gap detection against the DB. |
| [`data_pipeline/cleaning.py`](data_pipeline/cleaning.py) | Drops/repairs broken rows from raw frames. |
| [`data_pipeline/processing.py`](data_pipeline/processing.py) | Feature engineering (returns, MAs, HV) on cleaned bars. |
| [`data_pipeline/data_ops/`](data_pipeline/data_ops/) | `DataService` facade — DB-first cache with a 60 s freshness window, the single read entry-point. |
| [`data_pipeline/db.py`](data_pipeline/db.py) | `get_conn()` context manager, schema bootstrap, WAL pragmas, thread-local connection pooling. |
| [`data_pipeline/repos.py`](data_pipeline/repos.py) | Repository wrappers — the only modules that build SQL. |
| [`data_pipeline/scheduler.py`](data_pipeline/scheduler.py) | APScheduler wrapper: daily backfill + monthly correlation refresh, gated by a leader-lock file. |
| [`data_pipeline/job_cache.py`](data_pipeline/job_cache.py) | TTL'd in-process map keyed by `job_id`; lets `/render/<kind>` partials share the same form payload. |
| [`data_pipeline/quality_log.py`](data_pipeline/quality_log.py) | Persists pipeline anomalies for `/health/data`. |

### `utils/`

| File | Role |
|---|---|
| [`utils/constants.py`](utils/constants.py) | Domain constants (default ticker/window/frequency, MA windows). |
| [`utils/date_helpers.py`](utils/date_helpers.py) | `parse_month_str`, `exclusive_month_end`. |
| [`utils/network.py`](utils/network.py) | `init_yf_proxy()` (propagates `YF_PROXY` → env vars) and `yf_throttle()` (token-bucket rate limiter). |
| [`utils/api_errors.py`](utils/api_errors.py) | `ApiError` class + Flask error handlers that produce a uniform JSON envelope. |
| [`utils/data_utils.py`](utils/data_utils.py) | Small numeric helpers shared across `core/`. |
| [`utils/ticker_utils.py`](utils/ticker_utils.py) | Yahoo ↔ Futu (`US.NVDA` / `NVDA`) ticker normalisation. |
| [`utils/render_helpers.py`](utils/render_helpers.py) | Streaming slice renderers for HTMX. |

### Frontend (`static/`, `templates/`)

- [`templates/index.html`](templates/index.html) is the skeleton; each
  `templates/partials/tab_*.html` is the markup loaded into the matching
  HTMX placeholder by `/render/<kind>`.
- [`static/main.js`](static/main.js) bootstraps the form and tab manager;
  per-tab logic lives in `market_review.js`, `option-chain.js`,
  `position.js`, `regime.js`.
- [`static/api.js`](static/api.js) is the only `fetch` wrapper — it owns
  abort handling and error normalisation. Components must not call `fetch`
  directly.
- [`static/state/`](static/state/) holds the small reactive stores
  (`store.js`, `panelState.js`, `tabFlagsState.js`, `optionChainState.js`,
  …) that back the streaming-tab state machine.
- [`static/eventBus.js`](static/eventBus.js) is the cross-component pub/sub.
- [`static/cache.js`](static/cache.js) is the versioned `localStorage` wrapper.
- [`static/components/payoff_chart.js`](static/components/payoff_chart.js) is
  the only Chart.js renderer that runs in the browser (everything else is
  server-side PNG).

### `tests/`
`pytest` suites mirroring the package layout (`test_<module>.py`), plus
`tests/unit/` for vitest specs and `tests/e2e/` for Playwright with mocked
Flask routes. `conftest.py` loads `.env` so proxy-dependent tests can reach
Yahoo.

### `scripts/`
Repo-maintenance helpers, all standalone:
`doc_guard.py` (lint tag/ADR/doc invariants — runs in CI),
`audit_tags.py`, `regen_adr_index.py`, `draft_doc_updates.py`,
`find_drift_candidates.py`, `commit_msg_check.py`, `perf_regression.py`,
`seed_history.py`.

---

## HTTP API surface

| Method · Path | Purpose |
|---|---|
| `GET /` · `POST /` | Dashboard skeleton; POST registers a job and streams tabs. |
| `GET /render/{market_review,statistical,assessment,options_chain}` | HTMX tab fragments (consume `?job=&ticker=`). |
| `GET /api/ping`, `GET /api/_meta` | Liveness + route discovery. |
| `POST /api/validate_ticker`, `POST /api/validate_tickers` | Ticker existence check. |
| `GET /api/option_chain`, `POST /api/preload_option_chain` | Live chain fetch (filtered by DTE/moneyness). |
| `GET /api/options_chart/{iv_smile,oi_profile}` | Standalone option-chain chart JSON endpoints. |
| `POST /api/portfolio_analysis` | Stateless multi-leg analytics. |
| `GET\|POST /api/portfolio/positions`, `POST /api/portfolio/positions/<id>/close`, `GET /api/portfolio/snapshot` | Tracked-position CRUD + live snapshot. |
| `GET /api/strategies`, `POST /api/strategy/{analyze,build_from_chain}` | Strategy catalogue + analytics. |
| `GET /api/signals` | Pure-OHLCV signal vector. |
| `POST /api/market_review_ts`, `POST /api/odds_with_vol` | Time-series payloads for browser-side Chart.js. |
| `GET /api/regime/{current,history}`, `POST /api/regime/backfill` | Regime read + backfill. |
| `POST /api/data/seed` | One-shot historical backfill (rate-limited). |
| `GET /health/data`, `GET /health/status` | DB freshness + process health. |

`/api/v1/<path>` is an alias for every `/api/<path>` route (rewriting
middleware in `app.py`).

---

## Quick start

### 1. Prerequisites
- Python 3.12+
- Node 18+ (only for running the JS unit tests)

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install                  # only needed for vitest / playwright
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env (DB path, optional YF_PROXY, scheduler tickers, …)
```

### 4. Run

```bash
# Dev server (autoreload)
python app.py                # http://127.0.0.1:5001

# Production
gunicorn app:app -b 0.0.0.0:5001 --workers 2 --threads 4
```

---

## Testing

| Command | Scope |
|---|---|
| `pytest` | Full Python suite (incl. e2e) |
| `pytest -x --tb=short` | Stop at first failure |
| `pytest tests/e2e/` | Playwright e2e only (chromium) |
| `pytest tests/unit/ tests/test_*.py -k …` | Targeted unit / integration |
| `npx vitest run` | JS unit tests (`tests/unit/*.js`) |
| `python scripts/perf_regression.py -v` | 4-ticker concurrent perf benchmark |

The Playwright suite uses mocked Flask routes (`tests/e2e/conftest.py`) so it
runs offline. The perf benchmark spins up a real WSGI server and measures the
end-to-end fan-out time for `/render/<kind>` × tickers.

---

## Key environment variables

See [`.env.example`](.env.example) for the full list. The most relevant ones:

| Variable | Purpose | Default |
|---|---|---|
| `MARKET_DB_PATH` | SQLite path | `./market_data.sqlite` |
| `YF_PROXY` | HTTP/SOCKS proxy for yfinance (curl_cffi) | `http://127.0.0.1:1087` (recommended; required behind VPN) |
| `AUTO_UPDATE_TICKERS` | Comma-separated tickers for daily backfill | unset |
| `SCHED_TZ` | Timezone for scheduler cron | `UTC` |
| `JOB_CACHE_TTL` | Per-job render cache lifetime (seconds) | `90` |

---

## Operational notes

- **yfinance rate limits** are aggressive. The downloader throttles globally
  with a token bucket (default 5 req/s, burst 5) and uses a DB-first cache to avoid
  redundant downloads. Do not pass `session=requests.Session()` — yfinance
  uses `curl_cffi` and silently breaks otherwise.
- **DB layer**: always go through `data_pipeline/db.py::get_conn()`; it
  enables WAL mode, sets `synchronous=NORMAL`, and is safe to share across
  threads.
- **Logging**: use `logging.getLogger(__name__)`; no `print()` in production
  code. The dev server logs to stderr at INFO.
- **Charts**: server-side base64 PNG generation in `services/chart_service.py`.
  The market-review chart is the one exception — it streams JSON to Chart.js
  on the browser.

---

## Project conventions

- Public function signatures carry type hints.
- User-facing strings may be Chinese; code, comments and tests are in
  English.
- Financial domain constants (MA windows, oscillation params, etc.) live in
  `utils/constants.py` and are intentional — do **not** refactor them as
  "magic numbers".
- See [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
  for the AI-assistant ground rules and the failure-pattern feedback loop.

---

## Documentation

| File | Audience |
|---|---|
| [`docs/constraints.md`](docs/constraints.md) | **AI reviewers + contributors — read first** |
| [`docs/glossary.md`](docs/glossary.md) | Domain terms (IV, HV, regime, …) |
| [`docs/decisions/`](docs/decisions/) | Architecture Decision Records |
| [`docs/frontend_architecture.md`](docs/frontend_architecture.md) | Frontend contributors |
| [`docs/guides/USER_GUIDE.md`](docs/guides/USER_GUIDE.md) | End users |
| [`docs/reference/optimization_manual.md`](docs/reference/optimization_manual.md) | Quant model reference |
| [`docs/reference/option_decision_process.md`](docs/reference/option_decision_process.md) | Decision-flow reference |
| [`docs/nav/system_nav.md`](docs/nav/system_nav.md) | Sitemap of all dashboard tabs |

> **Heads-up for AI / new contributors**: many "magic numbers" and "weird workarounds"
> in this codebase are deliberate. Code annotated with `WHY:` / `CONSTRAINT:` /
> `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` is justified — see
> [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the
> tag convention and review rules.

---

## License

Internal / unpublished. All rights reserved by the project owner.

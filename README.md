# OptionLab — Market Analysis Dashboard

Flask-based market analysis dashboard with options strategy tools.
Pulls historical prices and option chains via [yfinance](https://github.com/ranaroussi/yfinance),
caches them in SQLite, and renders a streaming HTMX UI with vanilla JS state
management on top of Chart.js / Alpine.js.

---

## Architecture

```
app.py                       Flask routes + HTMX streaming render endpoints
└── services/                Orchestration: format core results for routes
    ├── analysis_service.py
    ├── chart_service.py
    ├── options_chain_service.py
    └── …
└── core/                    Computation logic (no Flask, no I/O)
    ├── market_analyzer.py
    ├── options_greeks.py
    └── …
└── data_pipeline/           Download · clean · process · DB access
    ├── data_service.py        DB-first cache with 60 s freshness window
    ├── downloader.py          yfinance wrappers (throttled, proxy-aware)
    ├── cleaning.py / processing.py
    ├── job_cache.py           Per-job memoisation for /render/<kind>
    ├── db.py                  SQLite (WAL, synchronous=NORMAL)
    └── scheduler.py           APScheduler daily updates
└── utils/                   Shared helpers (ticker normalisation, etc.)
└── static/                  Vanilla JS modules + state machines
└── templates/               Jinja2 skeleton + HTMX fragments
```

**Import direction is one-way:** `app.py → services/ → core/ → data_pipeline/`.
`core/` and `data_pipeline/` must not reach back into `services/` or `app.py`.

The frontend uses a **lazy / streaming tab** model: `POST /` returns a
skeleton in well under a second; each tab partial then fetches its slice
from `/render/<kind>?job=…&ticker=…` in parallel. See
[`docs/frontend_architecture.md`](docs/frontend_architecture.md) for the full
contract (state machine, tab flags, P1–P5 design principles).

---

## Module reference

### `app.py`
Flask entry point. Registers HTTP routes, installs the unified error envelope
and `/api/v1` alias middleware, mounts `flask-limiter`, propagates `YF_PROXY`
to `curl_cffi`, initialises the SQLite schema, and (for one elected worker)
starts the APScheduler daily/monthly jobs. Owns `parse_tickers()` and
`_filter_option_chain()` — request-shape concerns that don't belong in a
service.

### `services/` — orchestration (Flask-aware, no computation)

| File                                                                    | Role                                                                                                        | Pulls from                                                                         |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| [analysis_service.py](services/analysis_service.py)                     | Top-level "run a full market analysis" facade used by `/render/statistical` and `/render/assessment`.       | `core/market_analyzer`, `core/correlation_validator`, `data_pipeline/data_service` |
| [chart_service.py](services/chart_service.py)                           | Builds matplotlib figures and returns base64 PNGs; caches by `(ticker, kind, params)`.                      | `core/*`, `data_pipeline/data_service`                                             |
| [form_service.py](services/form_service.py)                             | Extracts and normalises POST form fields, applying defaults from `utils/utils.py`.                          | `utils/utils`                                                                      |
| [health_service.py](services/health_service.py)                         | Aggregates DB freshness / row-count / NaN metrics for `/health/*`.                                          | `data_pipeline/db`, `data_pipeline/repos`                                          |
| [market_service.py](services/market_service.py)                         | Ticker validation + market-review summary for `/api/validate_*` and `/render/market_review`.                | `core/market_review`, `data_pipeline/yf_client`                                    |
| [options_chain_service.py](services/options_chain_service.py)           | Drives `/render/options_chain`: fetches live chain, runs the analyzer, builds IV-smile & OI-profile charts. | `core/options_chain_analyzer`, `chart_service`                                     |
| [portfolio_service.py](services/portfolio_service.py)                   | CRUD for tracked positions in SQLite; computes live P&L via `data_service`.                                 | `core/portfolio`, `data_pipeline/repos`                                            |
| [portfolio_analysis_service.py](services/portfolio_analysis_service.py) | Stateless "analyse this basket of legs" endpoint backing `/api/portfolio_analysis`.                         | `core/portfolio`, `core/options_greeks`                                            |
| [regime_service.py](services/regime_service.py)                         | Labels & persists market regimes; serves `/api/regime/*`.                                                   | `core/regime`, `data_pipeline/repos`                                               |
| [signals_service.py](services/signals_service.py)                       | Wraps `core/signals` over DB-cached daily bars for `/api/signals`.                                          | `core/signals`, `data_pipeline/data_service`                                       |
| [strategy_service.py](services/strategy_service.py)                     | API layer over `core/strategies` multi-leg analytics.                                                       | `core/strategies`                                                                  |
| [strategy_builder.py](services/strategy_builder.py)                     | Picks real strikes from the live chain to instantiate a strategy template.                                  | `core/strategies`, `core/options_chain_analyzer`                                   |
| [validation_service.py](services/validation_service.py)                 | Pure form-value validation rules (date ranges, frequency, …).                                               | (none)                                                                             |

### `core/` — pure computation (no Flask, no I/O)

| File                                                        | Role                                                                                                               |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [market_analyzer.py](core/market_analyzer.py)               | Master "analyse OHLCV → features + chart specs" pipeline; the workhorse used by the statistical & assessment tabs. |
| [market_review.py](core/market_review.py)                   | Cross-ticker summary table (last close, MA flags, HV percentile).                                                  |
| [signals.py](core/signals.py)                               | Pure-OHLCV signals: HV, RSI, mean-reversion, trend filter.                                                         |
| [regime.py](core/regime.py)                                 | Volatility / direction → discrete regime label.                                                                    |
| [price_dynamic.py](core/price_dynamic.py)                   | Volatility & momentum primitives shared by signals/regime.                                                         |
| [correlation_validator.py](core/correlation_validator.py)   | Rolling pairwise correlations across feature columns.                                                              |
| [options_greeks.py](core/options_greeks.py)                 | Vectorised Black–Scholes Greeks for whole chains.                                                                  |
| [options_chain_analyzer.py](core/options_chain_analyzer.py) | IV smile, skew, OI profile, expected move from a snapshot chain.                                                   |
| [option_decision.py](core/option_decision.py)               | Quant scoring/ranking flow for put-selling candidates.                                                             |
| [strategies.py](core/strategies.py)                         | Multi-leg strategy definitions + payoff/Greek aggregation.                                                         |
| [portfolio.py](core/portfolio.py)                           | Aggregates Greeks and attributes P&L across tracked legs.                                                          |

### `data_pipeline/` — download / cache / persist

| File                                             | Role                                                                                                       |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| [yf_client.py](data_pipeline/yf_client.py)       | Single chokepoint for `yfinance` calls: global 1.5 s throttle, proxy probe, error mapping.                 |
| [downloader.py](data_pipeline/downloader.py)     | Uses `yf_client` to fetch raw bars / option chains, with gap detection against the DB.                     |
| [cleaning.py](data_pipeline/cleaning.py)         | Drops/repairs broken rows from raw frames.                                                                 |
| [processing.py](data_pipeline/processing.py)     | Feature engineering (returns, MAs, HV) on cleaned bars.                                                    |
| [data_service.py](data_pipeline/data_service.py) | DB-first cache with a 60 s freshness window — the single read entry-point used by every service.           |
| [db.py](data_pipeline/db.py)                     | `get_conn()` context manager, schema bootstrap, WAL pragmas, thread-local connection pooling.              |
| [repos.py](data_pipeline/repos.py)               | Repository wrappers (`prices_repo`, `regime_repo`, `positions_repo`, …) — the only modules that build SQL. |
| [job_cache.py](data_pipeline/job_cache.py)       | TTL'd in-process map keyed by `job_id`; lets `/render/<kind>` partials share the same form payload.        |
| [scheduler.py](data_pipeline/scheduler.py)       | APScheduler wrapper: daily backfill + monthly correlation refresh, gated by a leader-lock file.            |
| [quality_log.py](data_pipeline/quality_log.py)   | Persists pipeline anomalies (empty downloads, NaN spikes) for `/health/data`.                              |

### `utils/`

| File                                     | Role                                                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------------- |
| [utils.py](utils/utils.py)               | Domain constants (default ticker/window/frequency, MA windows) and `init_yf_proxy()`. |
| [api_errors.py](utils/api_errors.py)     | `ApiError` class + Flask error handlers that produce a uniform JSON envelope.         |
| [data_utils.py](utils/data_utils.py)     | Small numeric helpers (recent-extreme change, etc.) shared across `core/`.            |
| [ticker_utils.py](utils/ticker_utils.py) | Yahoo ↔ Futu (`US.NVDA` / `NVDA`) ticker normalisation.                               |

### Frontend (`static/`, `templates/`)

- [`templates/index.html`](templates/index.html) is the skeleton; each
  `templates/partials/tab_*.html` is the markup loaded into the matching
  HTMX placeholder by `/render/<kind>`.
- [`static/main.js`](static/main.js) bootstraps the form and tab manager;
  per-tab logic lives in `market-review.js`, `option-chain.js`,
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

| Method · Path                                                                                                   | Purpose                                                    |
| --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `GET /` · `POST /`                                                                                              | Dashboard skeleton; POST registers a job and streams tabs. |
| `GET /render/{market_review,statistical,assessment,options_chain}`                                              | HTMX tab fragments (consume `?job=&ticker=`).              |
| `GET /api/ping`, `GET /api/_meta`                                                                               | Liveness + route discovery.                                |
| `POST /api/validate_ticker`, `POST /api/validate_tickers`                                                       | Ticker existence check.                                    |
| `GET /api/option_chain`, `POST /api/preload_option_chain`                                                       | Live chain fetch (filtered by DTE/moneyness).              |
| `GET /api/options_chart/{iv_smile,oi_profile}`                                                                  | Standalone option-chain chart endpoints.                   |
| `POST /api/portfolio_analysis`                                                                                  | Stateless multi-leg analytics.                             |
| `GET\|POST /api/portfolio/positions`, `POST /api/portfolio/positions/<id>/close`, `GET /api/portfolio/snapshot` | Tracked-position CRUD + live snapshot.                     |
| `GET /api/strategies`, `POST /api/strategy/{analyze,build_from_chain}`                                          | Strategy catalogue + analytics.                            |
| `GET /api/signals`                                                                                              | Pure-OHLCV signal vector.                                  |
| `POST /api/market_review_ts`, `POST /api/odds_with_vol`                                                         | Time-series payloads for browser-side Chart.js.            |
| `GET /api/regime/{current,history}`, `POST /api/regime/backfill`                                                | Regime read + backfill.                                    |
| `POST /api/data/seed`                                                                                           | One-shot historical backfill (rate-limited).               |
| `GET /health/data`, `GET /health/status`                                                                        | DB freshness + process health.                             |

`/api/v1/<path>` is an alias for every `/api/<path>` route (rewriting
middleware in `app.py`).

---

## Quick start

### 1. Prerequisites
- Python 3.11+
- Node 18+ (only for running the JS unit tests)

### 2. Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install                  # only needed for vitest / playwright
```

### 3. Configure
```bash
cp .env.example .env
# edit .env (DB path, optional YF_PROXY, scheduler tickers, …)
```

### 4. Run
```bash
# Dev server (autoreload)
python app.py                # http://127.0.0.1:5000

# Production
gunicorn app:app -b 0.0.0.0:5000 --workers 2 --threads 4
```

---

## Testing

| Command                                   | Scope                              |
| ----------------------------------------- | ---------------------------------- |
| `pytest`                                  | Full Python suite (incl. e2e)      |
| `pytest -x --tb=short`                    | Stop at first failure              |
| `pytest tests/e2e/`                       | Playwright e2e only (chromium)     |
| `pytest tests/unit/ tests/test_*.py -k …` | Targeted unit / integration        |
| `npx vitest run`                          | JS unit tests (`tests/unit/*.js`)  |
| `python scripts/perf_regression.py -v`    | 4-ticker concurrent perf benchmark |

The Playwright suite uses mocked Flask routes (`tests/e2e/conftest.py`) so it
runs offline. The perf benchmark spins up a real WSGI server and measures the
end-to-end fan-out time for `/render/<kind>` × tickers.

---

## Key environment variables

See [`.env.example`](.env.example) for the full list. The most relevant ones:

| Variable              | Purpose                                    | Default                                                    |
| --------------------- | ------------------------------------------ | ---------------------------------------------------------- |
| `MARKET_DB_PATH`      | SQLite path                                | `./market_data.sqlite`                                     |
| `YF_PROXY`            | HTTP/SOCKS proxy for yfinance (curl_cffi)  | `http://127.0.0.1:1087` (recommended; required behind VPN) |
| `AUTO_UPDATE_TICKERS` | Comma-separated tickers for daily backfill | unset                                                      |
| `SCHED_TZ`            | Timezone for scheduler cron                | `UTC`                                                      |
| `JOB_CACHE_TTL`       | Per-job render cache lifetime (seconds)    | `90`                                                       |

---

## Operational notes

- **yfinance rate limits** are aggressive. The downloader throttles globally
  with a 1.5 s minimum gap between calls and uses a DB-first cache to avoid
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
  `utils/utils.py` and are intentional — do **not** refactor them as
  "magic numbers".
- See [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
  for the AI-assistant ground rules and the failure-pattern feedback loop.

---

## Documentation

| File                                                                                     | Audience                                     |
| ---------------------------------------------------------------------------------------- | -------------------------------------------- |
| [`docs/constraints.md`](docs/constraints.md)                                             | **AI reviewers + contributors — read first** |
| [`docs/glossary.md`](docs/glossary.md)                                                   | Domain terms (IV, HV, regime, …)             |
| [`docs/decisions/`](docs/decisions/)                                                     | Architecture Decision Records                |
| [`docs/frontend_architecture.md`](docs/frontend_architecture.md)                         | Frontend contributors                        |
| [`docs/guides/USER_GUIDE.md`](docs/guides/USER_GUIDE.md)                                 | End users                                    |
| [`docs/reference/optimization_manual.md`](docs/reference/optimization_manual.md)         | Quant model reference                        |
| [`docs/reference/option_decision_process.md`](docs/reference/option_decision_process.md) | Decision-flow reference                      |
| [`docs/nav/system_nav.md`](docs/nav/system_nav.md)                                       | Sitemap of all dashboard tabs                |

> **Heads-up for AI / new contributors**: many "magic numbers" and "weird workarounds"
> in this codebase are deliberate. Code annotated with `WHY:` / `CONSTRAINT:` /
> `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` is justified — see
> [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the
> tag convention and review rules.

---

## License

Internal / unpublished. All rights reserved by the project owner.

# Module Reference

> L2 | 权威：目录树、逐模块职责、HTTP API 表面 | 不权威：运行时请求流与分层规则（见 `docs/architecture.md`）、进度（见 `STATUS.md`）

> 由原 `README.md` 的 Architecture 图、Module reference 与 HTTP API surface 三段搬来，措辞未改；链接前缀已改为相对 `docs/`。

```
app.py                       Flask entry point — registers blueprints, middleware, scheduler
└── routes/                  Thin HTTP routing layer (blueprints only, no business logic)
    ├── core.py                /, /render/*, form handling
    ├── data.py                /api/data/*, /health/*
    ├── market.py              /api/signals, /api/market_review_ts
    ├── options.py             /api/option_chain, /api/options_chart/*, /api/expiry_probability
    ├── portfolio.py           /api/portfolio_analysis, /api/portfolio/positions
    ├── regime.py              /api/regime/*
    └── strategies.py          /api/strategies, /api/strategy/*
└── services/                Orchestration layer (Flask-aware, no heavy computation)
    ├── market/                Price analysis domain
    │   ├── facade.py            Ticker validation + market review
    │   ├── analysis/            Statistical & assessment slice generation
    │   ├── charts.py            Matplotlib → base64 PNG rendering
    │   ├── signals.py           OHLCV signal vectors
    │   ├── form.py              POST form normalisation
    │   ├── validation.py        Pure form-value validation
    │   ├── health.py            DB freshness metrics
    │   └── dispatch.py          /render/<kind> streaming dispatch
    ├── options/               Options domain
    │   ├── chain.py             Chain fetch, filter, chart generation
    │   ├── preload.py           Chain preload for the position module
    │   ├── simulation.py        Expiry-simulation payload validation
    │   ├── strategies.py        Strategy catalogue & analytics
    │   └── builder.py           Strategy instantiation from live chain
    ├── portfolio/             Portfolio domain
    │   ├── facade.py            Tracked-position CRUD
    │   └── analysis.py          Multi-leg portfolio analytics
    └── regime/                Regime domain
        ├── facade.py            Regime labelling & persistence
        └── ops/                 History bootstrap + regime_log writes
└── core/                    Pure computation (no Flask, no I/O)
    ├── market/
    │   ├── analyzer.py          Master OHLCV → features + charts pipeline
    │   ├── data_context.py      Data fetch & resample (DB first, yfinance fallback)
    │   ├── correlation_validator.py Rolling pairwise correlations
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
    └── _shared/                 Plotting helpers, types, validators
└── data_pipeline/           Acquire · process · serve (six one-way stages, ADR 0011)
    ├── providers/             The ONLY `import yfinance`: vendor adapter + canonical schema + registry
    ├── store/                 Canonical schema, the only SQL, the failure log
    ├── ingest/                Business-day gap detection + raw_bars upsert
    ├── transform/             Alignment + anomaly flags + feature engineering (provider-agnostic)
    ├── read/                  DataService facade (DB-first cache, 60 s freshness)
    ├── orchestrate/           Update/backfill drivers, job cache, optional scheduler
    └── _state.py              Process-local query cache + update locks
└── utils/                   Shared helpers (ticker normalisation, error envelopes, …)
    ├── constants.py           Domain defaults (DEFAULT_TICKER, FREQUENCY_DISPLAY, …)
    ├── date_helpers.py        parse_month_str, exclusive_month_end
    ├── network.py             init_yf_proxy, yf_throttle (token-bucket rate limiter)
    ├── api_errors.py          ApiError + unified Flask JSON error envelope
    ├── ticker_utils.py        Yahoo ↔ Futu ticker normalisation
    ├── render_helpers.py      Streaming slice renderers for HTMX
    └── rate_limit.py          Rate-limit utilities
└── static/                  Vanilla JS modules + state machines
│   └── sim/                 Pure client-side payoff simulation (zero I/O — Pages-safe)
└── templates/               Jinja2 skeleton + HTMX fragments
```

## Module reference

### `app.py`
Flask entry point. Registers blueprints, installs the unified error envelope
and `/api/v1` alias middleware, installs the in-house per-IP rate limiter,
propagates `YF_PROXY` to `curl_cffi`, initialises the SQLite schema, and (for
one elected worker) starts the APScheduler daily/monthly jobs.

### `routes/` — HTTP blueprints (thin, no business logic)

| Blueprint | File | Endpoints |
|---|---|---|
| `core_bp` | [`routes/core.py`](../routes/core.py) | `GET /`, `POST /`, `/render/*` |
| `data_bp` | [`routes/data.py`](../routes/data.py) | `/api/data/seed`, `/health/*` |
| `market_bp` | [`routes/market.py`](../routes/market.py) | `/api/signals`, `/api/market_review_ts` |
| `options_bp` | [`routes/options.py`](../routes/options.py) | `/api/option_chain`, `/api/options_chart/*`, `/api/expiry_probability` |
| `portfolio_bp` | [`routes/portfolio.py`](../routes/portfolio.py) | `/api/portfolio_analysis`, `/api/portfolio/positions` |
| `regime_bp` | [`routes/regime.py`](../routes/regime.py) | `/api/regime/*` |
| `strategies_bp` | [`routes/strategies.py`](../routes/strategies.py) | `/api/strategies`, `/api/strategy/*` |

### `services/` — orchestration (Flask-aware, no computation)

Packaged by business domain; each package exposes a `facade.py` entry point.

**`services/market/`**

| File | Role | Pulls from |
|---|---|---|
| [`services/market/facade.py`](../services/market/facade.py) | Ticker validation + market-review summary for `/api/validate_*` and `/render/market_review`. | `core/market_review`, `core/market.data_context` |
| [`services/market/analysis/facade.py`](../services/market/analysis/facade.py) | Top-level "run a full market analysis" facade for `/render/statistical` and `/render/assessment`. | `core/market.analyzer`, `core/market.correlation_validator`, `data_pipeline/read` |
| [`services/market/charts.py`](../services/market/charts.py) | Builds matplotlib figures and returns base64 PNGs; caches by `(ticker, kind, params)`. | `core/*`, `data_pipeline/read` |
| [`services/market/signals.py`](../services/market/signals.py) | Wraps `core/signals` over DB-cached daily bars for `/api/signals`. | `core/signals`, `data_pipeline/read` |
| [`services/market/form.py`](../services/market/form.py) | Extracts and normalises POST form fields, applying defaults from `utils/constants.py`. | `utils/constants`, `utils/date_helpers` |
| [`services/market/validation.py`](../services/market/validation.py) | Pure form-value validation rules (date ranges, frequency, …). | (none) |
| [`services/market/health.py`](../services/market/health.py) | Aggregates DB freshness / row-count / NaN metrics for `/health/*`. | `data_pipeline/store` |
| [`services/market/dispatch.py`](../services/market/dispatch.py) | Shared `/render/<kind>` handler: job lookup, memoisation, fragment render. | `services/market/analysis`, `services/options/chain` |

**`services/options/`**

| File | Role | Pulls from |
|---|---|---|
| [`services/options/chain.py`](../services/options/chain.py) | Drives `/render/options_chain` and `/api/option_chain`: fetches live chain, applies DTE/moneyness filters, generates charts/tables. | `core/options/chain/analyzer`, `core/options/chain/filters` |
| [`services/options/preload.py`](../services/options/preload.py) | Pre-loads option chain for Position module dropdowns with in-memory caching. | `data_pipeline/yf_client` |
| [`services/options/simulation.py`](../services/options/simulation.py) | Validates `POST /api/simulate_expiry` payloads and bounds the strike × expiry × IV grid. | `core/options/simulation` |
| [`services/options/strategies.py`](../services/options/strategies.py) | API layer over `core/strategies` multi-leg analytics. | `core/strategies` |
| [`services/options/builder.py`](../services/options/builder.py) | Picks real strikes from the live chain to instantiate a strategy template. | `core/strategies`, `core/options/chain/analyzer` |

**`services/portfolio/`**

| File | Role | Pulls from |
|---|---|---|
| [`services/portfolio/facade.py`](../services/portfolio/facade.py) | CRUD for tracked positions in SQLite; computes live P&L via `data_pipeline/store/repos`. | `core/portfolio`, `data_pipeline/store/repos` |
| [`services/portfolio/analysis.py`](../services/portfolio/analysis.py) | Stateless "analyse this basket of legs" endpoint backing `/api/portfolio_analysis`. | `core/options/greeks/portfolio`, `core/strategies` |

**`services/regime/`**

| File | Role | Pulls from |
|---|---|---|
| [`services/regime/facade.py`](../services/regime/facade.py) | Labels & persists market regimes; serves `/api/regime/*`. | `core/regime`, `data_pipeline/store/repos` |
| [`services/regime/ops/`](../services/regime/ops/) | History bootstrap + `regime_log` read/write helpers. | `data_pipeline/store/db`, `data_pipeline/downloader` |

### `core/` — pure computation (no Flask, no I/O)

| File | Role |
|---|---|
| [`core/market/analyzer.py`](../core/market/analyzer.py) | Master "analyse OHLCV → features + chart specs" pipeline; the workhorse used by the statistical & assessment tabs. |
| [`core/market/data_context.py`](../core/market/data_context.py) | Encapsulates data fetching & resampling (DB first, yfinance fallback). Returns plain DataFrames. |
| [`core/market_review/`](../core/market_review/) | Cross-ticker summary table (`compute.py`), fetch helpers (`fetch.py`), time-series (`timeseries.py`). |
| [`core/signals/`](../core/signals/) | Pure-OHLCV signals: HV (`hv.py`), RSI (`rsi.py`), Bollinger (`bollinger.py`), bundle (`bundle.py`). |
| [`core/regime/`](../core/regime/) | Volatility / direction → discrete regime label (`classify.py`, `series.py`, `models.py`). |
| [`core/options/chain/analyzer.py`](../core/options/chain/analyzer.py) | IV smile, skew, OI profile, expected move from a snapshot chain. |
| [`core/options/chain/filters.py`](../core/options/chain/filters.py) | DTE / moneyness / contract-count filtering over option-chain records. |
| [`core/options/greeks/black_scholes.py`](../core/options/greeks/black_scholes.py) | Vectorised Black–Scholes Greeks for whole chains. |
| [`core/options/greeks/portfolio.py`](../core/options/greeks/portfolio.py) | Portfolio-level Greek aggregation + theta-decay path. |
| [`core/strategies/`](../core/strategies/) | Multi-leg strategy definitions (`factories.py`), payoff/Greek aggregation (`analyze.py`, `payoff.py`, `greeks.py`). |
| [`core/portfolio/`](../core/portfolio/) | P&L attribution (`attribution.py`) and Greek aggregation (`greeks.py`) across tracked legs. |
| [`core/decision/`](../core/decision/) | Quant scoring/ranking flow for put-selling candidates. |
| [`core/market/correlation_validator.py`](../core/market/correlation_validator.py) | Rolling pairwise correlations across feature columns. |

### `data_pipeline/` — download / cache / persist

| File | Role |
|---|---|
| [`data_pipeline/providers/`](../data_pipeline/providers/) | The single chokepoint for `yfinance` (adapter + canonical mapping + registry) and the token-bucket throttle / proxy probe. |
| [`data_pipeline/ingest/`](../data_pipeline/ingest/) | Business-day gap detection and the `raw_bars` upsert, acquisition via `providers.get_provider()`. |
| [`data_pipeline/transform/`](../data_pipeline/transform/) | Business-day alignment, anomaly flags (gaps NA — never interpolated) and feature engineering (returns, MAs, HV). |
| [`data_pipeline/read/`](../data_pipeline/read/) | `DataService` facade — DB-first cache with a 60 s freshness window, the single read entry-point. |
| [`data_pipeline/store/`](../data_pipeline/store/) | `db.py` (`get_conn()`, schema bootstrap, WAL pragmas, thread-local pooling), `repos.py` (the only SQL), `quality_log.py`. |
| [`data_pipeline/orchestrate/`](../data_pipeline/orchestrate/) | Update/seed drivers, chunked backfill, the `/render/<kind>` TTL cache, and the optional APScheduler wrapper (lazy import; only needed when `AUTO_UPDATE_TICKERS` is set). |

### `utils/`

| File | Role |
|---|---|
| [`utils/constants.py`](../utils/constants.py) | Domain constants (default ticker/window/frequency, MA windows). |
| [`utils/date_helpers.py`](../utils/date_helpers.py) | `parse_month_str`, `exclusive_month_end`. |
| [`utils/network.py`](../utils/network.py) | `init_yf_proxy()` (propagates `YF_PROXY` → env vars) and `yf_throttle()` (**outbound** token-bucket throttle for yfinance). |
| [`utils/rate_limit.py`](../utils/rate_limit.py) | **Inbound** per-IP throttle: `rate_limit()` token bucket + `install(app)` global hook. 429s use the same JSON envelope as `ApiError` (`code: "rate_limited"`). |
| [`utils/api_errors.py`](../utils/api_errors.py) | `ApiError` class + Flask error handlers that produce a uniform JSON envelope. |
| [`utils/ticker_utils.py`](../utils/ticker_utils.py) | Yahoo ↔ Futu (`US.NVDA` / `NVDA`) ticker normalisation. |
| [`utils/render_helpers.py`](../utils/render_helpers.py) | Streaming slice renderers for HTMX. |

### Frontend (`static/`, `templates/`)

- [`templates/index.html`](../templates/index.html) is the skeleton. Tab shells
  are server-side includes (`templates/partials/tab_*.html`); the actual
  content fragments swapped into the HTMX placeholders by `/render/<kind>`
  live in [`templates/partials/fragments/`](../templates/partials/fragments/).
- [`static/main.js`](../static/main.js) bootstraps the form and tab manager;
  per-tab logic lives in `market_review.js`, `option-chain.js`,
  `position.js`, `option_pricing_matrix.js`, `regime.js`, `simulation.js`.
- [`static/api.js`](../static/api.js) is the only `fetch` wrapper — it owns
  abort handling and error normalisation. Components must not call `fetch`
  directly.
- [`static/state/`](../static/state/) holds the small reactive stores
  (`store.js`, `panelState.js`, `tabFlagsState.js`, `optionChainState.js`,
  …) that back the streaming-tab state machine.
- [`static/eventBus.js`](../static/eventBus.js) is the cross-component pub/sub.
- [`static/cache.js`](../static/cache.js) is the versioned `localStorage` wrapper.
- Chart.js renderers that run in the browser (everything else is
  server-side PNG): [`static/market_review_chart.js`](../static/market_review_chart.js)
  and [`static/components/payoff_chart.js`](../static/components/payoff_chart.js).
- [`static/sim/`](../static/sim/) — **pure, dependency-free, zero-I/O** payoff
  simulator (Black–Scholes pricing, expiry P&L, distribution stats). Shared by the
  Flask "Simulation" tab and the standalone GitHub Pages site. No `fetch` — portable.
- [`static/simulation.js`](../static/simulation.js) — DOM wiring for
  the Simulation tab (leg builder, dual-IV link toggle, K × DTE matrix).

### `tests/`
`pytest` suites mirroring the package layout (`test_<module>.py`), plus
`tests/unit/` for vitest specs and `tests/e2e/` for Playwright with mocked
Flask routes. `conftest.py` loads `.env` so proxy-dependent tests can reach
Yahoo.

### `scripts/`
Repo-maintenance helpers, all standalone:
`doc_guard.py` (lint tag/ADR/doc invariants — runs in CI),
`audit_tags.py`, `regen_adr_index.py`, `draft_doc_updates.py`,
`find_drift_candidates.py`, `perf_regression.py`, `seed_history.py`,
`gen_sim_golden.py` (emit JS/Python parity fixtures for the Simulation tab).

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
| `POST /api/market_review_ts`, `POST /api/expiry_probability` | Time-series payloads for browser-side Chart.js. |
| `GET /api/regime/{current,history}`, `POST /api/regime/backfill` | Regime read + backfill. |
| `POST /api/data/seed` | One-shot historical backfill (rate-limited). |
| `GET /health/data`, `GET /health/status` | DB freshness + process health. |

`/api/v1/<path>` is an alias for every `/api/<path>` route (rewriting
middleware in `app.py`).

> **Simulation and Option Pricing Matrix tabs** are purely client-side
> (`static/sim/` + `static/simulation.js`, `static/option_pricing_matrix.js`).
> They perform Black–Scholes pricing, expiry-payoff math and option-pricing-matrix
> evaluation in the browser and need **no** HTTP endpoint, so they also run
> standalone on GitHub Pages.

---

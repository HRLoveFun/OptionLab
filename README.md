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

| Variable              | Purpose                                    | Default                |
| --------------------- | ------------------------------------------ | ---------------------- |
| `MARKET_DB_PATH`      | SQLite path                                | `./market_data.sqlite` |
| `YF_PROXY`            | HTTP/SOCKS proxy for yfinance (curl_cffi)  | unset (direct)         |
| `AUTO_UPDATE_TICKERS` | Comma-separated tickers for daily backfill | unset                  |
| `SCHED_TZ`            | Timezone for scheduler cron                | `UTC`                  |
| `JOB_CACHE_TTL`       | Per-job render cache lifetime (seconds)    | `90`                   |

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

| File                                                                                     | Audience                      |
| ---------------------------------------------------------------------------------------- | ----------------------------- |
| [`docs/frontend_architecture.md`](docs/frontend_architecture.md)                         | Frontend contributors         |
| [`docs/guides/USER_GUIDE.md`](docs/guides/USER_GUIDE.md)                                 | End users                     |
| [`docs/reference/optimization_manual.md`](docs/reference/optimization_manual.md)         | Quant model reference         |
| [`docs/reference/option_decision_process.md`](docs/reference/option_decision_process.md) | Decision-flow reference       |
| [`docs/nav/system_nav.md`](docs/nav/system_nav.md)                                       | Sitemap of all dashboard tabs |

---

## License

Internal / unpublished. All rights reserved by the project owner.

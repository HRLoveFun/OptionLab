# Copilot Instructions — OptionStrategy

## Project Overview

Flask-based market analysis dashboard with options strategy tools.
- **Backend**: Python 3.12, Flask, SQLite (WAL mode), APScheduler, yfinance
- **Frontend**: Vanilla JS + CSS + Jinja2 templates
- **Architecture**: `app.py` → `services/` → `core/` → `data_pipeline/`

## Code Style

- Language: Python code and comments in **English**; user-facing strings may be Chinese
- Use `logging.getLogger(__name__)` — never `print()` in production code
- Prefer specific exception types over bare `except Exception`
- Type hints on public function signatures
- Constants belong in `utils/utils.py` or environment variables (see `.env.example`)

## Architecture Rules

- **Import direction**: `app.py` → `services/` → `core/` → `data_pipeline/`; never reverse
- **No circular imports**: `data_pipeline/` must not import from `services/` or `core/`
- `core/` contains computation logic — no Flask request handling
- `services/` orchestrates `core/` modules and formats results for routes
- `data_pipeline/` handles download, cleaning, processing, and DB access

## Database

- SQLite via `data_pipeline/db.py` — always use `get_conn()` context manager
- WAL mode enabled; `PRAGMA synchronous=NORMAL`
- DB path from `MARKET_DB_PATH` env var, default `./market_data.sqlite`

## Testing

- Framework: **pytest** (configured in `pyproject.toml`)
- Test files: `tests/test_*.py`
- Run: `pytest` or `pytest -x --tb=short`

## Environment Variables

See `.env.example` for all supported variables and defaults.

## Build & Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py                    # dev server on :5000
gunicorn app:app -b 0.0.0.0:5000  # production
```

## Key Patterns

- Financial domain constants (MA windows, oscillation params) are intentional — don't refactor as "magic numbers"
- Chart generation returns base64-encoded images via `chart_service.py`
- Options Greeks use vectorized Black-Scholes in `core/options_greeks.py`
- Data freshness: 60-second cooldown per ticker in `DataService`

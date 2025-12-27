# Market Observation Dashboard

Flask-based dashboard for market analysis, oscillation statistics, options P&L sketches, and quick multi-asset reviews. Data comes from Yahoo Finance, is optionally cached in SQLite, and is visualized with matplotlib on the backend and vanilla JS on the frontend.

## Highlights
- Multi-frequency returns/oscillation analysis with horizon-aware filtering (D/W/ME/QE).
- Oscillation projection with bias tuning and options portfolio P&L charting.
- Market review table across major benchmarks (USD, rates, gold, US/EU/Asia equity indices) with returns, volatility, and correlations.
- Client-side form persistence, async ticker validation, and collapsible options editor.

## Architecture
- app.py: Flask entrypoint, routes, and scheduler bootstrap.
- core/: Price shaping and analytics (price_dynamic, market_analyzer, market_review, correlation_validator).
- services/: Request orchestration, validation, and market review wiring.
- data_pipeline/: SQLite-backed ingest → clean → feature pipeline plus optional schedulers.
- static/ and templates/: Vanilla JS UI, styling, and dashboard template.
- tests/: Regression tests for chart horizon coverage.

## Data Pipeline (download → clean → process → serve)
- data_pipeline/downloader.py: Download OHLCV via yfinance and upsert into raw_prices (skip fully blank days).
- data_pipeline/cleaning.py: Align to business days, flag anomalies (5σ moves, volume spikes, OHLC inconsistencies), forward-fill volume only.
- data_pipeline/processing.py: Build daily/weekly/month-end aggregates and derived features (returns, amplitude, HL spread, Parkinson/GK variance, volume deltas/z-scores, MAs, momentum, osc ranges) into processed_prices.
- data_pipeline/data_service.py: Facade that initializes DB and performs a 7-day refresh on every fetch (manual_update) before returning cleaned/processed frames.
- data_pipeline/scheduler.py: Optional APScheduler jobs for daily refresh (16:15) and monthly correlation refresh; controlled by env.

Environment
- MARKET_DB_PATH: SQLite path (default ./market_data.sqlite).
- AUTO_UPDATE_TICKERS: Comma-separated tickers for scheduled refresh (e.g., "AAPL,MSFT,SPY").
- SCHED_TZ: Scheduler timezone (default UTC).

Optional seeding
```python
import datetime as dt
from data_pipeline.data_service import DataService
from data_pipeline.downloader import upsert_raw_prices
from data_pipeline.cleaning import clean_range
from data_pipeline.processing import process_frequencies

DataService.initialize()
start = dt.date.today() - dt.timedelta(days=730)
end = dt.date.today()
for t in ["AAPL", "MSFT", "SPY"]:
    upsert_raw_prices(t, start, end)
    clean_range(t, start, end)
    process_frequencies(t, start, end)
```

## Running Locally
1) Python 3.8+ and pip are required.
2) Install deps:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
3) (Optional) cp .env.example .env and set PORT, FLASK_ENV, SECRET_KEY, LOG_LEVEL.
4) Launch: `python app.py` then open http://localhost:5000.

## API Surface
- GET/POST / : Renders dashboard; POST accepts ticker, start_time (YYYYMM or YYYY-MM), optional end_time, frequency (D/W/ME/QE), risk_threshold (0-100), side_bias (Natural/Neutral), and option_position JSON.
- POST /api/validate_ticker : `{ "ticker": "AAPL" }` → `{ valid: bool, message: str }`.

## Usage
- Provide start/end horizon months, frequency, and risk threshold; choose side bias.
- Add option rows (type, strike, quantity, premium) if you want P&L overlay.
- Run analysis to receive oscillation/return charts, volatility dynamics, correlation chart, projection table, and market review table.

## Testing
- Regression for the chart horizon fix: `python tests/test_chart_time_range.py`.

## Deployment Notes
- Netlify build config pins Python 3.11 and installs via `pip install -r requirements.txt`.
- Gunicorn example: `gunicorn --bind 0.0.0.0:8000 app:application`.

## Chart Time Range Fix (documented)
- Problem: Charts showed only the last few points when the DB lacked full coverage for the requested horizon.
- Root cause: price_dynamic accepted any DB slice without checking start-date coverage, so yfinance fallback never ran.
- Fix: coverage check plus optional `apply_horizon=False` paths so calculations can use full history while displays stay horizon-filtered. Implemented in core/price_dynamic.py and core/market_analyzer.py.
- Verify: run the test above or instantiate MarketAnalyzer with multi-year horizons and confirm counts/plots.

## License & Support
MIT License. For support or issues, open a GitHub issue.
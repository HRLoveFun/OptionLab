# Pipeline Stages Reference

Data flows through 5 stages. A failure at any stage can propagate downstream as empty/NaN data.

## Stage 1: Download (`data_pipeline/downloader.py`)

**Function**: `upsert_raw_prices(ticker, start, end)`
**Input**: Ticker symbol, date range
**Output**: `PipelineResult(ok=True, rows=N)` or `PipelineResult(ok=False, error="...")`
**Side effect**: Writes to `raw_prices` table

**What can fail**:
- yfinance returns empty DataFrame (rate-limit, invalid ticker, network error)
- Proxy unreachable (curl_cffi timeout)
- Staleness check incorrectly skips download

**Check**: `SELECT count(*) FROM raw_prices WHERE ticker=? AND date BETWEEN ? AND ?`

## Stage 2: Clean (`data_pipeline/cleaning.py`)

**Function**: `clean_range(ticker, start, end)`
**Input**: Reads from `raw_prices` table
**Output**: `PipelineResult` — writes to `clean_prices` table
**Side effect**: Adds anomaly flags (price_jump_flag, vol_anom_flag, ohlc_inconsistent)

**What can fail**:
- Source `raw_prices` has NaN-only filler rows → cleans "pass through" NaN
- `pd.to_numeric()` coerces strings to NaN silently
- Anomaly flag thresholds are heuristic — may miss or over-flag

**Check**: `SELECT date, missing_any, price_jump_flag FROM clean_prices WHERE ticker=? ORDER BY date DESC LIMIT 10`

## Stage 3: Process (`data_pipeline/processing.py`)

**Function**: `build_features(ticker, frequency)`
**Input**: Reads from `clean_prices` table
**Output**: `PipelineResult` — writes to `processed_prices` table
**Side effect**: Computes MA, returns, volatility features

**What can fail**:
- Insufficient clean data for rolling window calculations → features are NaN
- Wrong frequency conversion (D→W→M) drops rows
- `object` dtype from DB causes numpy math errors

**Check**: `SELECT date, frequency, ma_20, ma_50 FROM processed_prices WHERE ticker=? AND frequency=? ORDER BY date DESC LIMIT 5`

## Stage 4: Core Analysis (`core/price_dynamic.py`, `core/market_analyzer.py`)

**Function**: `PriceDynamic._fetch_daily_from_db()` → `MarketAnalyzer` methods
**Input**: Reads from `processed_prices` (or `clean_prices` for some features)
**Output**: DataFrames for chart generation

**What can fail**:
- `features_df` shape (0, N) — zero rows after NaN filtering → empty charts
- Missing columns cause KeyError in chart methods
- Projection creates 0 historical + 0 projection data points

**Check**: Log output `"Projection DataFrame created: X total dates, Y historical data points"`

## Stage 5: Service + Route (`services/analysis_service.py`, `app.py`)

**Function**: `AnalysisService.run_analysis()` → chart methods → base64 images
**Input**: DataFrames from core modules
**Output**: Dict with base64-encoded chart images (or None for failed charts)

**What can fail**:
- Chart method returns None → template shows empty panel
- matplotlib "categorical units" warning → dates treated as strings
- Exception caught by generic handler → chart silently becomes None

**Check**: Look for `None` values in the analysis result dict keys (price_chart, volatility_chart, etc.)

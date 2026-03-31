---
name: debug-pipeline
description: "Diagnose data pipeline failures: empty charts, stale data, yfinance errors, NaN propagation, missing ticker data. Use when analysis shows blank panels or data appears outdated."
argument-hint: "Ticker symbol or symptom description"
---

# Data Pipeline Diagnosis

Systematic workflow to trace data failures from symptom to root cause in the OptionView pipeline.

## When to Use
- Analysis shows empty/blank chart panels
- Data appears stale or outdated despite refresh
- yfinance download errors in logs (429, timeout, empty DataFrame)
- NaN values appearing in analysis results
- "No valid Osc_low-Osc_high data" or similar warnings

## Procedure

### Step 1: Identify the Symptom

Classify the user's report:
| Symptom | Likely Layer |
|---------|-------------|
| Empty chart panels | core/ (PriceDynamic) or data_pipeline/ (NaN filler rows) |
| "No data for TICKER" message | data_pipeline/downloader.py (download failed) |
| Stale prices (dates from days ago) | data_pipeline/data_service.py (cooldown blocking refresh) |
| 429 / timeout errors | yfinance rate-limiting or proxy issue |
| Wrong values in analysis | data_pipeline/cleaning.py or processing.py |

### Step 2: Check DB State

Query the database for the target ticker using the terminal:
```sql
-- Check raw_prices for recent data
SELECT ticker, date, close FROM raw_prices WHERE ticker='{TICKER}' ORDER BY date DESC LIMIT 5;

-- Check for NaN-only filler rows (the root cause of empty charts)
SELECT count(*) FROM raw_prices WHERE ticker='{TICKER}' AND open IS NULL AND high IS NULL AND low IS NULL AND close IS NULL;

-- Check clean_prices status
SELECT ticker, date, missing_any, price_jump_flag FROM clean_prices WHERE ticker='{TICKER}' ORDER BY date DESC LIMIT 5;

-- Check processed_prices
SELECT ticker, date, frequency FROM processed_prices WHERE ticker='{TICKER}' ORDER BY date DESC LIMIT 5;
```

### Step 3: Check yfinance Connectivity

```python
import os, yfinance as yf
from utils.utils import yf_throttle

# Check proxy
print("HTTP_PROXY:", os.environ.get("HTTP_PROXY", "(not set)"))
print("HTTPS_PROXY:", os.environ.get("HTTPS_PROXY", "(not set)"))

# Test download
yf_throttle()
df = yf.download("{TICKER}", period="5d", progress=False)
print(f"Shape: {df.shape}")
print(df.tail() if not df.empty else "EMPTY - download failed")
```

### Step 4: Trace the Data Flow

Follow the data through each stage, checking for where it breaks. See [pipeline stages reference](./references/pipeline-stages.md) for expected inputs/outputs at each stage.

1. **downloader.py** → `upsert_raw_prices()` → writes to `raw_prices`
2. **cleaning.py** → `clean_range()` → reads `raw_prices`, writes to `clean_prices`
3. **processing.py** → `build_features()` → reads `clean_prices`, writes to `processed_prices`
4. **core/price_dynamic.py** → `_fetch_daily_from_db()` → reads `processed_prices`
5. **core/market_analyzer.py** → uses PriceDynamic features for charts
6. **services/analysis_service.py** → calls chart methods, returns base64 images

### Step 5: Identify Root Cause

Common root causes:
| Root Cause | Evidence | Fix |
|-----------|----------|-----|
| NaN-only filler rows from failed download | `raw_prices` has NULL in all price columns | Re-download with `yf_throttle()`, delete filler rows |
| 60s cooldown blocking retry | Download skipped, log says "No new data" | Wait 60s or reset cooldown in `DataService._ticker_locks` |
| Proxy unreachable | `curl: (28) Operation timed out` | Check `YF_PROXY` in `.env`, verify proxy is running |
| yfinance 429 rate limit | `YFRateLimitError` in logs | Wait 30s, ensure `yf_throttle()` is called everywhere |
| `features_df` shape (0, N) | 0 historical data points in projection log | Check `_fetch_daily_from_db()` NaN row filtering |

### Step 6: Suggest Fix + Test

After identifying root cause:
1. Propose a minimal code fix
2. Generate a test case that reproduces the failure
3. Verify the fix prevents NaN propagation downstream

### Step 7: Record Diagnosis

Update the failure registry so the system learns from this diagnosis:

1. Open `.github/data/failure-registry.yaml`
2. Find the matching pattern (e.g., `nan-propagation`, `yfinance-error`)
3. Update:
   - Increment `times_seen`
   - Set `last_seen` to current ISO timestamp
   - If this is a new root cause variant, update `resolution_note`
4. If `times_seen` reaches 3+ for the same pattern, recommend an **architectural fix** rather than another point fix. The pattern indicates a systemic issue that needs structural change.

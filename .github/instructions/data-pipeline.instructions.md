---
description: "Use when editing data pipeline code: downloader, cleaning, processing, DB access, or data_service modules."
applyTo: "data_pipeline/**"
---

# Data Pipeline Rules

## DB Access
- Always use `get_conn()` context manager from `data_pipeline/db.py` — never raw `sqlite3.connect()`
- Use `fetch_df()` for reads, `upsert_many()` for writes
- Convert DB-sourced columns with `pd.to_numeric(col, errors='coerce')` before any math — SQLite returns `object` dtype

## yfinance Calls
- Call `yf_throttle()` from `utils/utils.py` **before every** `yf.download()` or `yf.Ticker()` invocation
- Check for empty DataFrame immediately after download: `if df is None or df.empty: return`
- Never pass `requests.Session` to yfinance — it uses `curl_cffi` internally
- Proxy is set via `HTTP_PROXY`/`HTTPS_PROXY` env vars (handled by `init_yf_proxy()` at startup)

## Return Values
- Every pipeline stage (download/clean/process) must return a `PipelineResult` from `data_pipeline/__init__.py`
- Set `result.ok = False` and `result.error = "message"` on failure — never return bare `False` or `None`
- Non-fatal issues go in `result.warnings.append("message")`

## Error Handling
- Use specific exception types: `sqlite3.OperationalError`, `ValueError`, `KeyError` — not bare `except Exception`
- Log with `logger.error("...", exc_info=True)` for unexpected errors
- Transient failures (network, 429) should be retryable — don't set permanent error state

## Data Integrity
- NaN-only filler rows must not propagate — drop rows where ALL price columns are NaN before upserting
- Validate that price values are positive after `pd.to_numeric()` conversion
- The staleness check (DB-first pattern) uses `fetch_df()` to skip redundant downloads — preserve this pattern

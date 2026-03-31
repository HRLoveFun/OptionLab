---
description: "Use when modifying code that calls yfinance, Yahoo Finance, yf.download, yf.Ticker, fast_info, option_chain, or handles rate-limiting and proxy configuration."
---

# yfinance Safety Rules

## Rate Limiting
- Call `yf_throttle()` from `utils/utils.py` before **every** yfinance API call (download, Ticker, fast_info)
- `yf_throttle()` enforces a 1.5-second minimum gap between calls with a global threading lock
- Missing throttle calls cause HTTP 429 (Too Many Requests) — Yahoo aggressively rate-limits

## Proxy
- yfinance >= 0.2.50 uses `curl_cffi` internally — **never** pass `requests.Session()` as session parameter
- Proxy is configured via env vars: `HTTP_PROXY` / `HTTPS_PROXY` (set by `init_yf_proxy()` at startup)
- `init_yf_proxy()` reads `YF_PROXY` from `.env` and TCP-probes the proxy before setting env vars

## Empty Data Handling
- After any yfinance call, immediately check: `if df is None or df.empty:`
- Empty DataFrames from failed downloads can create NaN-only filler rows in cleaning stage
- NaN-only rows propagate through: cleaning → processing → DB → PriceDynamic → empty charts
- **Always** validate data is non-empty before passing downstream

## curl_cffi Specifics
- Timeout errors show as `curl: (28) Operation timed out` — this is curl_cffi, not requests
- SSL errors may differ from requests-based code — don't assume `requests.exceptions.*`
- `YFRateLimitError` is the specific exception for 429 responses

## Pattern: DB-First
```python
# Check DB cache before downloading
existing = fetch_df("SELECT MAX(date) ... WHERE ticker=?", (ticker,))
if recent_enough(existing):
    return  # skip download
yf_throttle()  # always throttle before yfinance call
df = yf.download(...)
```

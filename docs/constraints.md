# Project Constraints

> **Audience**: humans and AI code reviewers. Read this before suggesting refactors.
> Items here are **deliberate** — not bugs, not tech debt. Changing them requires an ADR (see [docs/decisions/](decisions/)).

This document lists external/historical constraints that shape the codebase.
When you see code that looks "weird", check here first; what looks like an anti-pattern
is usually a workaround for one of the items below.

---

## 1. yfinance is the only data source

- **Constraint**: This is a personal-use research tool. We do not pay for Bloomberg / Polygon / Tradier.
- **Implications**:
  - No SLA, no support, no stable schema. yfinance can break on any release.
  - Aggressive rate limiting (HTTP 429) — see §2.
  - **No option-chain history.** `yf.Ticker(...).option_chain(expiry)` only returns the *current snapshot*. There is no API for yesterday's IV smile, last week's OI profile, or 252-day IV history.
  - Therefore: **no IV rank / IV percentile / option backtests** are promised anywhere in this project from yfinance data alone. Use **HV percentile** as the substitute (see [glossary.md](glossary.md)).

## 2. yfinance rate limits & curl_cffi quirks

- yfinance >= 0.2.50 uses **`curl_cffi`** internally, NOT `requests`.
- **Do NOT pass `session=requests.Session()`** to any yfinance call — it silently fails to make the request.
- Proxy must be set via `HTTP_PROXY` / `HTTPS_PROXY` env vars; we read `YF_PROXY` and propagate to both. See [utils/network.py](../utils/network.py) `init_yf_proxy`.
- **Dead-proxy poisoning**: an unreachable proxy makes curl_cffi hang. We TCP-probe before activating; falls back to direct connect.
- **Global throttle**: token-bucket limiter (default 5 req/s, burst 5) in [utils/network.py](../utils/network.py)::`yf_throttle`. Every yfinance call MUST be routed through `data_pipeline/yf_client.py` (the single chokepoint) rather than calling `yf_throttle()` directly at each call site — see ADR 0005.
- **DB-first pattern**: never re-download data already in `clean_prices`. The 60-second cooldown in `DataService` exists to prevent thundering herd from concurrent UI requests.
- **Single yfinance exit point**: only `data_pipeline/yf_client.py` may `import yfinance`. Any other module needs a `# doc-guard: allow=single-yf-exit` marker, which is tracked as architecture debt (see [architecture_review.md](architecture_review.md) §2). Enforced by `scripts/doc_guard.py` rules `single-yf-exit`, `import-direction`, `core-purity` and `db-access`; trend-gated in CI by `scripts/arch_metrics.py --check`.

## 3. SQLite, single-machine deployment

- **Constraint**: this app runs on one developer machine, occasionally a small VPS. Postgres is overkill.
- **WAL mode + `synchronous=NORMAL`**: chosen for read concurrency. Do not switch to `FULL` (latency) or remove WAL (locks block reads during scheduler writes).
- **Thread-local connections** (`data_pipeline/db.py`): SQLite connections are not thread-safe to share, but per-query reconnects are wasteful. We cache one connection per (thread, path) and apply PRAGMAs once.
- **No migration framework**: schemas are created via `CREATE TABLE IF NOT EXISTS`. Breaking changes require manual `.sqlite` migration scripts in `scripts/`.

## 4. The machine is not 24/7

- Snapshot cadence (scheduler) **will have gaps**: laptop sleeps, weekends off, network outages.
- Any feature that consumes time-series data must tolerate **sparse, non-contiguous days**. Do NOT assume daily continuity.
- `data_pipeline/cleaning.py` aligns to business days and marks missing days as NA — **no interpolation**, by design. Filling gaps would invent prices that didn't trade.

## 5. Financial domain "magic numbers" are intentional

These are NOT magic numbers — they encode domain knowledge. Do not "DRY" them into a shared config without checking with the author:

- **MA windows**: 10 / 20 / 50 / 200 — industry-standard, used by every chartist.
- **Oscillation lookbacks**: 14 (RSI), 20 (BB), 12/26/9 (MACD) — Wilder/Bollinger/Appel originals.
- **HV window**: 30 trading days — common short-term realised-vol horizon.
- **Sigma threshold**: `5 * std` for price-jump anomaly flag — empirically tuned for US equities.
- **Greeks bounds**: `_SIGMA_MIN=0.001`, `_SIGMA_MAX=20.0` — filters yfinance IV anomalies (yfinance occasionally returns 999.x for illiquid strikes).
- **`_T_MIN = 1/365`**: avoids divide-by-zero on expiry day.

## 6. Computation must finish in one HTTP request

- **No background job queue** (no Celery, no RQ). The Flask process serves the UI and runs the scheduler in-thread.
- **APScheduler is optional and lazily imported.** The scheduler only starts when `AUTO_UPDATE_TICKERS` is set, and `data_pipeline/scheduler.py` imports APScheduler inside `UpdateScheduler.__init__` (plus a lazy `CronTrigger` import) so the rest of the app — and `acquire_scheduler_lock`'s unit tests — run without the package installed. **Do not move that import back to module scope**: an optional feature must not become a hard startup dependency.
- Long-running computations either:
  - Run inside a request and respond synchronously (fine for <2s), or
  - Are pre-computed by the scheduler and read from DB.
- **Vectorised numpy for Greeks** (`core/options/greeks/black_scholes.py`): scipy.optimize per-contract is 30x slower on 5000-contract chains.

## 7. Frontend: vanilla JS only

- **Constraint**: keep the frontend dependency-free. No React/Vue/Svelte build step.
- ES modules + native `customElements` where state is needed.
- Charts are server-side base64 PNGs (matplotlib via `services/market/charts.py`) to avoid shipping a charting library.

## 8. Chinese is the user-facing language

- Code, comments, identifiers, log messages: **English**.
- Template strings, error messages shown to users, chart titles: **may be Chinese**.
- Don't "translate" Chinese in templates.

## 9. Inbound rate limiting is dependency-free

- There is exactly **one** inbound limiter: [utils/rate_limit.py](../utils/rate_limit.py). The global per-IP budget is installed as a `before_request` hook via `install(app)`; per-endpoint budgets (e.g. `/api/data/seed`, `/api/regime/backfill`) call `rate_limit()` directly inside the route.
- **No third-party limiter** (`flask-limiter` was removed). It signals 429 by raising a Werkzeug `HTTPException`, which the catch-all handler in [utils/api_errors.py](../utils/api_errors.py) re-raises unchanged — so `/api/*` clients got an HTML page instead of the unified `{status, code, message}` envelope, and the frontend fell back to `code="http_429"` with an English `statusText`. Any replacement must emit the envelope itself, using `code: "rate_limited"`.
- TRADEOFF: limiter state is per-process, so under `gunicorn --workers N` the effective budget is `N × max_calls` (each worker counts independently). Accepted for a single-machine dashboard; a shared backend (Redis) is the upgrade path if it ever matters.

---

## How to remove a constraint

1. Open an ADR in `docs/decisions/` describing why the constraint no longer applies.
2. Get sign-off (from yourself, in writing — future-you will thank present-you).
3. Update this file: move the item to a "Removed" section with the ADR reference, don't delete it.

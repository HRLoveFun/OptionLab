# 0002. yfinance as Sole Market Data Source

- **Status**: Accepted
- **Date**: 2025-01-15 (retroactive)
- **Deciders**: project author

## Context

This is a personal-use research / learning tool. We need US equity OHLCV history,
current spot prices, and current option chains. We do not need: institutional-grade
quality, sub-minute data, sub-second latency, or 24/7 SLA.

## Options Considered

1. **Bloomberg Terminal / Refinitiv** — gold standard, $24k+/year. Out of scope for a personal project.
2. **Polygon.io / Tradier / Databento** — paid but reasonable ($100–$500/mo). Overkill for current usage.
3. **Alpha Vantage / Twelve Data** — free tier, but rate-limited and US-coverage gaps.
4. **yfinance** — free, scrapes Yahoo Finance, comprehensive enough for US tickers.
5. **Interactive Brokers TWS API** — would require an IBKR account; complex async client.

## Decision

Use **yfinance** as the sole data source. Centralise all calls in `data_pipeline/yf_client.py`
and `data_pipeline/downloader.py`.

## Consequences

- **Positive**: zero data cost; works out of the box.
- **Negative — accepted**:
  - No SLA. yfinance can break on any release. We pin a known-good version in `requirements.txt`.
  - Aggressive rate limiting (HTTP 429). Mitigated by token-bucket throttle (ADR 0005) and DB-first caching.
  - **No option-chain history** — `option_chain()` returns current snapshot only. This kills any feature requiring historical IV (IV rank, option backtests). See ADR 0004.
  - yfinance >= 0.2.50 uses `curl_cffi`, not `requests`. We must NOT pass `session=requests.Session()`. Documented in [docs/constraints.md §2](../constraints.md#2-yfinance-rate-limits--curl_cffi-quirks).
- Future: if the project ever leaves personal scope, revisit Polygon/Tradier (supersede this ADR).

## References

- `data_pipeline/yf_client.py`
- `data_pipeline/downloader.py`
- `.github/instructions/yfinance-safety.instructions.md`
- ADR 0004 (no IV history)
- ADR 0005 (throttle)

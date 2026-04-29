# 0005. Token-Bucket Throttle for yfinance Calls

- **Status**: Accepted
- **Date**: 2025-03-01 (retroactive — replaced earlier fixed 1.5s gap)
- **Deciders**: project author

## Context

Yahoo Finance aggressively rate-limits per-IP. Symptoms when we hit the limit:
- `YFRateLimitError` exceptions.
- Empty DataFrames returned silently.
- "Too Many Requests" in logs.
- Later: temporary IP-level cooldown (~1 hour) where everything fails.

A naive multi-ticker dashboard refresh easily fires 20+ requests in a second.

## Options Considered

1. **No throttling** — failed in practice within minutes of UI use.
2. **Fixed gap (sleep 1.5s before each call)** — what we had originally. Works but penalises legitimate small bursts (e.g. 5 parallel panels) by serialising them artificially.
3. **Token bucket** — small bursts allowed up to bucket size, then sustained rate enforced.
4. **Sliding window counter** — more complex, no benefit over token bucket here.

## Decision

Token-bucket limiter in `utils.utils.yf_throttle`:
- Refill rate: `YF_RATE_PER_SEC` (default **5 tokens/sec**).
- Burst capacity: `YF_BUCKET_SIZE` (default **5 tokens**).
- Every yfinance call (`yf.download`, `yf.Ticker`, `option_chain`, `fast_info`) must call `yf_throttle()` first.
- Thread-safe via a single `threading.Lock`.
- Layered with the **DB-first pattern**: if data exists in `clean_prices`, skip the call entirely.

## Consequences

- **Positive**: dashboard initial load (5–10 panels) completes in ~1s instead of 7.5s.
- **Positive**: sustained scheduler updates respect Yahoo's per-IP limit.
- **Trade-off**: defaults are conservative — if you run the app on a server behind a shared NAT (multiple users), reduce `YF_RATE_PER_SEC`.
- **Tested via**: `tests/test_yf_failure_injection.py`, `tests/test_concurrency.py`.

## References

- `utils/utils.py` — `yf_throttle`, `_yf_throttle_reset`
- `.github/instructions/yfinance-safety.instructions.md`
- ADR 0002 (yfinance choice)

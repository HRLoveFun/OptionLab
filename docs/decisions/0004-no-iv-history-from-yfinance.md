# 0004. No IV Rank / IV History from yfinance — Use HV Percentile

- **Status**: Accepted
- **Date**: 2025-02-10 (retroactive)
- **Deciders**: project author

## Context

A natural feature request for any options dashboard is **IV rank** ("is implied vol cheap or rich?").
The textbook formula is `(IV_today − IV_min_52w) / (IV_max_52w − IV_min_52w)`.
This requires **252 days of historical IV data**.

`yf.Ticker(t).option_chain(expiry)` returns only a **current snapshot**. There is no Yahoo Finance
endpoint exposing yesterday's IV smile, last week's OI, or the chain as of any past date.
Confirmed empirically and from yfinance source.

## Options Considered

1. **Roll our own IV history**: snapshot the chain on a schedule and persist it.
   - Pros: gives true IV rank eventually.
   - Cons: machine isn't 24/7 (see [constraints.md §4](../constraints.md#4-the-machine-is-not-247)). Snapshots will have gaps. Requires months of cadence before IV rank becomes meaningful.
2. **Pay for a chain-history API** (Polygon options, Tradier, ORATS).
   - Pros: instant, accurate.
   - Cons: cost (out of scope per ADR 0002).
3. **Substitute HV percentile for IV rank**.
   - Pros: HV history is freely available via `Ticker.history()`. No data collection lag.
   - Cons: HV is realised, IV is forward-looking. They diverge in regime changes.
4. **Show only current ATM IV without ranking**.
   - Pros: honest.
   - Cons: gives the user no "is this expensive?" answer.

## Decision

- **Primary**: use **HV percentile** (current 30-day HV ranked against its own 252-day history) as the "is vol cheap/rich" indicator.
- **Secondary**: display current ATM IV as a single-point comparison.
- **Optionally**: opportunistically snapshot chains we already query (best-effort sparse history). Treat the resulting `option_snapshots` table as gappy; queries must handle missing days.
- **Never**: claim IV rank / IV percentile in user-facing copy or in plans.

## Consequences

- **Positive**: feature works on day one with no data-collection runway.
- **Trade-off**: HV percentile and true IV rank disagree, especially around earnings / macro events. UI must label clearly.
- **Trade-off — locked in**: any future feature that *truly* needs IV history (e.g. backtesting an iron condor entered 30 days ago) is out of scope until ADR 0002 is superseded.

## References

- [docs/glossary.md](../glossary.md) — HV percentile definition
- ADR 0002 (yfinance only)
- `core/options_greeks.py`, `core/market_review.py`

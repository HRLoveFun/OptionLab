# Glossary

> Domain terms used throughout this codebase. When AI or new contributors encounter
> a term they're unsure about, check here before assuming.

## Volatility

### IV (Implied Volatility)
Forward-looking volatility implied by an option's market price via Black-Scholes inversion.
**In this project**: only available as a **current snapshot** from yfinance — see [constraints.md §1](constraints.md).

### HV (Historical / Realised Volatility)
Annualised standard deviation of close-to-close log returns.
- Window: typically 30 trading days (configurable).
- `HV = std(log(close_t / close_{t-1})) * sqrt(252)`
- Computed in `core/options_greeks.py` and `core/market_review.py`.

### IV Rank
`(current_IV - 52wk_min_IV) / (52wk_max_IV - 52wk_min_IV)` — in [0, 1].
**Not available** in this project: requires 252 days of IV history; yfinance provides none.

### IV Percentile
% of days in the past year where IV was below today's IV. Same data requirement, **not available**.

### HV Percentile (substitute for IV Rank)
HV today ranked against its own 252-day history. **This is what we use** when the UI asks "is vol cheap or rich?"

## Options

### Greeks
- **Delta**: ∂Price/∂Spot
- **Gamma**: ∂Delta/∂Spot
- **Theta**: ∂Price/∂Time (per day)
- **Vega**: ∂Price/∂σ (per 1%)
- **Rho**: ∂Price/∂r (per 1%)
- All vectorised in `core/options_greeks.py`. Scalars and NumPy arrays both supported.
- We assume **European exercise**. American early-exercise premium is ignored — acceptable for index options and short-dated equity options.

### Option Chain
The full set of calls + puts at every strike for a given expiry. yfinance returns this via `yf.Ticker(t).option_chain(expiry)` — **snapshot only**, no history.

### Mid Price
`(bid + ask) / 2`. We use mid for IV calc and PnL marking. **Beware**: when `bid == 0` (illiquid strike), mid is misleading; pre-filter before computing.

## Market Regime

### Regime
A coarse classification of market state — bullish/bearish/sideways and high/low vol.
Computed in `core/regime.py` from a basket of indicators (trend strength, vol percentile, breadth).

### Side Bias
User-supplied directional preference (Bull / Bear / Neutral) used to filter strategy suggestions.

## Data Pipeline

### `raw_prices`
Untouched OHLCV pulled from yfinance. Indexed by `(ticker, date)`.

### `clean_prices`
`raw_prices` aligned to business days, anomalies flagged, missing days = NA. **NO interpolation** — see [constraints.md §4](constraints.md#4-the-machine-is-not-247).

### Anomaly Flags
- `price_jump_flag`: |log return| > 5σ.
- `vol_anom_flag`: |Δlog volume| > 5σ.
- `ohlc_inconsistent`: low > open OR close > high (data error).

### Gap Backfill
On manual update, scan past `GAP_SCAN_DAYS` (default 30) for missing business days and download them. Capped at `MAX_AUTO_BACKFILL_DAYS` to prevent runaway downloads after a long outage.

## Architecture

### Service / Core / Pipeline
Three-layer architecture with strict import direction:
```
app.py → services/ → core/ → data_pipeline/
```
- **services/**: orchestration, formats results for routes.
- **core/**: pure computation, no Flask.
- **data_pipeline/**: download, clean, persist, query.

See [.github/copilot-instructions.md](../.github/copilot-instructions.md) for enforcement rules.

### DataService Cooldown
60-second per-ticker write lock prevents thundering-herd downloads when multiple UI panels render the same ticker simultaneously.

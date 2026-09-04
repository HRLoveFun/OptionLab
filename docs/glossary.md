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
- Computed in `core/signals/hv.py` (per-ticker rolling) and surfaced cross-ticker via `core/market_review/`.

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
- All vectorised in `core/options/greeks/black_scholes.py`. Scalars and NumPy arrays both supported.
- We assume **European exercise**. American early-exercise premium is ignored — acceptable for index options and short-dated equity options.

### Option Chain
The full set of calls + puts at every strike for a given expiry. yfinance returns this via `yf.Ticker(t).option_chain(expiry)` — **snapshot only**, no history.

### Mid Price
`(bid + ask) / 2`. We use mid for IV calc and PnL marking. **Beware**: when `bid == 0` (illiquid strike), mid is misleading; pre-filter before computing.

## Market Regime

### Regime
A coarse classification of market state — bullish/bearish/sideways and high/low vol.
Computed in the `core/regime/` package (`classify.py`, `series.py`, `models.py`) from a basket of indicators (trend strength, vol percentile, breadth).

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
app.py → routes/ → services/ → core/ → data_pipeline/
```
- **routes/**: thin HTTP blueprints (no business logic).
- **services/**: orchestration, formats results for routes.
- **core/**: pure computation, no Flask.
- **data_pipeline/**: download, clean, persist, query.

Import direction is one-way; `core/` and `data_pipeline/` must not reach back into
`services/`, `routes/` or `app.py`. See [ADR 0001](decisions/0001-three-layer-architecture.md)
and [.github/copilot-instructions.md](../.github/copilot-instructions.md) for enforcement.

### DataService Cooldown
60-second per-ticker write lock prevents thundering-herd downloads when multiple UI panels render the same ticker simultaneously.

## Features

### Simulation Tab (Expiry Payoff Simulator)
A feature (see `docs/plans/simulation_tab.md`; ADR 0007 for the public GitHub Pages variant, ADR 0008 for the server-side module) that, given spot / strikes / maturities / implied vols, simulates single-option expiration P&L across a strike × maturity × IV grid.
- **Server path**: `POST /api/simulate_expiry` → `services/options/simulation.run_simulation` → `core.options.simulation.expiry.simulate_expiry`. Pure numpy/scipy, no network; entry pricing reuses `core/options/greeks/black_scholes.greeks_vectorized`.
- **Client-side twin** (`static/sim/`) is the single source of truth for the standalone Pages build and must parity-match the Python math to 1e-6 via golden tests (`scripts/gen_sim_golden.py`). Both assume European exercise, no dividends (consistent with the Greeks note above).

### Premium Matrix Tab (Premium-Rate Grid)
A hypothetical-input calculator (no market data, no network): given `price` / `IV` / `risk-free` / `spread`, it renders a strike × DTE matrix where every cell is split into a call half and a put half, each showing the Black-Scholes price and the **premium rate** — the move the underlying must make to reach breakeven: call `(K + P − S) / S`, put `(S − K + P) / S`.
- **Engine**: `static/sim/premium_matrix.js` (pure, zero I/O, Pages-safe). Per column it precomputes `√T` / `e^(−rT)` / `σ_move`; per row it precomputes `ln(S/K)`; the put comes from put-call parity, so a cell costs two `normCdf` calls. The finished matrix is memoised per input signature.
- **DOM layer**: `static/premium_matrix.js` renders one `<table>` and drives the four visibility switches (price / premium rate / call / put) through `data-show-*` attributes — pure CSS, no recompute.
- **Axis alignment contract** (three rules, all load-bearing — breaking any one makes the grid unreadable):
  1. A `<td>` must never be a flex container. `display: flex` on a table cell removes it from the table's column layout, which stacks all 18 data columns on top of the first one. The flex lives on a `<span class="pm-pair">` inside the cell; `.pm-head-pair` is its counterpart in the header.
  2. A DTE header cell mirrors the data cell one-for-one: tenor caption + `±1σ` centred over the whole column, then a `CALL` / `PUT` pair laid out by the same flex rules as `.pm-pair`. Both the header `<th>` and the data `<td>` are padding-free so the sub-columns stay pixel-aligned.
  3. The two sticky left rails share one measured width. `width` is only a hint under `table-layout: auto`, so JS writes the real strike-column width into `--pm-sigma-left` (via a `ResizeObserver`, since the panel is `display: none` until the panel state flips to `loaded`). The `(max-width: 720px)` rule that drops the sigma rail is mirrored in JS, because `<col>` maps to columns by position and a stale `<col>` shifts the crosshair by one column.
- **Crosshair**: hovering a column tints it (via its `<col>`, so one class write beats 41); hovering never rewrites values. Clicking a column promotes it to the sigma reference and syncs the `#pm-ref-dte` select.
- **Price basis**: mid is the Black-Scholes value; the fill moves half the spread away from it (`buy` → ask, `sell` → bid). Both perspectives share the same rate formulas, so a seller's rate is always the lower one.

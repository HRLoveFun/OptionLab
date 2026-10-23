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
- We assume **European exercise**. American early-exercise premium is ignored — acceptable for index options and short-dated equity options. The one exception is the option-portfolio simulator (`core/optsim/`, ADR 0013), which can price American exercise.

### Option Chain
The full set of calls + puts at every strike for a given expiry. yfinance returns this via `yf.Ticker(t).option_chain(expiry)` — **snapshot only**, no history.

### Mid Price
`(bid + ask) / 2`. We use mid for IV calc and PnL marking. **Beware**: when `bid == 0` (illiquid strike), mid is misleading; pre-filter before computing.

### Payoff Ratio
The **Payoff Ratio** tab (formerly "Expiry Odds", ADR 0010) plots, per strike and
expiry, `max(intrinsic_at_target, 0) / premium` — a **gross** return multiple:
`0x` = the option expires worthless (whole premium lost), `1x` = breakeven
(dashed reference line on the chart), `2.5x` = 2.5× the premium back (+150% net).
`intrinsic_at_target` uses `spot × (1 ± est_move%)` as the assumed terminal
price; the long option is priced at the **ask**. **Not probability-weighted** —
a cheap far-OTM strike shows a high ratio *because* the chance of reaching the
target is low. For a probability view use `est_move` alongside IV, or the
(currently dormant) `/api/expiry_probability` touch-probability endpoint.

## Market Regime

### Regime
A coarse classification of market state — bullish/bearish/sideways and high/low vol.
Computed in the `core/regime/` package (`classify.py`, `series.py`, `models.py`) from a basket of indicators (trend strength, vol percentile, breadth).

### Side Bias
User-supplied directional preference (Bull / Bear / Neutral) used to filter strategy suggestions.

## Data Pipeline

### `raw_bars`
Untouched OHLCV pulled from a provider (yfinance today) and mapped onto the canonical schema. Indexed by `(ticker, date)`.

### `clean_bars`
`raw_bars` aligned to business days, anomalies flagged, missing days = NA. **NO interpolation** — see [constraints.md §4](constraints.md#4-the-machine-is-not-247).

### `feature_bars`
`clean_bars` resampled per frequency (D/W/ME/QE) with engineered features (returns, MA, HV, oscillation). Indexed by `(ticker, date, frequency)`.

> **Compatibility (one release)**: the pre-rename names `raw_prices` / `clean_prices` / `processed_prices` still exist as shadow tables — every write goes to both families (see `data_pipeline/store/db.py`) — so an un-migrated DB and a `git revert` of the rename keep working. See [ADR 0011](decisions/0011-pluggable-data-provider-seam.md).

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

### Option Pricing Matrix Tab
A hypothetical-input calculator (no market data, no network): given `price` / `IV` / `risk-free` / `spread`, it renders a strike × DTE matrix where every cell is split into a call half and a put half, each showing the Black-Scholes price and the **premium rate** — the move the underlying must make to reach breakeven: call `(K + P − S) / S`, put `(S − K + P) / S`.
- **Engine**: `static/sim/option_pricing_matrix.js` (pure, zero I/O, Pages-safe). Per column it precomputes `√T` / `e^(−rT)` / `σ_move`; per row it precomputes `ln(S/K)`; the put comes from put-call parity, so a cell costs two `normCdf` calls. The finished matrix is memoised per input signature.
- **DOM layer**: `static/option_pricing_matrix.js` renders one `<table>` and drives the four visibility switches (price / premium rate / call / put) through `data-show-*` attributes — pure CSS, no recompute.
- **Side**: a mutually exclusive buy / sell switch in the matrix toolbar (top-right, with the Price / Prem. rate / Call / Put switches, divided from them) — the one switch that DOES recompute, because it moves the fill off the mid by `offset = max(mid × spreadPct / 200, $0.01)`. The floor is on the spread's DOLLAR effect, not on the input: a penny is the smallest tick an option trades on, so even the 1% minimum (the legal floor of the 1–100% range) leaves the two sides one tick apart on cheap wings where 1% of the mid is below a penny (otherwise 4% of a 5-cent wing premium rounds to nothing and the switch looks broken).
- **Axis alignment contract** (three rules, all load-bearing — breaking any one makes the grid unreadable):
  1. A `<td>` must never be a flex container. `display: flex` on a table cell removes it from the table's column layout, which stacks all 18 data columns on top of the first one. The flex lives on a `<span class="opm-pair">` inside the cell; `.opm-head-pair` is its counterpart in the header.
  2. A DTE header cell mirrors the data cell one-for-one: tenor caption + `±1σ` centred over the whole column, then a `CALL` / `PUT` pair laid out by the same flex rules as `.opm-pair`. Both the header `<th>` and the data `<td>` are padding-free so the sub-columns stay pixel-aligned.
  3. The two sticky left rails share one measured width. `width` is only a hint under `table-layout: auto`, so JS writes the real strike-column width into `--opm-sigma-left` (via a `ResizeObserver`, since the panel is `display: none` until the panel state flips to `loaded`). The `(max-width: 720px)` rule that drops the sigma rail is mirrored in JS, because `<col>` maps to columns by position and a stale `<col>` shifts the crosshair by one column.
- **Sigma reference**: the column the row-header σ multiple is computed for — the one closest to 30D (`REF_DTE_DEFAULT`) by default. There is no `select`: clicking anywhere in a column (data cell or header) picks it; from a focused header (`tabindex="0"`), Enter / Space activate and ArrowLeft / ArrowRight walk the date axis with roving focus, clamped at the edges. The picked header carries `aria-current="true"` plus a persistent `.is-ref` mark on both the `<col>` and the `<th>`; the mark is a `box-shadow` bar, because that header is an opaque sticky mask — a translucent fill would let scrolled rows show through.
- **Crosshair**: hovering a column tints it (via its `<col>`, so one class write beats 41); hovering (or focusing) never rewrites values. Only a click, Enter / Space, or an arrow key moves the sigma reference.
- **Price basis**: mid is the Black-Scholes value; the fill moves off it by `max(mid × spreadPct / 200, $0.01)` (`buy` → ask, `sell` → bid). Both perspectives share the same rate formulas, so a seller's rate is always the lower one.

### Option Portfolio Simulator (optsim)
A pure-computation package (`core/optsim/`, ADR 0013) that revalues a multi-leg position on a spot × day × IV-shift grid and reports value, P&L, position Greeks and margin. The package itself reads no market data. Two entry points share it: the CLI (`scripts/optsim.py`, hypothetical inputs from TOML — examples in `docs/optsim/examples/`) and the **Position Simulator** tab (`static/optsim.js` → `POST /api/optsim` → `services/options/optsim.py`), whose grid is trimmed to stay interactive (at most 8 evenly spaced date slices plus every expiry, IV shifts at entry only, a 100-step tree for American legs). Status and roadmap: `docs/plans/optsim.md`.
- **Market (Hypothetical / Ticker)**: the tab's switch for where the market inputs come from. *Hypothetical* prices on typed inputs (spot and a parametric smile). *Ticker* takes spot, listed expiries and strikes, and each leg's IV from the option chain of the header ticker (yfinance, through the 15-minute option-chain preload cache): a leg's DTE snaps to the nearest listed expiry and its strike to the nearest listed strike, and its IV is implied from the contract's bid/ask mid (or read off that expiry's IV curve when there is no two-sided quote). Ticker mode also takes the risk-free rate from the 13-week Treasury bill (`^IRX` on Yahoo, quoted in percent; the typed rate only when it is unavailable), sets the dividend yield to 0, and picks the margin class from the underlying's type: named high-cap broad indexes and their ETFs (SPX, NDX, SPY, QQQ, …) → broad index / broad-index ETF, IWM-type ETFs and other indexes → other broad index, any other ETF, stock or unknown type → single stock.
- **Break-even IV**: per leg, the implied volatility at which the leg is still worth its entry premium on a later day and spot — above it the leg is worth more than it cost, below it less. Searched between 0.5% and 300%; at expiry it collapses to the spot `strike ± premium`. Not the same quantity as the break-even *realized* volatility `σ_BE` in `docs/plans/optsim_design.md` §3.2.
- **Exercise style**: `european` (Black-Scholes-Merton with a dividend yield) or `american` (CRR binomial tree with a European control variate — 200 steps in the CLI, 100 in the tab); one switch for the whole position.
- **Sticky-strike**: every leg keeps its own IV as spot and time move; IV scenarios are parallel shifts in vol points.
- **BPR (buying-power reduction)**: the capital a position ties up beyond the premium it received — the unit both margin regimes report in.
- **Reg-T**: strategy-based margin, reported as BPR (the premium received is netted out). Naked short = max(15% (broad indexes, their ETFs and other broad indexes) or 20% (equity) of spot − OTM amount, a 10% floor — of spot for calls, of the strike for puts); a spread or condor = largest expiry loss − net credit. A long covers a short of the same type only if it expires no earlier, so a reverse calendar (short far, long near) is margined as a naked short plus the long.
- **PM (portfolio margin)**: risk-based; the worst loss over the unshocked point plus 10 spot shocks, 5 equidistant on each side (−8%/+6% for broad indexes and their ETFs, ±10% for other broad indexes, ±15% for equities), floored at $0.375 × multiplier per contract (a floor capped at the position's value when every leg is long). A proxy for OCC TIMS without vol shocks or broker add-ons.

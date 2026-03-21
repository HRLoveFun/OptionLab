# Market Dashboard — User Guide

This guide explains every tab in the Market Dashboard, covering the concepts, formulas, and interpretation of each analytical component.

---

## Table of Contents

1. [Parameter](#1-parameter)
2. [Market Review](#2-market-review)
3. [Statistical Analysis](#3-statistical-analysis)
4. [Assessment & Projections](#4-assessment--projections)
   - [Oscillation Projection](#41-oscillation-projection)
   - [Position Sizing](#42-position-sizing)
   - [Options Portfolio P&L](#43-options-portfolio-pl)
5. [Option Chain](#5-option-chain)
6. [Volatility Analysis](#6-volatility-analysis)
   - [Key Metrics](#61-key-metrics-snapshot)
   - [Volatility Premium Context](#62-volatility-premium-context)
7. [Odds](#7-odds)

---

## 1. Parameter

The **Parameter** tab is the control panel for all analyses. Configure your inputs here before running.

### Input Fields

| Field | Description | Default |
|---|---|---|
| **Ticker Symbol** | Yahoo Finance ticker (e.g., `AAPL`, `^SPX`, `GC=F`). Validated asynchronously against live data. | `^SPX` |
| **Frequency** | Time aggregation for price bars: **Daily (D)**, **Weekly (W)**, **Monthly (ME)**, **Quarterly (QE)**. | Monthly |
| **Side Bias** | Controls the projection weight direction. **Natural** — algorithm optimizes the high/low weight from historical data; **Neutral** — targets zero directional bias. | Neutral |
| **Time Horizon** | Start month (required) and end month (optional). Determines the analysis window. If end month is omitted, data extends to the latest available date. | Past 5 years to present |
| **Risk Threshold (%)** | Percentile used for oscillation-based projections and rolling envelopes (0–100). Higher values widen the projected range. | 90 |
| **Rolling Window (periods)** | Number of historical periods used to compute rolling percentile projections in the Return-Oscillation chart. | 120 |

### Position Sizing (Optional)

Expand the **Position Sizing** accordion to configure capital-aware risk management:

| Field | Description | Default |
|---|---|---|
| **Account Size ($)** | Total account equity in USD. Must be a positive number (max $1 billion). | *(empty — sizing disabled)* |
| **Max Risk per Trade (%)** | Maximum percentage of account equity to risk on a single trade (0.1 – 20%). | 2.0 |

When both fields are provided, the system calculates the maximum number of contracts you can trade while staying within your risk budget. Results appear in the **Assessment** tab.

### Option Positions (Optional)

Add rows to define an options portfolio for P&L analysis:

| Column | Description |
|---|---|
| **Type** | `SC` (Short Call), `SP` (Short Put), `LC` (Long Call), `LP` (Long Put) |
| **Strike** | Strike price of the option contract |
| **Quantity** | Number of contracts (positive integer) |
| **Premium** | Option premium per contract |

> Form state is automatically saved to browser `localStorage` and restored on revisit.

---

## 2. Market Review

The **Market Review** tab displays a cross-asset comparison table anchored to the ticker you selected. It benchmarks your instrument against major global assets.

### Benchmark Universe

| Label | Ticker | Description |
|---|---|---|
| USD | `DX-Y.NYB` | US Dollar Index |
| US10Y | `^TNX` | US 10-Year Treasury Yield |
| Gold | `GC=F` | Gold Futures |
| SPX | `^SPX` | S&P 500 Index |
| CSI300 | `000300.SS` | CSI 300 (China A-Share) |
| HSI | `^HSI` | Hang Seng Index |
| NKY | `^N225` | Nikkei 225 |
| STOXX | `^STOXX` | EURO STOXX |

### Metrics

The table is organized into four metric groups across four time periods (**1M**, **1Q**, **YTD**, **ETD**):

#### Return

Period return calculated as:

$$R_{t_0 \to t_1} = \frac{P_{t_1}}{P_{t_0}} - 1$$

where $P_{t_0}$ is the price at period start and $P_{t_1}$ is the price at period end.

For the **ETD** (Extreme-to-Date) column, return is measured from the most recent price extreme (local high or low) to the current price, reflecting the magnitude of the ongoing move.

#### Volatility

Annualized historical volatility from daily returns:

$$\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252}$$

where $\sigma_{\text{daily}}$ is the standard deviation of daily percentage returns in each period.

#### Correlation

Pearson correlation of daily returns between the target instrument and each benchmark:

$$\rho_{X,Y} = \frac{\text{Cov}(R_X, R_Y)}{\sigma_{R_X} \cdot \sigma_{R_Y}}$$

Values range from $-1$ (perfect inverse) to $+1$ (perfect co-movement).

### Visual Enhancements

- **Inline bars** — Each cell shows a tiny bar whose length is proportional to the value within the column, providing an at-a-glance heatmap.
- **Sortable headers** — Click any sub-column header to sort ascending/descending.

---

## 3. Statistical Analysis

The **Statistical Analysis** tab provides scatter plots, dynamics charts, and rolling correlation studies.

### 3.1 Oscillation vs Returns Scatter

A joint distribution scatter plot with marginal histograms.

**Oscillation** (on-effect) measures the total bar range relative to the previous close, capturing the price swing inclusive of any overnight gap:

$$\text{Oscillation} = \frac{\max(H_t,\, C_{t-1}) - \min(L_t,\, C_{t-1})}{C_{t-1}} \times 100\%$$

where $H_t$ is the period high, $L_t$ is the period low, and $C_{t-1}$ is the prior period's close.

**Returns** measure the close-to-close percentage change:

$$\text{Return}_t = \frac{C_t - C_{t-1}}{C_{t-1}} \times 100\%$$

**Chart Features:**
- **Orange dots**: All historical data points.
- **Red dots + labels**: Top 5 periods by the x-axis metric (highest oscillation values), labeled with date.
- **Blue dots + labels**: Most recent 5 periods, labeled with month.
- **Purple dots**: Periods that appear in both the top 5 and most recent 5.
- **Dashed lines**: 20th, 40th, 60th, and 80th percentiles for both axes.
- **Marginal histograms**: Distribution of each axis with fixed-width bins.
- **Percentile annotations**: The histogram panels show the percentile rank of the latest data point.
- **In-chart table** — A small "Stronger Osc" analysis table (upper-left) quantifying:
  - **Overall**: Periods where historical oscillation ≥ current oscillation — count, frequency, and median return.
  - **Risk**: Subset of "Overall" where the historical return was also at least as extreme in the same direction as the current return — count, frequency, and median return.

### 3.2 High-Low Scatter

A scatter plot of **Osc_low** (x-axis) vs **Osc_high** (y-axis) with marginal histograms:

$$\text{Osc\_high}_t = \frac{H_t}{C_{t-1}} - 1 \quad (\times 100\%)$$

$$\text{Osc\_low}_t = \frac{L_t}{C_{t-1}} - 1 \quad (\times 100\%)$$

The five periods with the largest spread ($\text{Osc\_high} - \text{Osc\_low}$) are highlighted and labeled.

**Interpretation**: This plot reveals the asymmetry between upside and downside intraperiod moves. A tight clustering along the diagonal suggests balanced high/low oscillation; a skew toward one axis implies directional bias in intraperiod volatility.

### 3.3 Return-Oscillation Dynamics

A time-series line chart showing **Returns**, **Osc_high**, and **Osc_low** over the selected horizon, overlaid with rolling percentile projections.

**Rolling Projection**:

For each period $t$, the projection is the $p$-th percentile of the preceding $W$ observations:

$$\text{HighProj}_t = Q_p\bigl(\{\text{Osc\_high}_{t-W}, \ldots, \text{Osc\_high}_{t-1}\}\bigr)$$

$$\text{LowProj}_t = Q_{1-p}\bigl(\{\text{Osc\_low}_{t-W}, \ldots, \text{Osc\_low}_{t-1}\}\bigr)$$

where $W$ is the Rolling Window parameter and $p = \text{Risk Threshold} / 100$.

These rolling envelopes (dashed green/red lines) outline the expected upper and lower oscillation bounds based on recent history. The legend shows the latest projection value marked with `*`.

### 3.4 Volatility Dynamics

A dual-axis chart combining:

- **Left axis (log scale)**: Price trajectory segmented into bull/bear phases.
  - Bull segment (green): Price ≥ 80% of cumulative max.
  - Bear segment (red): Price < 80% of cumulative max.
- **Right axis (linear)**: Rolling annualized volatility.

$$\sigma_{\text{rolling}} = \text{Std}(r_{t-w}, \ldots, r_t) \times \sqrt{252} \times 100$$

where $w$ is the volatility window (D:5, W:5, ME:21, QE:63 trading days).

A purple dot marks the current (latest) volatility level.

### 3.5 Correlation Dynamics

A consolidated rolling correlation chart with four series:

| Series | Color | Definition |
|---|---|---|
| **Consecutive Returns (1Y)** | Blue solid | $\text{Corr}(r_t, r_{t-1})$ over 1-year rolling window |
| **Consecutive Returns (5Y)** | Light blue dashed | $\text{Corr}(r_t, r_{t-1})$ over 5-year rolling window |
| **High-Low Corr (1Y)** | Orange solid | $\text{Corr}(\text{Osc\_high}_t, \text{Osc\_low}_t)$ over 1-year rolling window |
| **High-Low Corr (5Y)** | Light orange dashed | $\text{Corr}(\text{Osc\_high}_t, \text{Osc\_low}_t)$ over 5-year rolling window |

**Returns** are converted to log returns for autocorrelation: $r_t = \ln(1 + R_t)$.

Rolling window sizes adapt to frequency:

| Frequency | 1-Year Window | 5-Year Window |
|---|---|---|
| Daily | 252 | 1260 |
| Weekly | 52 | 260 |
| Monthly | 12 | 60 |
| Quarterly | 4 | 20 |

**Interpretation**:
- **Return autocorrelation** near zero suggests a random walk (efficient market); persistent positive or negative values indicate momentum or mean-reversion tendencies.
- **High-Low correlation** measures how coordinated intraperiod extremes are. High positive correlation means highs and lows tend to move together (large uniform bars); low or negative correlation suggests one extreme is independent of the other.

---

## 4. Assessment & Projections

The **Assessment & Projections** tab generates forward-looking estimates and options P&L analysis.

### 4.1 Oscillation Projection

Projects next-period price bounds using historical oscillation statistics.

#### Step 1: Projection Volatility

$$V_{\text{proj}} = Q_p(\text{Oscillation}_{\text{all}})$$

where $p$ is the Risk Threshold (e.g., 90th percentile) and the oscillation series uses the entire historical dataset.

#### Step 2: High/Low Weight

Depending on Side Bias:

- **Natural bias**: A **walk-forward** procedure splits the historical data into a training set (first 70%) and an out-of-sample (OOS) validation set (last 30%). The algorithm grid-searches over weights $w \in [0.3, 0.7]$ using the training set to maximize the hit rate, then evaluates the chosen weight on the held-out validation set:

$$w^* = \arg\max_w \;\frac{1}{N_{\text{train}}}\sum_{t=1}^{N_{\text{train}}} \mathbf{1}\bigl[C_t \in [\text{ProjLow}_t,\, \text{ProjHigh}_t]\bigr]$$

  The OOS hit rate is displayed in the projection chart's info box (e.g., "OOS Hit 78.5% (Train 840 / Valid 360)"), providing transparency on the model's true forward-looking accuracy and guarding against overfitting.

- **Neutral bias**: Grid-search over $w \in [0.4, 0.6]$ to minimize the net directional bias:

$$\text{Bias} = \frac{\#\text{Above} - \#\text{Below}}{N}$$

#### Step 3: Projected Bounds

For the **current period** (anchored at previous close $C_{t-1}$):

$$\text{ProjHigh}_{\text{cur}} = C_{t-1} \times \left(1 + \frac{V_{\text{proj}}}{100} \times w\right)$$

$$\text{ProjLow}_{\text{cur}} = C_{t-1} \times \left(1 - \frac{V_{\text{proj}}}{100} \times (1 - w)\right)$$

For the **next period** (anchored at current close $C_t$):

$$\text{ProjHigh}_{\text{next}} = C_t \times \left(1 + \frac{V_{\text{proj}}}{100} \times w\right)$$

$$\text{ProjLow}_{\text{next}} = C_t \times \left(1 - \frac{V_{\text{proj}}}{100} \times (1 - w)\right)$$

#### Projection Chart

The chart displays business-day granularity:
- **Green circles**: Daily close prices.
- **Purple triangles (▲) + line**: Daily highs.
- **Blue triangles (▼) + line**: Daily lows.
- **Red hollow circles**: Current-period projected high/low envelope (expanding along a $\sqrt{t}$ diffusion path).
- **Orange hollow circles**: Next-period projected high/low envelope.

The inset text box shows the Threshold, projected Volatility, Bias configuration, and (for Natural bias) the **OOS hit rate** with train/validation split sizes.

#### Projection Table

A detailed table showing daily values for Close, High, Low, and both current and next-period projected bounds (iHigh, iLow, iHigh1, iLow1).

### 4.2 Position Sizing

When **Account Size** and **Max Risk per Trade** are configured in the Parameter tab, the Assessment section includes a **Position Sizing** card that calculates how many contracts you can trade while staying within your risk budget.

#### Calculation

$$\text{Max Risk (\$)} = \text{Account Size} \times \frac{\text{Max Risk \%}}{100}$$

$$\text{Max Contracts} = \left\lfloor \frac{\text{Max Risk (\$)}}{\text{Max Loss per Contract}} \right\rfloor$$

where **Max Loss per Contract** is derived from the option P&L matrix (the worst-case loss across all price scenarios).

#### Edge Cases

| Scenario | Behavior |
|---|---|
| **Unlimited risk** (e.g., naked call) | Max contracts = 0; a warning is displayed: *"Strategy has unlimited risk — position sizing not applicable"* |
| **Near-zero max loss** (e.g., deep ITM spread) | Caps at 1,000 contracts to prevent absurdly large positions |
| **Credit strategy** (net credit received) | Uses the net credit as the risk basis |
| **No option positions defined** | Position sizing section is hidden |

#### Output Fields

| Field | Description |
|---|---|
| **Max Contracts** | Maximum whole number of contracts within risk budget |
| **Max Loss / Contract** | Worst-case loss for a single contract |
| **Actual Risk ($)** | Max Contracts × Max Loss — your actual capital at risk |
| **Risk %** | Actual Risk as a percentage of account equity |
| **Warnings** | Any edge-case alerts (unlimited risk, capped contracts, etc.) |

### 4.3 Options Portfolio P&L

If option positions are defined in the Parameter tab, a P&L payoff diagram is generated.

**P&L formulas per leg at expiration:**

| Type | P&L at Price $S$ |
|---|---|
| **Long Call (LC)** | $\max(S - K, 0) \times Q - P \times Q$ |
| **Long Put (LP)** | $\max(K - S, 0) \times Q - P \times Q$ |
| **Short Call (SC)** | $P \times Q - \max(S - K, 0) \times Q$ |
| **Short Put (SP)** | $P \times Q - \max(K - S, 0) \times Q$ |

where $K$ = strike, $Q$ = quantity, $P$ = premium.

The portfolio P&L is the sum across all legs, graphed over a price range of $[0.7 \times S_{\text{current}},\; 1.3 \times S_{\text{current}}]$.

**Chart annotations:**
- Green shaded area: Profit zone.
- Red shaded area: Loss zone.
- Red dashed vertical line: Current underlying price.
- Info box: Max Profit, Max Loss, and Breakeven point(s).

#### Greeks Overlay

When option positions include DTE and IV data (available when loaded from the Option Chain), the P&L chart displays a **Greeks summary box** in the upper-right corner showing the portfolio-level (net) Black-Scholes Greeks:

| Greek | Symbol | Meaning |
|---|---|---|
| **Delta** | $\Delta$ | Sensitivity of portfolio value to a \$1 move in the underlying |
| **Gamma** | $\Gamma$ | Rate of change of Delta per \$1 move — measures convexity |
| **Theta** | $\Theta$ | Daily time decay in dollars — how much value the portfolio loses per calendar day |
| **Vega** | $\nu$ | Sensitivity to a 1-percentage-point change in implied volatility |

Greeks are computed using the **Black-Scholes model** with vectorized NumPy operations for performance:

$$\Delta_{\text{call}} = N(d_1), \quad \Delta_{\text{put}} = N(d_1) - 1$$

$$\Gamma = \frac{n(d_1)}{S \cdot \sigma \cdot \sqrt{T}}$$

$$\Theta_{\text{call}} = -\frac{S \cdot n(d_1) \cdot \sigma}{2\sqrt{T}} - r K e^{-rT} N(d_2)$$

$$\nu = S \cdot n(d_1) \cdot \sqrt{T}$$

where $d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma\sqrt{T}}$, $d_2 = d_1 - \sigma\sqrt{T}$, $N(\cdot)$ is the standard normal CDF, and $n(\cdot)$ is the standard normal PDF.

---

## 5. Option Chain

The **Option Chain** tab provides a real-time T-format options chain fetched from Yahoo Finance.

### How to Use

1. Enter a ticker in the **Parameter** tab.
2. Switch to the **Option Chain** tab and click **Load Chain**.
3. Browse expiration dates via the sub-tabs that appear.

### Table Layout (T-Format)

The chain is presented in a T-shaped layout with:

| Calls ← | Strike | → Puts |
|---|---|---|
| IV%, OI, Volume, Bid, Ask, Last, Prem | Strike Price | Prem, Last, Bid, Ask, Volume, OI, IV% |

- **IV%**: Implied volatility as a percentage.
- **OI**: Open interest (number of outstanding contracts).
- **Volume**: Trading volume for the session.
- **Bid / Ask / Last**: Best bid, best ask, and last traded price.
- **Prem**: Time value of the option — the extrinsic component of the premium.

$$\text{Prem (Call)} = \text{Last} - \max(S - K, 0)$$

$$\text{Prem (Put)} = \text{Last} - \max(K - S, 0)$$

- **ITM shading**: In-the-money rows are highlighted.
- **Spot marker**: A labeled row marks the current spot price position.

### Liquidity Score

Each option row receives a **liquidity score** (GOOD / FAIR / AVOID) based on four criteria evaluated independently for the call and put side:

| Criterion | AVOID if | FAIR if |
|---|---|---|
| **Bid-Ask Spread** | Spread > 20% of mid price | Spread > 10% of mid price |
| **Open Interest** | OI < 10 contracts | OI < 100 contracts |
| **Volume** | Volume = 0 | Volume < 10 |
| **Moneyness** | Moneyness < 0.80 or > 1.20 | — |

The worst score between the call and put side determines the row's overall score. Visual indicators:

- **AVOID** rows: Dimmed (45% opacity) with strike-through text — these contracts are illiquid and should generally be avoided.
- **FAIR** rows: Light yellow background — tradeable but check spreads before entering.
- **GOOD** rows: Default styling — adequate liquidity for most strategies.

---

## 6. Volatility Analysis

The **Volatility Analysis** tab delivers a comprehensive implied-volatility teardown from live options chain data.

### 6.1 Key Metrics Snapshot

A summary table with:

| Metric | Description |
|---|---|
| **Spot Price** | Current underlying price |
| **Nearest Expiry** | Closest expiration date |
| **Nearest ATM IV** | At-the-money implied volatility for nearest expiry |
| **25Δ Put Skew** | Difference between 25-delta put IV and 25-delta call IV: $\text{Skew}_{25\Delta} = \text{IV}_{\text{put},\,\Delta\approx0.25} - \text{IV}_{\text{call},\,\Delta\approx0.25}$ (approximated via moneyness) |
| **Term Structure Slope** | Near-term ATM IV minus second-expiry ATM IV. Positive = backwardation (higher near-term IV). |
| **PCR (Vol)** | Put/Call volume ratio for nearest expiry |
| **Expected Move** | ATM straddle cost = ATM Call Ask + ATM Put Ask |
| **Max Pain** | The strike at which total option holder losses are minimized |

### 6.2 Volatility Premium Context

Displayed as a card immediately after the Key Metrics table, the **Vol Premium** panel compares implied volatility against realized (historical) volatility to assess whether options are cheap or expensive.

| Field | Description |
|---|---|
| **ATM IV** | At-the-money implied volatility from the nearest expiry |
| **HV 10d / 20d / 60d** | Annualized historical volatility over 10, 20, and 60 trading-day windows: $\sigma_w = \text{Std}(\ln r_t) \times \sqrt{252}$ |
| **Vol Premium** | Ratio of ATM IV to 20-day HV: $\text{Premium} = \text{ATM IV} / \text{HV}_{20}$. Values > 1 indicate IV is above realized vol. |
| **HV Rank** | Percentile rank of the current 20-day HV relative to the full 252-day HV distribution (0 – 100%). |
| **Term Slope** | Ratio of 60-day HV to 10-day HV. Values > 1 indicate long-term vol exceeds short-term vol (calming regime); < 1 indicates a vol spike. |
| **Signal** | Qualitative trading signal derived from the vol premium ratio: |

**Signal logic:**

| Condition | Signal | Interpretation |
|---|---|---|
| Premium ≥ 1.2 | **Seller** | IV is rich — favor selling premium (e.g., short strangles, iron condors) |
| Premium ≤ 0.8 | **Buyer** | IV is cheap — favor buying premium (e.g., long straddles, debit spreads) |
| Premium ≤ 0.8 AND HV Rank > 70% | **Mean-reversion** | IV is cheap but HV is elevated — vol may normalize; selling HV / buying IV |
| Otherwise | **Neutral** | No clear edge — vol is fairly priced |

### 6.3 Expected Move Table

For each expiry, the table shows:

$$\text{Expected Move} = C_{\text{ATM}} + P_{\text{ATM}}$$

$$\text{Expected Move \%} = \frac{\text{Expected Move}}{S} \times 100$$

$$\text{Upper Bound} = S + \text{Expected Move}, \quad \text{Lower Bound} = S - \text{Expected Move}$$

where $C_{\text{ATM}}$ and $P_{\text{ATM}}$ are the ask prices of ATM call and put options, and $S$ is the spot price.

### 6.4 IV Smile

Plots call and put implied volatilities across strikes for the nearest expiry.

**What to look for:**
- **Symmetric smile**: Equal OTM put and call IV — typical of index options.
- **Skew (smirk)**: OTM puts have higher IV than OTM calls — reflects tail-risk hedging demand.

### 6.5 IV Term Structure

ATM put IV plotted across all available expiration dates.

- **Contango (normal)**: Near-term IV < far-term IV. Market is calm; term structure slopes upward.
- **Backwardation (inverted)**: Near-term IV > far-term IV. Elevated short-term uncertainty (e.g., earnings, events).

### 6.6 IV Surface (3D)

A three-dimensional scatter plot with:
- **X-axis**: Moneyness = $K / S$ (filtered to $[0.7, 1.3]$)
- **Y-axis**: Days to Expiry (DTE)
- **Z-axis**: Put IV (%)

Color-coded by IV level (RdYlGn colormap) showing the full volatility landscape.

### 6.7 Skew Analysis

Two sub-plots for the nearest expiry:

**Put Skew (top):**

$$\text{Put Skew}(K) = \text{IV}_{\text{put}}(K) - \text{IV}_{\text{ATM}}$$

for OTM puts (moneyness ≤ 1.0). Positive skew indicates that OTM puts carry higher IV than ATM, reflecting demand for downside protection.

**Risk Reversal (bottom):**

$$\text{RR}(K) = \text{IV}_{\text{put}}(K) - \text{IV}_{\text{call}}(K)$$

Positive values (red bars) indicate put IV exceeds call IV at that strike — bearish skew. Negative values (green bars) indicate call IV exceeds put IV — bullish skew.

The **25Δ Skew** annotation shows the approximate risk reversal at the 25-delta level.

### 6.8 OI / Volume Profile

Side-by-side bar charts for the nearest expiry:

- **Left panel**: Open Interest distribution — calls (positive, green) vs puts (negative, red) by strike.
- **Right panel**: Volume distribution — same layout.
- **Spot line** (black dashed): Current underlying price.
- **Max Pain line** (purple dotted): The strike at which total dollar losses to option holders are minimized.

$$\text{Max Pain} = \arg\min_K \sum_{i} \bigl[\max(K_i^{C} - K, 0) \times \text{OI}_i^C + \max(K - K_i^{P}, 0) \times \text{OI}_i^P\bigr]$$

### 6.9 Put/Call Ratio by Expiry

Paired horizontal bar charts showing **Volume PCR** and **OI PCR** for each expiration (up to 12).

$$\text{PCR} = \frac{\text{Put Volume (or OI)}}{\text{Call Volume (or OI)}}$$

Reference levels:
- **PCR < 0.7** (green): Bullish sentiment — more call activity.
- **0.7 ≤ PCR ≤ 1.3** (blue): Neutral.
- **PCR > 1.3** (red): Bearish sentiment — more put activity.

---

## 7. Odds

The **Odds** tab calculates the profit odds for long call and long put options across all strikes and expirations, given a target price.

### How to Use

1. Enter a ticker and click **Load Chain** to fetch the live options chain.
2. Adjust the **Target** input (as a percentage of the spot price). For example, 105 means you expect the price to reach 105% of the current spot.

### Calculation

For each option contract:

$$\text{Mid Price} = \frac{\text{Bid} + \text{Ask}}{2}$$

(Falls back to Last Price if bid/ask is unavailable.)

**Long Call Odd at strike $K$:**

$$\text{Odd}_{\text{call}} = \frac{\max(T - K,\; 0) - \text{Mid}}{\text{Mid}}$$

**Long Put Odd at strike $K$:**

$$\text{Odd}_{\text{put}} = \frac{\max(K - T,\; 0) - \text{Mid}}{\text{Mid}}$$

where $T$ is the target price.

**Interpretation:**
- Odd $> 0$: Profitable if the underlying reaches the target. Higher odds mean better reward per dollar risked.
- Odd $= 0$: Break-even.
- Odd $< 0$: Loss even if the target is reached — the premium exceeds the intrinsic payoff.

Each expiration date is rendered as a separate line on the chart, color-coded. The spot price is marked with a dashed yellow vertical line. The call chart is capped at the target + 1% for readability; the put chart floors at the target − 1%.

---

## Glossary

| Term | Definition |
|---|---|
| **ATM** | At-the-money — option whose strike equals (or is nearest to) the current spot price |
| **OTM** | Out-of-the-money — call with strike > spot, or put with strike < spot |
| **ITM** | In-the-money — call with strike < spot, or put with strike > spot |
| **IV** | Implied Volatility — the market's expectation of future volatility priced into the option |
| **HV** | Historical Volatility — realized volatility computed from observed log returns over a lookback window |
| **OI** | Open Interest — total number of outstanding (unsettled) option contracts |
| **PCR** | Put/Call Ratio — ratio of put activity to call activity |
| **DTE** | Days to Expiry — calendar days until the option contract expires |
| **Max Pain** | The underlying price at which option sellers (writers) have the least financial exposure |
| **Moneyness** | Ratio of strike to spot ($K/S$); 1.0 = ATM |
| **25Δ Skew** | Difference in IV between 25-delta put and 25-delta call, measuring volatility asymmetry |
| **Contango** | Upward-sloping term structure (far-term IV > near-term IV) |
| **Backwardation** | Inverted term structure (near-term IV > far-term IV) |
| **Delta (Δ)** | Rate of change of option price with respect to a \$1 change in the underlying |
| **Gamma (Γ)** | Rate of change of Delta per \$1 move in the underlying — measures convexity of the payoff |
| **Theta (Θ)** | Daily time decay — dollar amount the option loses per calendar day, all else equal |
| **Vega (ν)** | Sensitivity of option price to a 1-percentage-point change in implied volatility |
| **Vol Premium** | Ratio of ATM IV to 20-day HV — values > 1 mean implied vol exceeds realized vol |
| **HV Rank** | Percentile rank of current HV relative to its trailing 252-day distribution |
| **Liquidity Score** | GOOD / FAIR / AVOID rating based on bid-ask spread, open interest, volume, and moneyness |
| **Walk-Forward** | Validation method that trains on earlier data and tests on later data to avoid look-ahead bias |
| **OOS** | Out-of-Sample — the held-out validation portion of data not used during model fitting |

# Frontend Architecture

> Architecture overview of the OptionView Market Dashboard frontend.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Templating | Jinja2 (Flask) | Server-side HTML rendering |
| Styling | Vanilla CSS + Inter font | Component styling |
| Icons | Font Awesome 6 | UI icons |
| Charts | Chart.js 4 + date-fns adapter | Interactive charts |
| State | Vanilla JS (no framework) | Form persistence, tab state |

---

## Directory Structure

```
static/
├── main.js                 (59KB) Core application logic
├── market_review_chart.js  (9KB)  Market review time-series charts
└── styles.css              (30KB) Component styles

templates/
└── index.html              (48KB) Single-page application template
```

---

## Page Architecture

The application uses a **single-page template** (`index.html`) with tab-based navigation.

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  Header (site-header)                                   │
│  ├── Brand (icon + title + subtitle)                    │
│  └── Ticker Badge (when analysis active)                │
├─────────────────────────────────────────────────────────┤
│  Sidebar      │  Main Panel                             │
│  (tab-nav)    │  (tab-content)                          │
│               │                                         │
│  • Parameter  │  Tab 1: Parameter Form                  │
│  • Market     │  Tab 2: Market Review Table/Chart       │
│  • Statistics │  Tab 3: Statistical Analysis Charts     │
│  • Assessment │  Tab 4: Assessment & Projections        │
│  • Chain      │  Tab 5: Option Chain T-View             │
│  • Volatility │  Tab 6: Volatility Analysis             │
│  • Odds       │  Tab 7: Expiry Odds                     │
│  • Put Sel.   │  Tab 8: Put Option Selector             │
│               │                                         │
└───────────────┴─────────────────────────────────────────┘
```

### Tab Navigation

| Tab ID | Label | Data Source |
|--------|-------|-------------|
| `tab-parameter` | Parameter | Static form |
| `tab-summary` | 综合 (Multi-ticker summary) | `results.__综合__` |
| `tab-market-review` | Market Review | `market_review_table` |
| `tab-statistical-analysis` | Statistical Analysis | `scatter_*`, `dynamics_*` charts |
| `tab-market-assessment` | Assessment & Projections | `projection_*`, `pnl_chart` |
| `tab-option-chain` | Option Chain | `oc_chain`, `oc_*` analysis |
| `tab-options-chain` | Volatility Analysis | `oc_*` metrics and charts |
| `tab-odds` | Expiry Odds | `odds_chart` |
| `tab-game` | Put Selector | Game service output |

---

## JavaScript Modules

### 1. main.js — Core Application

**Location**: `static/main.js`

**Key Components**:

| Function/Module | Purpose |
|-----------------|---------|
| `parseTickers()` | Parse comma-separated ticker input |
| `getValidTickers()` | Extract validated tickers from input |
| `window._chainCache` | Global cache for option chain data (Module 1) |
| **Position Module** | Cascade dropdowns for options (Module 2) |
| `createPositionRow()` | Generate position input row |
| `onPositionTickerChange()` | Handle ticker selection, populate expiry |
| `onPositionExpiryChange()` | Handle expiry selection, populate strikes |
| `onPositionStrikeChange()` | Handle strike selection, auto-fill price |
| `getPositionsData()` | Serialize positions for form submission |
| **Form Management** | |
| `FormManager` | localStorage persistence for form state |
| `validateAllTickers()` | Async ticker validation with badges |
| `preloadOptionChains()` | Background fetch option chains |

**Data Flow for Position Module**:
```
User selects ticker
    ↓
onPositionTickerChange()
    ↓
Check window._chainCache[ticker]
    ↓
Populate expiry dropdown
    ↓
User selects expiry
    ↓
onPositionExpiryChange()
    ↓
Filter calls/puts by type, populate strike dropdown
    ↓
User selects strike
    ↓
onPositionStrikeChange()
    ↓
Auto-fill mid price from option dataset
```

### 2. market_review_chart.js — Time-Series Charts

**Location**: `static/market_review_chart.js`

**Purpose**: Renders interactive time-series charts for Market Review tab.

**Key Components**:
| Constant/Function | Purpose |
|-------------------|---------|
| `MR_CHART_CONFIG` | Color scheme and window sizes |
| `loadMarketReviewChart()` | Fetch data from `/api/market_review_ts` |
| `renderMarketReviewChart()` | Render Chart.js line chart |
| Mode: `return` | Cumulative returns from period start |
| Mode: `vol` | Rolling 20-day volatility |
| Mode: `corr` | Rolling correlation vs main ticker |

**Chart Features**:
- Period switching (1M / 1Q / YTD / ETD)
- Asset toggle (show/hide benchmarks)
- Tooltip with value formatting
- Responsive design

---

## CSS Architecture

**Location**: `static/styles.css`

**Organization**:
```
1. CSS Variables (colors, spacing, shadows)
2. Reset & Base
3. Layout (header, sidebar, main-panel)
4. Components (buttons, forms, cards, tables)
5. Tab System (tab-nav, tab-content)
6. Ticker Badges & Validation
7. Position Table (Module 2 styling)
8. Chart Containers
9. Responsive Utilities
```

**Design System**:
- **Primary**: `#2196F3` (blue)
- **Success**: `#4CAF50` (green)
- **Warning**: `#FF9800` (orange)
- **Danger**: `#F44336` (red)
- **Font**: Inter (300, 400, 500, 600, 700)

---

## State Management

### Form Persistence

```javascript
// FormManager pattern
FormManager.saveState()   // On form input changes
FormManager.loadState()   // On page load
FormManager.clearState()  // After successful submission
```

**Stored Keys**:
- `ticker`, `frequency`, `side_bias`
- `start_time`, `end_time`
- `risk_threshold`, `rolling_window`
- `account_size`, `max_risk_pct`
- `positions` (JSON array)

### Global State

```javascript
window._chainCache = {
  "AAPL": {
    "ticker": "AAPL",
    "spot": 213.5,
    "expiries": ["2025-04-18", ...],
    "chain": {
      "2025-04-18": {
        "calls": [{"strike": 210, "mid": 3.6, "iv": 0.22, ...}],
        "puts": [...]
      }
    }
  }
};
```

---

## API Integration

### Endpoints Called from Frontend

| Endpoint | Method | Called By | Purpose |
|----------|--------|-----------|---------|
| `/` | POST | Form submit | Main analysis |
| `/api/validate_ticker` | POST | `validateAllTickers()` | Ticker validation |
| `/api/preload_option_chain` | POST | `preloadOptionChains()` | Cache option data |
| `/api/market_review_ts` | POST | `loadMarketReviewChart()` | Time-series data |
| `/api/option_chain` | GET | (Direct link) | Raw chain JSON |
| `/api/portfolio_analysis` | POST | `runPortfolioAnalysis()` | Portfolio metrics |

---

## Multi-Ticker Mode

When multiple tickers are provided:

1. **Sidebar**: Shows ticker switcher buttons
2. **Tab "综合"**: Aggregated summary view
3. **Per-ticker tabs**: Each ticker has isolated results
4. **Position Module**: Dropdown shows all validated tickers

**JavaScript**: `switchTickerContext(ticker)` filters visible content.

---

## Key Architectural Decisions

### 1. No Frontend Framework
- **Reason**: Project scope fits vanilla JS; keeps build simple
- **Trade-off**: Manual DOM manipulation vs framework abstraction

### 2. Server-Side Rendering (Jinja2)
- **Reason**: Python/Flask backend; SEO not critical
- **Benefit**: Initial page load has all data embedded

### 3. localStorage for Form State
- **Reason**: Persist user input across refreshes
- **Limitation**: Does not sync across tabs

### 4. Global Cache Pattern
- **Reason**: Share option chain data between components
- **Location**: `window._chainCache` for cross-function access

### 5. Module Comments in JS
- **Pattern**: `/* === Module N: Description === */`
- **Purpose**: Matches `optimization_manual.md` module structure

---

## Extension Points

To add a new tab:

1. **Add sidebar button** in `index.html`:
   ```html
   <button class="tab-btn" data-tab="tab-new">
       <i class="fas fa-icon"></i>
       <span>Tab Name</span>
   </button>
   ```

2. **Add panel** in `index.html`:
   ```html
   <div class="tab-content" id="tab-new">
       <!-- Content -->
   </div>
   ```

3. **Add handler** in `main.js` if interactive.

4. **Add styles** in `styles.css` under appropriate section.

---

## Dependencies

**External (CDN)**:
- `chart.js@4` — Charting library
- `chartjs-adapter-date-fns@3` — Date adapter for Chart.js
- `font-awesome@6` — Icon library
- `fonts.googleapis.com` — Inter font family

**No npm/build step required** — all dependencies loaded via CDN.

---

## Performance Considerations

1. **Image Optimization**: Charts are base64 PNGs generated server-side
2. **Lazy Loading**: Option chains fetched on-demand via `preloadOptionChains()`
3. **Caching**: `window._chainCache` prevents duplicate API calls
4. **Debouncing**: Ticker validation waits for blur event

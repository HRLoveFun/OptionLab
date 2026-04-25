# Frontend Architecture

> Architecture overview of the OptionView Market Dashboard frontend.

---

## Technology Stack

| Layer      | Technology                    | Purpose                     |
| ---------- | ----------------------------- | --------------------------- |
| Templating | Jinja2 (Flask)                | Server-side HTML rendering  |
| Styling    | Vanilla CSS + Inter font      | Component styling           |
| Icons      | Font Awesome 6                | UI icons                    |
| Charts     | Chart.js 4 + date-fns adapter | Interactive charts          |
| State      | Vanilla JS (no framework)     | Form persistence, tab state |

---

## Directory Structure

```
static/
├── main.js                 Bootstrap, tab routing, multi-ticker switcher
├── api.js                  Thin fetch wrappers for /api/* endpoints
├── cache.js                Client-side memoisation (option chain cache, etc.)
├── eventBus.js             Pub/sub primitive used across feature modules
├── utils.js                Shared helpers (parseTickers, formatters, …)
├── option-chain.js         Option chain T-view rendering + interaction
├── position.js             Cascade dropdowns for option positions
├── market-review.js        Market review tab logic
├── market_review_chart.js  Chart.js time-series renderer
├── regime.js               Regime panel
├── game.js                 Put-selector ("game") tab
├── styles.css              Component styles + design tokens
├── state/                  Reactive store + per-feature state machines
│   ├── store.js               Tiny observable store
│   ├── panelState.js          Four-phase async state per panel
│   ├── tabFlagsState.js       Lazy-load flags per tab (avoid re-fetch)
│   ├── optionChainState.js    Selected expiry / strike / mode
│   ├── chainCacheState.js     Per-ticker option chain cache
│   ├── oddsChainState.js      Odds tab state
│   └── abortRegistry.js       AbortController registry to cancel in-flight
│                              requests when the user switches ticker
├── features/               (extension slot for future feature modules)
└── components/             (extension slot for component partials)

templates/
├── index.html              Skeleton + tab shells; rendered on POST /
└── partials/
    ├── tab_*.html          Per-tab partial (parameter, market_review, …)
    └── fragments/          HTMX fragments returned by /render/<kind>
```

---

## Streaming / Lazy-Tab Architecture

Heavy analysis no longer runs synchronously inside `POST /`. The flow is:

```
Browser ── POST / (form data) ─────────────────► Flask
                                                 │
Flask creates a JobCache entry (job_id) and immediately renders
`index.html` with `streaming_mode=True`. Each tab partial emits an
HTMX placeholder:

    <div hx-get="/render/market_review?job=…&ticker=…"
         hx-trigger="load" hx-swap="outerHTML">
      <!-- spinner / banner here -->
    </div>

Browser ◄── skeleton (≪ 1 s)

Browser fans out 4× /render/<kind> in parallel for each visible ticker:
   /render/market_review
   /render/statistical
   /render/assessment
   /render/options_chain

Flask ── compute_or_get(job_id, ticker, kind) ──► AnalysisService.*_slice
                                                  └─ memoised per (job, ticker, kind)

Flask ── HTML fragment ─────────────────────────► hx-swap="outerHTML"
```

Key files:
- `data_pipeline/job_cache.py` — in-process JobCache (TTL 90 s).
- `app.py::_render_streaming_slice` — shared `/render/<kind>` handler.
- `services/analysis_service.py::generate_*_slice` — per-tab compute.
- `templates/partials/fragments/*.html` — rendered fragments.

The browser-side HTMX library replaces each placeholder when its fragment
arrives, so users see tabs populate as their data is ready instead of
waiting for the slowest tab.

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

| Tab ID                     | Label                       | Data Source                      |
| -------------------------- | --------------------------- | -------------------------------- |
| `tab-parameter`            | Parameter                   | Static form                      |
| `tab-summary`              | 综合 (Multi-ticker summary) | `results.__综合__`               |
| `tab-market-review`        | Market Review               | `market_review_table`            |
| `tab-statistical-analysis` | Statistical Analysis        | `scatter_*`, `dynamics_*` charts |
| `tab-market-assessment`    | Assessment & Projections    | `projection_*`, `pnl_chart`      |
| `tab-option-chain`         | Option Chain                | `oc_chain`, `oc_*` analysis      |
| `tab-options-chain`        | Volatility Analysis         | `oc_*` metrics and charts        |
| `tab-odds`                 | Expiry Odds                 | `odds_chart`                     |
| `tab-game`                 | Put Selector                | Game service output              |

---

## JavaScript Modules

### 1. main.js — Core Application

**Location**: `static/main.js`

**Key Components**:

| Function/Module            | Purpose                                       |
| -------------------------- | --------------------------------------------- |
| `parseTickers()`           | Parse comma-separated ticker input            |
| `getValidTickers()`        | Extract validated tickers from input          |
| `window._chainCache`       | Global cache for option chain data (Module 1) |
| **Position Module**        | Cascade dropdowns for options (Module 2)      |
| `createPositionRow()`      | Generate position input row                   |
| `onPositionTickerChange()` | Handle ticker selection, populate expiry      |
| `onPositionExpiryChange()` | Handle expiry selection, populate strikes     |
| `onPositionStrikeChange()` | Handle strike selection, auto-fill price      |
| `getPositionsData()`       | Serialize positions for form submission       |
| **Form Management**        |                                               |
| `FormManager`              | localStorage persistence for form state       |
| `validateAllTickers()`     | Async ticker validation with badges           |
| `preloadOptionChains()`    | Background fetch option chains                |

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
| Constant/Function           | Purpose                                 |
| --------------------------- | --------------------------------------- |
| `MR_CHART_CONFIG`           | Color scheme and window sizes           |
| `loadMarketReviewChart()`   | Fetch data from `/api/market_review_ts` |
| `renderMarketReviewChart()` | Render Chart.js line chart              |
| Mode: `return`              | Cumulative returns from period start    |
| Mode: `vol`                 | Rolling 20-day volatility               |
| Mode: `corr`                | Rolling correlation vs main ticker      |

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

State is split into three layers:

1. **Form state** (`FormManager` in `main.js`) — persisted to `localStorage`
   so a refresh does not wipe ticker / window inputs.
2. **App state** (`window.appState` from `static/state/store.js`) — observable
   maps for `panels`, `tabFlags`, and per-feature slices. Components
   subscribe via `appState.<slice>.subscribe(fn)`.
3. **DOM state** — Alpine.js `x-data` islands inside partials use the
   global stores to reactively show/hide phases (`x-show="phase==='loaded'"`).

### Four-phase panel state (P2 contract)

`panelState.set(panelId, phase)` where `phase ∈ {idle, loading, loaded,
empty, error}`. The setter is the single source of truth — banners,
spinners and Alpine bindings all derive from it.

### Tab flags (lazy-load guard)

`tabFlags.has(tabId)` records "this tab has been loaded at least once".
Tab switches consult the flag to avoid re-firing `/render/<kind>` when the
fragment is already in the DOM.

### Abort registry

`abortRegistry` keeps a map from `(panel, ticker)` to an `AbortController`.
Switching ticker calls `.abort()` on the previous controller so stale
fragments do not overwrite the new ticker's data.

### Form Persistence

```javascript
FormManager.saveState()   // On form input changes
FormManager.loadState()   // On page load
FormManager.clearState()  // After successful submission
```

**Stored Keys**: `ticker`, `frequency`, `side_bias`, `start_time`,
`end_time`, `risk_threshold`, `rolling_window`, `account_size`,
`max_risk_pct`, `positions` (JSON array).

---

## API Integration

### Endpoints Called from Frontend

| Endpoint                                 | Method   | Called By                 | Purpose                             |
| ---------------------------------------- | -------- | ------------------------- | ----------------------------------- |
| `/`                                      | POST     | Form submit               | Register job, return skeleton       |
| `/render/market_review`                  | GET      | HTMX placeholder          | Market review fragment              |
| `/render/statistical`                    | GET      | HTMX placeholder          | Statistical analysis fragment       |
| `/render/assessment`                     | GET      | HTMX placeholder          | Assessment fragment                 |
| `/render/options_chain`                  | GET      | HTMX placeholder          | Volatility / options-chain fragment |
| `/api/validate_ticker`                   | POST     | `validateAllTickers()`    | Single-ticker validation            |
| `/api/validate_tickers`                  | POST     | `validateAllTickers()`    | Batch ticker validation             |
| `/api/preload_option_chain`              | POST     | `preloadOptionChains()`   | Cache option data                   |
| `/api/market_review_ts`                  | POST     | `loadMarketReviewChart()` | Time-series chart data              |
| `/api/option_chain`                      | GET      | Option-chain tab reload   | Raw chain JSON                      |
| `/api/odds_with_vol`                     | POST     | Odds tab                  | Odds + IV per expiry                |
| `/api/portfolio_analysis`                | POST     | `runPortfolioAnalysis()`  | Portfolio metrics                   |
| `/api/regime/{current,history,backfill}` | GET/POST | Regime tab                | Macro regime data                   |

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

---

## UI Design Principles

These five principles are the contract for every panel, partial and component
in the dashboard. They are encoded in CSS tokens (`static/styles.css`) and
enforced by the PR review checklist below. **When any rule conflicts with a
quick fix, the principle wins** — escalate the design instead of bending it.

### P1 — Information hierarchy is decided per panel

Every panel must declare a **primary metric** and surface it in a hero
slot at **24–32px / weight 700**. Secondary metrics live in a KPI strip
(`.kpi-strip`); tertiary detail goes into tables/charts below the fold.
This produces "one glance ⇒ one number" reading flow.

| Panel         | Primary metric (hero)            | Secondary KPI strip                   |
| ------------- | -------------------------------- | ------------------------------------- |
| Market Review | Total Return (ETD)               | Volatility (ETD), Sharpe (ETD)        |
| Option Chain  | Spot price                       | Expiry count, ATM IV (when available) |
| Regime        | Composite regime label           | VIX, SPY vs SMA, slope                |
| Assessment    | Expected odds / projection score | (panel-specific)                      |

### P2 — Four-state machine on every async surface

Async panels (option chain, regime history, market review chart) must
render exactly four phases: `idle → loading → loaded → empty|error`.
- States are mutually exclusive (`x-show` / `aria-hidden`).
- Loading state shows a `.panel-banner--loading` with `<i fa-spin>`.
- Error state uses `.panel-banner--error` and a single `--error` token.
- Empty state uses `.empty-state`, never an empty silent panel.
- The state-bearing region carries `aria-live="polite"` so screen readers
  announce transitions.

### P3 — Semantic color is locked

The four semantic tokens are reserved meanings — never reuse them for
decoration:

| Token  | CSS var                 | Reserved for                                 |
| ------ | ----------------------- | -------------------------------------------- |
| Green  | `--success` (`#10b981`) | Gains, up-trend, low risk, completed         |
| Red    | `--error` (`#ef4444`)   | Losses, down-trend, high risk, failures      |
| Blue   | `--blue` (`#3b82f6`)    | Neutral / informational accents, primary CTA |
| Orange | `--warning` (`#f59e0b`) | Caution, incomplete data, chop, elevated vol |

Tints (`*-bg`, `*-light`) follow the same semantics. Regime tokens
(`--regime-*`) compose the same four base colors and **must not be
introduced for non-regime UI**.

### P4 — Buttons and interactive elements follow one spec

- One canonical class per role: `.btn-primary`, `.btn-ghost`, `.btn-toggle`.
- Toggle groups use `.btn-group > .btn-toggle.active` for the selected state.
- Every interactive element has an accessible name — either visible text
  or an explicit `aria-label`. Icon-only buttons must declare `aria-label`.
- Disabled state is conveyed via the `disabled` attribute (Alpine binds it),
  never by visual styling alone.

### P5 — Accessibility baseline (WCAG AA, axe ≥ 95)

- Color contrast for text vs. background ≥ 4.5:1 (≥ 3:1 for ≥ 24px).
- Focus rings are visible (`:focus-visible` outline) on every interactive
  element — never `outline:none` without a replacement.
- Live regions: any DOM area whose content changes asynchronously declares
  `aria-live="polite"` (or `role="status"` for banners).
- Form controls have `<label>` or `aria-label`; tables have `<caption>` or
  `aria-label` describing their purpose.

---

## PR Review Checklist (UI changes)

Copy this into the PR description for any change touching `templates/`
or `static/styles.css` / `static/*.js` rendering DOM.

```
## UI design checklist
- [ ] P1 — Primary metric is identified and rendered at 24–32px / 700.
- [ ] P1 — Secondary metrics use `.kpi-strip` / `.kpi-card`, not ad-hoc divs.
- [ ] P2 — All four phases (idle / loading / loaded / empty|error)
        are reachable and visually distinct in the new flow.
- [ ] P2 — The async region carries `aria-live="polite"` (or `role=status`).
- [ ] P3 — Green / red / blue / orange used only for their reserved
        semantics. No decorative red/green.
- [ ] P3 — New colors come from existing CSS variables; no new hex
        literals introduced without a token.
- [ ] P4 — All buttons use `.btn-primary` / `.btn-ghost` / `.btn-toggle`.
- [ ] P4 — Every icon-only or non-text control has `aria-label`.
- [ ] P5 — Focus ring visible on every new interactive element.
- [ ] P5 — Ran axe DevTools (or equivalent): score ≥ 95, zero contrast
        warnings, zero ARIA errors.
- [ ] Visual walk-through done on the affected tab(s) at 1280px and
        1024px widths.
```

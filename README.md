# OptionLab — Market Analysis Dashboard

> L1 | 权威：项目定位、能力边界、快速开始、环境变量、Pages 部署、对外限制 | 不权威：模块与结构、批次进度、代码约定、决策理由

Flask-based market analysis dashboard with options strategy tools.
Pulls historical prices and option chains via [yfinance](https://github.com/ranaroussi/yfinance),
caches them in SQLite, and renders a streaming HTMX UI with vanilla JS state
management on top of Chart.js / Alpine.js.

**Live demo (GitHub Pages, static snapshot):** <https://hrlovefun.github.io/OptionLab/>

**Features**

- Streaming dashboard: submit a ticker and each analysis tab loads in
  parallel (`/render/<kind>` fragments) instead of one blocking POST.
- Market analysis: oscillation projection, volatility dynamics, HV/RSI/
  Bollinger signals, cross-ticker market review, regime labelling.
- Options: live chain analytics (IV smile/skew, OI profile, expected move,
  max pain, term structure), vectorised Black–Scholes Greeks, multi-leg
  strategy analysis, expiry simulation and a client-side option pricing matrix.
- Portfolio: tracked positions with live P&L and portfolio-level Greeks.
- Fully client-side tabs (Simulation, Option Pricing Matrix) also run standalone
  on GitHub Pages with zero backend.

---

## Status and known limitations

**Status:** usable, under active development by a single maintainer; no
tagged releases yet — track `main` for the current state.
**Last verified:** 2026-09-11, by cross-checking the defaults and behaviour
documented below against the current source (`app.py`, `data_pipeline/`,
`.env.example`).

Batch progress, evidence and the deferred follow-ups live in
[`STATUS.md`](STATUS.md); this section only records what the tool deliberately
does **not** do.

**Known limitations**

- **yfinance is the only live data source.** There's no fallback provider if
  Yahoo blocks or rate-limits a request; the ADR 0011 provider seam makes a
  second provider pluggable, but none is wired in yet.
- **No option-chain history.** Yahoo doesn't expose historical chains, so
  there's no IV rank/percentile or options backtesting — HV percentile is
  used as the deliberate substitute (see `docs/decisions/`, ADR 0004).
- **Proxy fallback is silent.** If `YF_PROXY` is set but unreachable, the app
  falls back to a direct connection with no user-visible warning; in regions
  where Yahoo is blocked (e.g. mainland China) this can silently degrade to
  failed data fetches instead of an obvious error.
- **SQLite only, no migration framework.** Schema changes are additive
  (`CREATE TABLE IF NOT EXISTS`); backfilling an existing DB after a schema
  change requires a one-off script (see `scripts/migrate_canonical_tables.py`).
- **The GitHub Pages demo is a frozen static snapshot** (one ticker, one
  date) — form submission is intercepted rather than fetching live data. Run
  the Flask app locally for live analysis.

---

## Quick start

### 1. Prerequisites
- Python 3.12+
- Node 18+ (only for running the JS unit tests)

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install                  # only needed for vitest / playwright
```

### 3. Configure environment

```bash
cp .env.example .env
# edit .env (DB path, optional YF_PROXY, scheduler tickers, …)
```

### 4. Run

```bash
# Dev server (autoreload)
python app.py                # http://127.0.0.1:5001
```

### 5. Verify

```bash
pytest                       # Python suite
npx vitest run               # JS unit tests
pytest tests/e2e/            # Playwright (needs pytest-playwright + chromium)
```

Full command reference (lint, e2e, doc-automation scripts): `docs/CONVENTIONS.md` §Commands.

---

## Key environment variables

See [`.env.example`](.env.example) for the full list. The most relevant ones:

| Variable | Purpose | Default |
|---|---|---|
| `MARKET_DB_PATH` | SQLite path | `./data/market_data.sqlite` |
| `YF_PROXY` | HTTP/SOCKS proxy for yfinance (curl_cffi) | `http://127.0.0.1:1087` (recommended; required behind VPN) |
| `AUTO_UPDATE_TICKERS` | Comma-separated tickers for daily backfill (requires `APScheduler`) | unset |
| `SCHED_TZ` | Timezone for scheduler cron | `UTC` |
| `JOB_CACHE_TTL` | Per-job render cache lifetime (seconds) | `90` |
| `RATE_LIMIT_DEFAULT` | Inbound per-IP request budget (`<n> per <unit>`) | `120 per minute` |
| `RATE_LIMIT_DISABLED` | Set to `1` to disable inbound throttling (tests do) | unset |

---

## Deployment — GitHub Pages

https://hrlovefun.github.io/OptionLab/ is an **identical-UI static mirror** of
this Flask app: the same `templates/index.html`, the same `static/` (CSS/JS),
the same tab interactions — users learn one UI. Only one file is Pages-only:
`site/pages-shim.js`, a fetch-level stub that answers backend endpoints with
committed snapshot fixtures. `static/` and `templates/` are never forked.

- Snapshot source of truth: `site/snapshot/snapshot.json` (NVDA analysis
  slices incl. matplotlib PNGs) + `site/fixtures/*.json` (chain, regime,
  validation, time-series). Regenerate locally with full deps + DB:
  `python scripts/build_pages_site.py --refresh-snapshot`.
- Pages artifact: `site/` (`index.html` rendered from the real templates,
  `static/` copied verbatim, legacy demo URLs kept as redirects), assembled by
  `scripts/build_pages_site.py` (CI-safe: plain Jinja2, no network/DB) and
  deployed by `.github/workflows/pages.yml`.
- **Only the inputs are committed**: `site/fixtures/`, `site/snapshot/`,
  `site/pages-shim.js`. The rendered `site/index.html`, the redirects and the
  `site/static/` copy are build artefacts and are git-ignored — keeping them in
  git used to create a shadow copy of `static/` that silently drifted (see
  [`docs/l0_architecture.md`](docs/l0_architecture.md) §5).
- The banner on the demo site states the snapshot ticker/date; the analysis
  form submit is intercepted with an explanation instead of navigating.

> Requires the repository to be **public** (free GitHub Pages). The local
> `market_data.sqlite` is excluded from the public tree (see ADR 0007).

---

## Documentation

- **New to the repo?** Start with [`STATUS.md`](STATUS.md) (where the work stands)
  and [`docs/constraints.md`](docs/constraints.md) (what you must not "fix").
- **Changing code?** [`docs/architecture.md`](docs/architecture.md) for layers and the
  request flow, [`docs/module_reference.md`](docs/module_reference.md) for per-module
  responsibilities, [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) for conventions.
- **All documents, tagged by topic and by when to read them:** [`DOC_MAP.md`](DOC_MAP.md)
  (tags find documents that never mention your keyword; still grep as well).
- **Users** of the dashboard: [`docs/guides/USER_GUIDE.md`](docs/guides/USER_GUIDE.md).

> **Heads-up for AI / new contributors**: many "magic numbers" and "weird workarounds"
> in this codebase are deliberate. Code annotated with `WHY:` / `CONSTRAINT:` /
> `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` is justified — see
> [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) §Domain constants and comment tags.

---

## License

**MIT License** — see [LICENSE](LICENSE). Copyright (c) the project author.

The code is provided "as is", without warranty of any kind. The simulation math
(Black–Scholes and payoff computations) is research tooling, not financial advice.

> Previously marked "Internal / unpublished"; relicensed open-source when the
> simulator was published on GitHub Pages — see ADR
> [0007](docs/decisions/0007-public-github-pages.md).

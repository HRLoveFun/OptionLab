# Architecture Review — Scorecard, Debt Registry & Guardrails

> **Audience**: contributors and AI code reviewers. This is the standing record
> of the 2026-09 architecture review: the scoring framework, the registered
> tech-debt whitelist, and how the guardrails keep the score from regressing.
> Update this file whenever a `doc-guard: allow=` marker is added or removed.

---

## 1. The 8-dimension scorecard

Each dimension is scored 0–10 and weighted. Overall ≥ 8.5 excellent, 7.0–8.4
good, 5.5–6.9 passing but fragile, < 5.5 refactor needed.

| # | Dimension | Weight | Primary metrics |
|---|---|---|---|
| D1 | Layering clarity | 20% | cross-layer imports; calls only reach adjacent layers |
| D2 | Module coupling | 15% | fan-out per module (`arch_metrics.py`), fan-in concentration, cycles |
| D3 | Cohesion / SRP | 15% | responsibilities per file; files > 400 lines |
| D4 | Directory structure | 10% | domain-oriented packages; orphan modules; dead code |
| D5 | Naming consistency | 10% | duplicate module names; `_`-private module readability |
| D6 | Extensibility | 10% | files touched to add a feature; registry/plugin mechanics |
| D7 | Governance & guardrails | 10% | doc_guard rule coverage; blind spots; metric output |
| D8 | Doc/code consistency | 10% | declared invariants vs. real import graph |

**Baseline (2026-09-03, before remediation): 6.6 / 10 — passing but fragile.**
The dominant finding was not the structure itself but D7: the layer rule in
`scripts/doc_guard.py` had three blind spots (routes layer entirely unpoliced,
utils exempted, core→data_pipeline treated as legal), which let the code drift
from the architecture documented in [CODEBUDDY.md](../CODEBUDDY.md).

**After remediation (same day): ≈ 8.3 / 10.** All layer violations are either
fixed or registered in §2, cycles are zero, and the guardrails cover every
layer (see §3).

## 2. Registered architecture debt (`doc-guard: allow=` markers)

These are the *known, deliberate* violations. Each carries a suppression
comment in code and is counted by `scripts/arch_metrics.py --check`, so the
count can only go down without an explicit baseline update.

Run `grep -rn "doc-guard: allow" --include='*.py' core services data_pipeline`
for the live list. State at registration:

### core-purity (core must not import data_pipeline) — 2 markers

| Location | Why it exists | Exit condition |
|---|---|---|
| `core/market/data_context.py` (DataService, fetch_daily_ohlcv) | `build_data_context` *is* the DB-first read path; extracting it means inverting who constructs `DataContext` | `DataContext` becomes data-in/data-out; the fetch moves into a service factory |
| `core/market_review/fetch.py`, `core/market_review/__init__.py` (fetch_close_panel, get_conn) — **resolved 2026-09-03** | L1/L2/L3 cache ladder lived beside the computation it feeds | ladder moved to `services/market_review` (`fetch.py` + `facade.py`); `core/market_review` now receives panels via pure `build_review` / `build_timeseries` |
| `core/options/chain/analyzer.py` — **resolved 2026-09-03** | former ticker-only constructor fetched yfinance internally | constructor now requires `snapshot=`; fetch lives in `services/options/chain._build_analyzer` |

### db-access (services must not touch `data_pipeline.db` primitives) — 0 markers

| Location | Why it exists | Exit condition |
|---|---|---|
| `services/market/health.py` — **resolved 2026-09-03**, `services/portfolio/facade.py` — **resolved 2026-09-03** (`get_conn`) | ad-hoc health/inventory SQL predates `repos.py` coverage | queries moved into `data_pipeline/repos.py` |
| `services/regime/facade.py`, `services/regime/ops/_bootstrap.py`, `services/regime/ops/_persistence.py` (`fetch_df`, `init_db`, `upsert_many`) — **resolved 2026-09-03** | regime log writes were split across service and ops modules | consolidated behind `data_pipeline/repos.py` (regime-log + clean-row ops) |

### single-yf-exit (only `yf_client.py` may import yfinance) — 1 marker

| Location | Why it exists | Exit condition |
|---|---|---|
| `data_pipeline/downloader.py` | DB-aware gap-detection bulk downloads; documented chokepoint alongside `yf_client` (see `yf_client` module docstring) | fold the gap logic into `yf_client` |
| `data_pipeline/data_ops/_query.py::get_latest_spot` — **resolved 2026-09-03** | former spot fast-path fetched yfinance internally | now routes through `yf_client.fetch_spot` |

## 3. Guardrails (how the score is kept)

| Tool | Role | Run where |
|---|---|---|
| `scripts/doc_guard.py` | blocks violating edits: `import-direction`, `core-purity`, `db-access`, `single-yf-exit`, `sqlite-bypass`, `yfinance-throttle`, `yfinance-session-kwarg`, `tag-syntax`, `module-docstring`, ADR rules | pre-commit + CI, per changed file |
| `scripts/arch_metrics.py` | trend metrics: layer-edge violations, import cycles (Tarjan), god files, dead-code candidates, fan-in/out Top-5; `--check` fails CI on regression vs `.github/data/arch_baseline.json` | CI, whole repo |
| `tests/test_architecture_purity.py` | contract test re-asserting core purity at the test layer so suppressed markers stay visible in the test report | pytest |

**Layer allow-list** (single source of truth: `doc_guard.py::_ALLOWED_DEPS`,
mirrored in `arch_metrics.py`):

```
app           → routes, services, core, data_pipeline, utils
routes        → services, data_pipeline, utils          (never core directly)
services      → core, data_pipeline, utils
core          → utils (data_pipeline only via §2 markers)
data_pipeline → utils
utils         → (leaf: nothing upward)
```

## 4. Completed in the 2026-09 remediation

1. `doc_guard.py`: routes/utils brought under `import-direction`; new rules
   `core-purity`, `db-access`, `single-yf-exit`; suppression is now per-line.
2. `OptionsChainAnalyzer` made I/O-free — snapshot injected by services.
3. `utils → services` inversion removed: slice dispatch moved to
   `services/market/dispatch.py`; `utils/render_helpers.py` keeps only the
   pure error-fragment builder.
4. Routes de-layered: `routes/options.py` no longer imports `core`;
   `routes/core.py` gets spot quotes via `MarketService.fetch_spot`; all
   function-local service imports promoted back to module top level.
5. Import cycle `data_ops/_query.py <-> facade.py` broken (query calls sibling
   modules, never the facade).
6. Renames for D5: `market_analysis/{_service,_statistical,_assessment,
   _sizing,_summary}.py` → `{facade,statistical,assessment,sizing,summary}.py`;
   same for `data_ops/_service.py` → `facade.py`. Dead code
   `core/_shared/validators.py` deleted; `correlation_validator.py` moved into
   `core/market/`.
7. Chart-render fan-out of `core/options/chain/analyzer.py` collapsed through
   `core/options/charts/facade.py` (fan-out 11 → 5).
8. **`core/market/analyzer.py` fan-out** (15 → 2): the orchestration was split
   from the chart assembly. All chart-producing methods (`generate_scatter_plots`,
   `generate_high_low_scatter`, `generate_return_osc_high_low_chart`,
   `generate_volatility_dynamics`, `generate_oscillation_projection`,
   `analyze_options`, plus the feature/projection primitives that feed them)
   moved into `core/market/charts/facade.py::MarketChartAssembly`. `MarketAnalyzer`
   is now a thin orchestrator that builds the `DataContext` and delegates rendering,
   mirroring the options-side facade. The chart-assembly fan-out (14) now lives in
   the cohesive `charts/facade.py` instead of magnetising the orchestrator.
   `_get_current_price()` was also restored (it was referenced by
   `services/market/analysis/assessment.py` but previously unimplemented).
8. **services/ domain packaging** (D4): the flat `*_service.py` bag became four
   domain packages — `services/market|options|portfolio|regime/`, each with a
   `facade.py` entry point. `market_analysis/` → `market/analysis/`,
   `regime_ops/` → `regime/ops/`. All `routes/`, `tests/`, docstring
   `Dependencies:` blocks and docs were re-pointed in the same batch.

## 5. Open items (next batches)

1. **§2 debt paydown** (easiest first): `_query.get_latest_spot` → `yf_client` — **done
   2026-09-03**; `health`/`portfolio` SQL → `repos.py` — **done 2026-09-03**; `market_review`
   cache ladder → `services/market_review` — **done 2026-09-03**; `regime` SQL consolidation →
   `repos.py` — **done 2026-09-03**. All registered §2 debt is now resolved.
3. **Frontend consolidation** (P3): move the eight loose root-level scripts in
   `static/` (`option-chain.js`, `position.js`, `regime.js`, `simulation.js`,
   `market_review.js`, …) into `static/features/`.
4. ~~**`core/market/analyzer.py` fan-out** (15, top change-magnet): split the
   orchestration from the chart assembly the way the options side did.~~
   **Resolved 2026-09-03** — see §4 item 8.

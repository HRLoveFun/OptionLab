# L0 File Architecture — 顶层骨架清单与整改批次

> **Audience**: AI reviewers + contributors who need the "shape" of the repo before
> touching any module. L1 (per-package internals) is documented in
> [`CODEBUDDY.md`](../CODEBUDDY.md) §Architecture and
> [`docs/architecture_review.md`](architecture_review.md).
>
> **Snapshot**: 2026-09-08 · commands to refresh the numbers are in §6.

---

## 0. What "L0" means here

`L0` is **not** a term used elsewhere in this repo (`docs/automation.md` defines
only L1 guards / L2 AI drafts / L3 derived artefacts). In this document L0 is
defined as:

> The outermost structure that decides the project's shape — root-level files,
> the first-level directory boundaries, and the one-way dependency trunk that
> runs between them.

Everything *inside* a first-level directory (`core/market/charts/…`,
`services/market/analysis/…`) is L1+ and out of scope here.

---

## 1. L0 inventory

### A. Runtime trunk — dependency direction is one-way

```
app.py → routes/ → services/ → core/ → data_pipeline/ → utils/
```

| Node | Scale | Responsibility | Health |
|---|---|---|---|
| `app.py` | 114 lines · fan-out 6 | Thin adapter only: JSON error envelope, `/api/v1` → `/api` alias middleware, rate limiter, `YF_PROXY` propagation, DB init, scheduler leader-lock, registers 7 blueprints (`app.py:100-106`) | good |
| `routes/` | 909 lines · 8 files | 7 blueprints + `__init__.py` aggregate export; no business logic | good |
| `services/` | 3 540 lines · 5 domain packages | `market` (incl. `analysis/` slice factory), `market_review`, `options`, `portfolio`, `regime` | good |
| `core/` | 6 372 lines · 8 sub-packages + `_shared` | Pure computation — no Flask, no DB, no network | good |
| `data_pipeline/` | 2 645 lines · 12 files | The only I/O boundary: `yf_client`, `db`/`repos`, `data_ops`, `scheduler`, `job_cache` | good |
| `utils/` | 756 lines · 7 files | Leaf layer; highest fan-in (`ticker_utils.py` = 11) | good |
| `templates/` | 1 546 lines · 17 files | `index.html` skeleton + `partials/fragments/*` (HTMX swap targets) | good |
| `static/` | 5 473 lines · 31 JS/CSS | `state/` · `sim/` · `components/` · `features/` + tab entry files | fair (see §4 P3-1) |

### B. Dependencies & configuration

| File | Content | Risk |
|---|---|---|
| `requirements.txt` (17) | 9 runtime deps, mostly `==` pinned; `flask>=3.1.3`, `gunicorn>=23.0.0` unbounded | medium — no lock/hash (P2-3) |
| `pyproject.toml` (51) | pytest `addopts = "-x --tb=short -q"`; ruff `required-version >=0.16.5,<0.17`; `src = core/services/data_pipeline/utils` | low |
| `package.json` + `package-lock.json` (3 235) | vitest / jsdom / coverage only — **no runtime npm dependency**; lockfile committed | low |
| `vitest.config.js` (21) | runs `tests/unit/**`; coverage limited to `api.js` / `eventBus.js` / `utils.js` / `state/**` | coverage scope too narrow (P3-1) |
| `.env` / `.env.example` | `.env` correctly git-ignored | low |
| `.pre-commit-config.yaml` (23) | doc-guard + derived artefacts, `language: system` | low |
| `.github/` | 4 workflows, agents/prompts/skills/hooks, baselines `arch_baseline.json` · `tag_baseline.json` · `failure-registry.yaml` | low |
| `deploy/` | `Dockerfile`, `optionlab.service`, `setup_oracle.sh` | low |

### C. Context documentation (human + AI)

| File | Audience | Note |
|---|---|---|
| `README.md` (440 lines) | humans | duplicate architecture source (P2-1) |
| `CODEBUDDY.md` (226 lines) | AI | duplicate architecture source (P2-1) |
| `docs/` (19 md) | contributors | `architecture_review.md` (scorecard + debt registry), `automation.md`, `constraints.md`, `frontend_architecture.md`, `glossary.md`, `decisions/` (10 ADRs) |

### D. Generated artefacts & local data (the "dust zone" of L0)

| Item | State | Note |
|---|---|---|
| `market_data.sqlite` (11.7 MB) | git-ignored, lives in repo root | default `DB_PATH = os.getcwd()/market_data.sqlite` (`data_pipeline/db.py:27`) — P2-2 |
| `site/` | **inputs committed (9 files) · build output ignored** | tracked: `fixtures/` (7) · `snapshot/snapshot.json` · `pages-shim.js`; ignored: `index.html`, 5 feature + 6 showcase redirects, `static/**` (42 generated files) — see §5 P1-1 |
| `archive/` (8 files · 1 070 lines) | committed | retired code still in tree — P3-3 |
| `test.ipynb` (58 lines) | git-ignored | leftover scratch file — P2-2 |
| `coverage/` · `__pycache__` · `.pytest_cache` · `.ruff_cache` · `node_modules/` | git-ignored | fine |

---

## 2. Measured shape (`scripts/arch_metrics.py`)

```
modules=146  import_edges=300
Layer-edge violations : (none)
Import cycles         : 0
God files (>400 lines): (none)
Top fan-out  : core/market/charts/facade.py(14) · core/market/data_context.py(7)
               routes/__init__.py(7) · routes/core.py(7) · app.py(6)
Top fan-in   : core/_shared/plotting.py(13) · data_pipeline/yf_client.py(11)
               utils/ticker_utils.py(11) · data_pipeline/db.py(9)
Dead code    : services/market/analysis/summary.py  (only one; already on the
               watch list in docs/architecture_review.md §2)
```

Static checks at snapshot time: `ruff check .` clean · `ruff format --check .`
319 files clean · `pytest -m "not network" --ignore=tests/e2e` → 453 passed /
5 skipped, exit 0.

---

## 3. Target L0 layout (after remediation)

```
OptionLab/
├─ app.py                      # thin adapter entry point
├─ routes/ services/ core/ data_pipeline/ utils/   # five-layer one-way trunk
├─ templates/ static/          # ONE UI shared by Flask and Pages
├─ tests/  tests/e2e/  tests/unit/
├─ scripts/                    # governance + build (never imported at runtime)
├─ docs/  docs/decisions/      # single source of truth for architecture
├─ deploy/  .github/           # deployment + governance baselines
├─ site/                       # ONLY fixtures/ · snapshot/ · pages-shim.js tracked
├─ data/                       # market_data.sqlite moves out of the source root
└─ archive/                    # mark read-only or move out
```

---

## 4. Open findings (summary; details in the 2026-09-08 review)

| ID | Level | Item |
|---|---|---|
| ~~P1-1~~ | 严重 · **已整改 2026-09-08** | generated Pages mirror untracked + git-ignored (42 files) |
| ~~P1-2~~ | 严重 · **已整改 2026-09-08** | `static/sidebar.js` committed (`7ef2a33`) + guard test added (`65c01f6`); the 8 favicon/webmanifest assets referenced by `templates/index.html:8-13` were committed by the same work stream, so the guard is green |
| P2-1 | 建议 | Three parallel descriptions of the architecture (`README`, `CODEBUDDY.md`, `docs/`) |
| P2-2 | 建议 | Root-level strays: `options_learning_charter_v1_2.md`, `market_data.sqlite`, `test.ipynb` |
| P2-3 | 建议 | `requirements.txt` has unbounded ranges and no lock file |
| P3-1 | 提示 | vitest coverage scope covers only 4 paths; ~4 000 lines of `static/` unmeasured |
| P3-2 | 提示 | `np.trapz` deprecated (`core/strategies/prob_profit.py:41,44`) |
| P3-3 | 提示 | `docs/reference/` empty dir (git cannot track it); `archive/` still in tree |

---

## 5. Remediation batches (P1-1 / P1-2)

Ordering matters: **P1-2 first, then P1-1** — the generated-copy cleanup must
not be performed while `static/sidebar.js` is still untracked, otherwise the
shadow copy and the source disagree about a file that is not in git at all.

### P1-2 — bring the referenced-but-untracked frontend file into git

**Status: done (2026-09-08)** — `7ef2a33 feat(frontend): 添加侧边栏折叠功能`
committed the script/template/style/doc as one unit; `65c01f6` added the guard
test (`tests/test_pages_build.py::test_template_static_references_exist`),
verified to fail when `static/sidebar.js` is removed.

> **Same-shift catch**: the guard immediately flagged the next instance of the
> pattern — `templates/index.html:8-13` referenced 6 favicon files plus
> `site.webmanifest` that were untracked at the time. They were committed with
> `routes/core.py::favicon_root` in the same work stream, so the invariant now
> holds for the whole `static/` tree.

| Step | Action | Command / edit |
|---|---|---|
| B1 | Decide: finish or drop. `templates/index.html:168` already loads `sidebar.js` and `docs/frontend_architecture.md:134` documents it → keep it | — |
| B2 | Commit the whole WIP set **atomically** so template, style, doc and script never disagree again | `git add static/sidebar.js templates/index.html static/styles.css docs/frontend_architecture.md && git commit -m "feat(ui): collapsible sidebar"` |
| B3 | Add a regression guard: assert every `url_for('static', filename=…)` referenced by `templates/**` exists on disk | new test in `tests/test_pages_build.py` (or a `doc_guard` rule) — scan `templates/*.html` + `templates/partials/*.html`, `assert (static / name).exists()` |
| B4 | Verify | `pytest tests/test_pages_build.py -q` · `pytest tests/e2e/test_smoke.py -q` · `python scripts/build_pages_site.py --out /tmp/ol_site && ls /tmp/ol_site/static/sidebar.js` |
| Rollback | `git revert` the single commit; the guard in B3 is independent | — |

**Exit criteria**: `git ls-files static/sidebar.js` non-empty, and no template
references a missing static asset.

### P1-1 — stop tracking the generated Pages mirror

**Status: done (2026-09-08)** — forensics run first
(`build_pages_site.py --out /tmp/ol_site_check` + `diff -rq`) proved 42
generated files vs 10 sources; `.gitignore` now lists exactly those 42, and
`git rm -r --cached` untracked them without touching the working tree.

| Step | Action | Command / edit |
|---|---|---|
| B1 | Prove the generated-file set instead of guessing: build to a scratch dir and diff against the committed `site/` | `python scripts/build_pages_site.py --out /tmp/ol_site_check` then `diff -rq /tmp/ol_site_check site` |
| B2 | Record the boundary in `.gitignore` (candidates: `site/static/`, `site/index.html`, `site/*/index.html`, `site/showcase/*.html`) — **only for files B1 proves are generated** | edit `.gitignore` |
| B3 | Untrack without deleting the working-tree copy | `git rm -r --cached site/static site/index.html site/*/index.html …` |
| B4 | Fix the now-wrong claim in `.github/workflows/pages.yml` ("static/* … never forked for Pages") — CI keeps generating them, they are simply no longer committed | edit workflow header comment |
| B5 | Update the Pages description in `README.md` §Deployment and `docs/frontend_architecture.md` if they reference committed `site/static` | edit docs |
| B6 | Verify | `git ls-files site \| wc -l` (expect ≈ fixtures + snapshot + shim) · `pip install jinja2 && python scripts/build_pages_site.py` · `pytest tests/test_pages_build.py -q` · `pytest tests/test_pages_fixtures.py -q` |
| Rollback | `git revert` + `git rm --cached` reversal; `site/` is fully regenerable from `scripts/build_pages_site.py` | — |

**Exit criteria**: `static/` and `templates/` exist exactly once in the repo;
every other file under `site/` is either a committed input (fixtures, snapshot,
shim) or regenerable output.

### Follow-up batches (P2/P3, low urgency)

| Batch | Scope | Notes |
|---|---|---|
| B-A | P2-1 | Make `docs/` the single architecture source; `README` keeps quick-start + API; `CODEBUDDY.md` links instead of duplicating |
| B-B | P2-2 | Move `options_learning_charter_v1_2.md` → `docs/`; default `MARKET_DB_PATH` → `data/market_data.sqlite`; delete `test.ipynb` |
| B-C | P2-3 | Pin `flask` / `gunicorn` with `~=` or add `requirements.lock` |
| B-D | P3-1/2/3 | Widen vitest `coverage.include`; `np.trapz` → `np.trapezoid`; decide on `docs/reference/` and `archive/` |

---

## 6. Refreshing this document

```bash
python scripts/arch_metrics.py                     # §2 metrics
python -m ruff check . && python -m ruff format --check .
pytest -m "not network" --ignore=tests/e2e -q
python -m pip_audit                                # dependency audit
npm audit                                          # JS dependency audit
find . -maxdepth 1 -type f -exec wc -l {} \; | sort -rn   # §1 root inventory
```

Re-run these whenever a first-level directory is added/removed, or when
`arch_metrics.py --check` reports a baseline drift — a drift means §2 of this
file is stale.

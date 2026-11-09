# Conventions — Code, Tests, Commands, Review

> L1 | 权威：语言与命名、日志与类型、领域常数、注释标签、数据访问、测试与命令参考、评审与文档维护义务 | 不权威：分层与依赖方向（见 `docs/architecture.md`）、外部约束（见 `docs/constraints.md`）

Laid out by the same rules that `doc_guard.py` enforces, plus the AI-review rules that used to live
in `.github/copilot-instructions.md`. If a rule here contradicts the code, the rule wins for
*normative* items (see `AGENTS.md` 元规则) — fix the code or record an exception in
`docs/constraints.md`.

## Language and naming

- **Language**: code, comments, logs, identifiers in English; UI strings may be Chinese — do not
  "translate" template Chinese.
- Tests use behavioural names (`test_<subject>_<expected_behaviour>`), not bare symbol names.
- Public function signatures carry type hints.
- Use `logging.getLogger(__name__)`, never `print()`. The dev server logs to stderr at INFO.
- Prefer specific exception types over bare `except Exception`.
- Constants belong in `utils/constants.py` (domain defaults such as `DEFAULT_TICKER`,
  `FREQUENCY_DISPLAY`) or environment variables (see `.env.example`).

## Domain constants and comment tags

- **"Magic numbers" in `core/` are domain constants** (MA 10/20/50/200, RSI 14, BB 20, HV 30,
  sigma bounds for Greeks). Read `docs/constraints.md` §5 and `docs/glossary.md` before touching
  them, and do **not** refactor them as "magic numbers".
- **Comment tags mark already-reviewed code.** `WHY:`, `CONSTRAINT:`, `TRADEOFF:`, `INVARIANT:`,
  `DOMAIN:`, `HACK:`/`WORKAROUND:` — do **not** propose refactors on tagged code unless asked.
  `doc_guard.py` `tag-syntax` keeps the vocabulary canonical.

| Tag | Meaning |
|-----|---------|
| `WHY:` | Explains the motivation behind a non-obvious line/block. |
| `CONSTRAINT:` | External or historical constraint that forbids changing this. Often references `docs/constraints.md` or an ADR. |
| `TRADEOFF:` | Acknowledged trade-off; states what was given up and why. |
| `INVARIANT:` | A property that must hold; breaking it causes silent bugs elsewhere. |
| `DOMAIN:` | A "magic number" that encodes financial domain knowledge — not a config value. |
| `HACK:` / `WORKAROUND:` | Temporary fix; should include the trigger condition and cleanup criterion. |

When **adding** new code that has implicit reasoning, use these tags. Example:

```python
# CONSTRAINT: yfinance >= 0.2.50 uses curl_cffi internally; passing a
# requests.Session here silently fails. See docs/constraints.md §2.
yf_throttle()
df = yf.download(ticker, start=start, end=end)
```

## Every new module needs a docstring

Every new module under `core/`, `data_pipeline/`, `services/`, `utils/` needs a top-level docstring
(`doc_guard.py` `module-docstring`), in the `Domain: / Context: / Contracts: / Dependencies:` shape.

## Data access

- Always go through `data_pipeline/store/db.py::get_conn()`; it enables WAL mode, sets
  `synchronous=NORMAL`, and is safe to share across threads.
- Only `data_pipeline/store/repos.py` builds SQL (`doc_guard` `db-access`).
- DB path comes from `MARKET_DB_PATH`.

## Commands

### Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # Python 3.12+
npm install                              # only for vitest JS tests
cp .env.example .env                     # set YF_PROXY, MARKET_DB_PATH, AUTO_UPDATE_TICKERS
pre-commit install
```

`ruff`, `pytest-playwright`, `APScheduler`, and `Pillow` are deliberately **not** in
`requirements.txt` — install them only when needed (CI installs `ruff==0.16.5` in its own step;
keep in sync with `required-version` in `pyproject.toml`). `Pillow` is only for
`scripts/gen_favicons.py`, the one-shot regenerator of the raster favicon set.

### Run

```bash
python app.py                                              # dev server, PORT defaults to 5001, HOST (bind address) defaults to 0.0.0.0
gunicorn app:app -b 0.0.0.0:5001 --workers 2 --threads 4   # production
```

`app.py` is a thin adapter: wires `/api/v1/*`→`/api/*` middleware, installs the JSON error
envelope (`utils/api_errors.py::install`) and the in-house per-IP rate limiter
(`utils/rate_limit.py::install`), propagates `YF_PROXY` to curl_cffi, bootstraps the SQLite
schema, and starts APScheduler only on the worker that wins the leader lock. APScheduler is
lazily imported and only required when `AUTO_UPDATE_TICKERS` is set. Tests set `RATE_LIMIT_DISABLED=1`.

### Lint and format

```bash
ruff check .          # E,W,F,I,B,UP; line-length 120; config in pyproject.toml
ruff format --check .  # CI runs both
```

### Python tests

```bash
pytest                                            # whole suite; addopts "-x --tb=short -q" stops at first failure
pytest --maxfail=0                                # override the -x to see everything
pytest tests/test_signals.py::test_hv_window -v   # a single test
pytest -m "not network"                           # skip live-yfinance tests
pytest --ignore=tests/e2e                         # skip Playwright
```

`tests/conftest.py` is autouse: it points `MARKET_DB_PATH` at a per-test tmp file and clears
`DataService`'s process-wide query cache, so tests never touch the real `market_data.sqlite`.

The Playwright suite uses mocked Flask routes (`tests/e2e/conftest.py`) so it runs offline; see
`tests/e2e/README.md`. The perf benchmark spins up a real WSGI server and measures the end-to-end
fan-out time for `/render/<kind>` × tickers (`python scripts/perf_regression.py -v`).

JS math parity: `tests/unit/sim/*.test.js` compares the browser implementation against fixtures
from `scripts/gen_sim_golden.py` (real Python output), within 1e-6 — no mocked data.

### E2E (Playwright) and JS tests

```bash
pip install pytest-playwright && playwright install chromium
pytest tests/e2e/                     # headless; real Flask server in a daemon thread, /api/* mocked at the browser layer
npx vitest run                        # tests/unit/**/*.test.js (jsdom)
npx vitest run tests/unit/api.test.js
```

### Doc and architecture automation (also run by pre-commit + CI)

```bash
python scripts/doc_guard.py --files a.py b.md    # lint L1 invariants on changed files
python scripts/arch_metrics.py --check           # drift gate vs .github/data/arch_baseline.json
python scripts/regen_adr_index.py                # regenerate docs/decisions/README.md after adding an ADR
python scripts/audit_tags.py                     # comment-tag coverage regression
python scripts/seed_history.py NVDA 5            # one-shot 5-year SQLite backfill
bash scripts/doc-check.sh                        # doc map / vocabulary / file reconciliation
```

## Code review rules

When reviewing or modifying this codebase:

1. **Tagged code is justified code.** If a line has `WHY:` / `CONSTRAINT:` / `TRADEOFF:` / `DOMAIN:` / `INVARIANT:` above it, do not suggest "improving" it without explicit user request.
2. **Magic numbers in `core/`** are usually domain constants (MA windows, IV bounds, sigma thresholds). Search `docs/glossary.md` and `docs/constraints.md` before suggesting extraction to config.
3. **Before suggesting a new dependency**, check whether the constraint section explicitly forbids it (e.g. no React, no Postgres, no `requests.Session` for yfinance).
4. **Before suggesting a refactor that crosses layers**, re-read `docs/architecture.md` and ADR 0001.
5. **When uncertain whether something is intentional**, ask the user — do not silently change it.
6. **For bug fixes**, follow the fix-review skill (`.github/skills/fix-review/SKILL.md`): architecture compliance, test coverage, NaN safety.

## Documentation duty

Whenever you make a code change, also update the relevant documentation artefacts **in the same
response** — do not defer this:

| If your change… | Then also update… |
|---|---|
| introduces a new non-obvious constant or branch | add a `WHY:` / `CONSTRAINT:` / `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` comment at the call site |
| introduces a new external constraint (lib quirk, rate limit, version pin) | add a section to `docs/constraints.md` |
| introduces a new architectural decision (new module boundary, new tech) | add an ADR via `docs/decisions/TEMPLATE.md` **and** run `scripts/regen_adr_index.py` |
| introduces a new domain term to user-visible UI / docs / API | add an entry to `docs/glossary.md` |
| modifies code that an existing ADR references in its "Related code" section | update that ADR's "Consequences" or set its status to "needs review" |
| adds a new module under `core/` / `data_pipeline/` / `services/` | include a top-level docstring in the `Domain/Context/Contracts/Dependencies` shape |
| adds a new test | use a behavioural name (`test_<subject>_<expected_behaviour>`) |
| adds or moves a document | update `DOC_MAP.md` first, then run `bash scripts/doc-check.sh` |
| finishes a batch | update its row in `STATUS.md` (status + evidence + date) |

Before claiming a task complete, run (or simulate) `python scripts/doc_guard.py` mentally: would your
change pass tag-syntax, yfinance-throttle, sqlite-bypass, import-direction, module-docstring,
adr-link-integrity, adr-index-fresh? If not, fix it before handing back. The full automation
contract is documented in `docs/automation.md`.

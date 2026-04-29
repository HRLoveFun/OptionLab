# Copilot Instructions — OptionStrategy

## Project Overview

Flask-based market analysis dashboard with options strategy tools.
- **Backend**: Python 3.12, Flask, SQLite (WAL mode), APScheduler, yfinance
- **Frontend**: Vanilla JS + CSS + Jinja2 templates
- **Architecture**: `app.py` → `services/` → `core/` → `data_pipeline/`

## Code Style

- Language: Python code and comments in **English**; user-facing strings may be Chinese
- Use `logging.getLogger(__name__)` — never `print()` in production code
- Prefer specific exception types over bare `except Exception`
- Type hints on public function signatures
- Constants belong in `utils/utils.py` or environment variables (see `.env.example`)

## Architecture Rules

- **Import direction**: `app.py` → `services/` → `core/` → `data_pipeline/`; never reverse
- **No circular imports**: `data_pipeline/` must not import from `services/` or `core/`
- `core/` contains computation logic — no Flask request handling
- `services/` orchestrates `core/` modules and formats results for routes
- `data_pipeline/` handles download, cleaning, processing, and DB access

## Database

- SQLite via `data_pipeline/db.py` — always use `get_conn()` context manager
- WAL mode enabled; `PRAGMA synchronous=NORMAL`
- DB path from `MARKET_DB_PATH` env var, default `./market_data.sqlite`

## Testing

- Framework: **pytest** (configured in `pyproject.toml`)
- Test files: `tests/test_*.py`
- Run: `pytest` or `pytest -x --tb=short`

## Environment Variables

See `.env.example` for all supported variables and defaults.

## Build & Run

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py                    # dev server on :5000
gunicorn app:app -b 0.0.0.0:5000  # production
```

## Key Patterns

- Financial domain constants (MA windows, oscillation params) are intentional — don't refactor as "magic numbers"
- Chart generation returns base64-encoded images via `chart_service.py`
- Options Greeks use vectorized Black-Scholes in `core/options_greeks.py`
- Data freshness: 60-second cooldown per ticker in `DataService`

## Project Documentation Map

Before suggesting non-trivial changes, consult these:

- **[docs/constraints.md](../docs/constraints.md)** — external/historical constraints (yfinance limits, SQLite choice, single-machine assumption, intentional "magic numbers"). Read this before flagging anything as tech debt.
- **[docs/glossary.md](../docs/glossary.md)** — domain terms (IV vs HV, Greeks, regime, anomaly flags). Read this before assuming a term means what you think it means.
- **[docs/decisions/](../docs/decisions/)** — Architecture Decision Records. Each ADR explains the context, options considered, and accepted trade-offs for a major design choice.

## Comment Tag Convention

We mark intentional design choices with a fixed vocabulary so AI reviewers and future contributors recognise them. **When you see one of these tags, treat the code as already-justified — do not suggest refactors unless the user explicitly asks to revisit the decision.**

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

## AI Code Review Guidelines

When reviewing or modifying this codebase:

1. **Tagged code is justified code.** If a line has `WHY:` / `CONSTRAINT:` / `TRADEOFF:` / `DOMAIN:` / `INVARIANT:` above it, do not suggest "improving" it without explicit user request.
2. **Magic numbers in `core/`** are usually domain constants (MA windows, IV bounds, sigma thresholds). Search `docs/glossary.md` and `docs/constraints.md` before suggesting extraction to config.
3. **Before suggesting a new dependency**, check whether the constraint section explicitly forbids it (e.g. no React, no Postgres, no requests.Session for yfinance).
4. **Before suggesting a refactor that crosses layers**, re-read the Architecture Rules and ADR 0001.
5. **When uncertain whether something is intentional**, ask the user — do not silently change it.
6. **For bug fixes**, follow the [fix-review skill](skills/fix-review/SKILL.md): architecture compliance, test coverage, NaN safety.

## AI Doc-Maintenance Duty

Whenever you (the AI) make a code change, you MUST also update the relevant
documentation artefacts **in the same response** — do not defer this:

| If your change… | Then also update… |
|---|---|
| introduces a new non-obvious constant or branch | add a `WHY:` / `CONSTRAINT:` / `TRADEOFF:` / `INVARIANT:` / `DOMAIN:` comment at the call site |
| introduces a new external constraint (lib quirk, rate limit, version pin) | add a section to [`docs/constraints.md`](../docs/constraints.md) |
| introduces a new architectural decision (new module boundary, new tech) | add an ADR via [`docs/decisions/TEMPLATE.md`](../docs/decisions/TEMPLATE.md) |
| introduces a new domain term to user-visible UI / docs / API | add an entry to [`docs/glossary.md`](../docs/glossary.md) |
| modifies code that an existing ADR references in its "Related code" section | update that ADR's "Consequences" or set its status to "needs review" |
| adds a new module under `core/` / `data_pipeline/` / `services/` | include a top-level `Context:` docstring |
| adds a new test | use a behavioural name (`test_<subject>_<expected_behaviour>`), not just the symbol under test |

Before claiming a task complete, run (or simulate) `python scripts/doc_guard.py`
mentally: would your change pass tag-syntax, yfinance-throttle, sqlite-bypass,
import-direction, module-docstring, adr-link-integrity, adr-index-fresh? If
not, fix it before handing back.

The full automation contract is documented in [`docs/automation.md`](../docs/automation.md).

## Custom Skills & Agents

Use these when relevant — type `/` in chat to invoke skills/prompts, or select agents from the agent picker.

### Skills (workflows)
- **`/debug-pipeline`** — Diagnose data pipeline failures (empty charts, stale data, yfinance errors)
- **`/test-escalation`** — Escalate testing strategy when tests miss root cause (4-level system)
- **`/fix-review`** — Review a bug fix before committing (architecture, tests, NaN safety)

### Agents (specialists)
- **`@pipeline-doctor`** — Read-only data pipeline diagnostician
- **`@test-strategist`** — Analyze test failures and recommend strategy changes (3-strike rule)

### Prompts (quick tasks)
- **`/diagnose`** — Quick diagnosis: why is ticker data empty/stale?
- **`/new-test`** — Generate a test following project patterns
- **`/pipeline-status`** — Check DB row counts, data freshness, NaN rows

### Hooks (automatic)
- **Import guard**: After editing `data_pipeline/` or `core/`, checks for forbidden imports (logs to `.github/data/import_violations.log`)
- **Test analyzer**: After running pytest, detects recurring failure patterns using the failure registry and suggests escalation with cooldown
- **Session context**: At session start, injects active (unresolved) failure patterns from the tracker as context

### Data (feedback loop)
- **`.github/data/failure-registry.yaml`** — Central source of truth for failure patterns, escalation levels, and resolution status. Updated by skills after diagnosis/fix.
- **`.github/data/failure_tracker.json`** — Auto-maintained by the test analyzer hook. Tracks occurrence counts and timestamps per failure category.

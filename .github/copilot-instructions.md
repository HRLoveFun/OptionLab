# Copilot Instructions — OptionLab

> L0 | 权威：Copilot 专属路由与自定义 skill/agent/hook 清单 | 不权威：规则条文（见 AGENTS.md 与 docs/CONVENTIONS.md）

> 本文件只是路由：规则与命令的权威在下面几处，不在这里复述。

## Read first

- `AGENTS.md` — agent 入口：元规则、改动协议、门禁最小命令集。
- `DOC_MAP.md` — 全部文档的清单与标签（按主题 / 时机 / 修改事件查）。
- `docs/CONVENTIONS.md` — 代码风格、注释标签（`WHY:` / `CONSTRAINT:` / `TRADEOFF:` /
  `INVARIANT:` / `DOMAIN:`）、评审清单、文档维护义务。
- `docs/architecture.md` — 分层依赖方向与 streaming 请求流。
- `docs/constraints.md` — 外部与历史约束；判技术债之前先读。

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

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->

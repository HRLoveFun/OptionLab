# AGENTS.md

OptionLab is a single-process Flask dashboard for equity/options research. It pulls prices and
option chains from **yfinance only**, caches them in **SQLite (WAL)**, and serves a **streaming
HTMX + vanilla-JS** UI where nearly all charts are server-side matplotlib PNGs.

## 现在到哪

进度、未完成项与已知风险只在 `STATUS.md`；本文件不复述。

## 文档地图

完整清单在 `DOC_MAP.md`，本文件不复述。先看开头的词表，再按标签查，查完还要全文搜索：

```bash
grep '【arch' DOC_MAP.md                            # 主题换成词表里的父级
grep '【arch' DOC_MAP.md | grep '【cross-module】'   # 再叠一个时机标签
```

Accepted ADRs are not up for re-litigation: read `docs/decisions/` before proposing to undo one.
Layout, request flow and data stages: `docs/architecture.md`. Per-module responsibilities:
`docs/module_reference.md`.

## 元规则

只放两类：路由（读什么）与文档维护（怎么改）。产品与技术规范一律在 `docs/CONVENTIONS.md`，
外部约束在 `docs/constraints.md`。

1. 一次只读需要的那 1–3 份，不全量读。
2. 同一事实只在一处可写，其余位置只留指针；发现副本就地改成指针。
3. 代码与文档冲突：描述性文档（现状、结构、进度）以代码为准改文档；规范性文档（约定、契约）
   以文档为准改代码，做不到就把例外记进 `docs/constraints.md`。
4. 状态只有 `STATUS.md` 里那几个枚举值；不许写「基本完成」「大概做完」，写不准就写进 `docs/plans/`。

## 改动协议

1. 查该改哪份：`grep '【事件】' DOC_MAP.md`（事件换成词表里的修改事件），看“时改”那段，逐份更新。
2. 改文档结构：先改 `DOC_MAP.md`，再动文件，最后对账。
3. 每个开发任务在自己的 worktree 里跑（ADR 0009）：`python scripts/worktree.py create <task-name>`；
   主工作区始终保持 `main` 且干净，流程见 `docs/guides/GIT_WORKTREE_WORKFLOW.md`。
4. 验收：`bash scripts/doc-check.sh` 退出码 0，且 `python scripts/doc_guard.py` 无违规。
5. 代码改动在同一次响应里更新文档——改哪份查 `docs/CONVENTIONS.md` §Documentation duty 的表。

## 命令（门禁最小集）

```bash
pytest                              # full suite (-x --tb=short by default)
ruff check . && ruff format --check .
python scripts/doc_guard.py         # tag / architecture / ADR invariants
bash scripts/doc-check.sh           # doc map / vocabulary / file reconciliation
```

Setup, run, e2e, vitest 与文档自动化脚本的完整命令在 `docs/CONVENTIONS.md` §Commands。

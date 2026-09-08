# 0009. Per-Task Git Worktree Isolation

- **Status**: Accepted
- **Date**: 2026-09-08
- **Deciders**: repo owner

## Context

Development tasks (features, fixes, experiments) were previously done by switching
branches inside the single main workspace. With parallel tasks this causes:

- **Code conflicts**: uncommitted / half-finished changes from one task leak into
  another when branches are switched.
- **Dependency interference**: a shared `.venv` mutated for one task (dep bump,
  e2e-only installs like `pytest-playwright`) breaks another task's test run.
- **Dirty main workspace**: long-lived branches keep the main checkout on a
  non-`main` state, so "what is clean?" becomes ambiguous.

Git worktrees give every task its own checkout directory + branch, sharing one
`.git` object store, with zero branch-switching.

## Options Considered

1. **Option A — stay on single-workspace branch switching.**
   - Pros: no new tooling.
   - Cons: serialises tasks; uncommitted state and `.venv` drift cause cross-task
     breakage; error-prone `git stash` juggling.
2. **Option B — full clone per task.**
   - Pros: total isolation.
   - Cons: duplicates the whole object store and history; no shared refs; heavier
     disk usage; slower setup.
3. **Option C — one worktree per task under a dedicated root.**
   - Pros: full working-tree + venv isolation per task, shared `.git` (cheap),
     main workspace stays permanently on `main` and clean.
   - Cons: needs a convention for paths, env bootstrap and cleanup discipline.

## Decision

We chose **Option C**. Rules:

- Every non-trivial task gets its own worktree at `.worktrees/<task-name>/`
  (override root with `WORKTREE_ROOT`), paired with a dedicated branch.
- All development and modification happens **only inside the worktree**; the main
  workspace stays on `main` and is never used for task edits.
- Each worktree bootstraps its own `.venv` and copies `.env`, so dependencies and
  local config never interfere across tasks.
- After a task's branch is merged, its worktree and branch are deleted promptly
  (`scripts/worktree.py remove/clean`), keeping the repo tidy.

Workflow, commands and guard rails: [`docs/guides/GIT_WORKTREE_WORKFLOW.md`](../guides/GIT_WORKTREE_WORKFLOW.md).
Helper tooling: `scripts/worktree.py`.

## Consequences

- Positive: tasks are fully isolated (code + venv + local data); parallel work is
  trivial; main workspace is always clean and reviewable; no stash juggling.
- Negative / accepted trade-offs: each worktree needs a one-time venv bootstrap
  (~1 min); multiple worktrees consume extra disk; contributors must remember to
  clean up (mitigated by `scripts/worktree.py clean` and its merged-only guard).
- Follow-up actions: `.gitignore` covers `.worktrees/`; dev-server port / DB-path
  separation per worktree is documented in the guide.

## References

- Related code: `scripts/worktree.py`, `.gitignore`
- Related ADR: 0003 (SQLite local file — per-worktree `MARKET_DB_PATH` note in the guide)
- External: `git worktree` documentation

# Git Worktree Workflow — Per-Task Isolation (ADR 0009)

Every development task runs in its **own git worktree**: an independent checkout
directory with its own branch and its own `.venv`. The main workspace stays on
`main`, clean, and is never used for task edits.

```
OptionLab/                    ← main workspace: stays on main, clean
└── .worktrees/               ← all task worktrees (gitignored)
    ├── fix-rate-limiter/     ← branch `fix-rate-limiter`, own .venv, own .env
    └── add-glossary-links/   ← branch `add-glossary-links`, own .venv, own .env
```

## 1. Create a worktree for a new task

Preferred — the helper script does bootstrap for you:

```bash
python scripts/worktree.py create fix-rate-limiter
# → creates branch `fix-rate-limiter` from main (or --base <ref>),
#   worktree at .worktrees/fix-rate-limiter/,
#   bootstraps .venv + copies .env, prints the cd path

cd .worktrees/fix-rate-limiter && source .venv/bin/activate
```

Equivalent manual commands:

```bash
git worktree add .worktrees/fix-rate-limiter -b fix-rate-limiter main
cd .worktrees/fix-rate-limiter
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env . 2>/dev/null || cp .env.example .env
```

Rules:

- Branch name = task name (short, kebab-case); it must be **unique** across tasks.
- One task = one worktree = one branch. Never share a worktree between tasks.
- **Never create task worktrees outside `.worktrees/`** (or `$WORKTREE_ROOT`).

## 2. Switch between tasks

Worktrees are directories — "switching" is just `cd`; no branch switching,
no stashing:

```bash
cd .worktrees/fix-rate-limiter && source .venv/bin/activate   # task A
cd .worktrees/add-glossary-links && source .venv/bin/activate # task B
```

To see everything at a glance:

```bash
python scripts/worktree.py list    # or: git worktree list
```

## 3. Run / test inside a worktree without collisions

Parallel tasks must not fight over shared process resources:

- **Dev server port**: export a distinct `PORT` per worktree (e.g. 5001, 5002, …).
- **Database**: `MARKET_DB_PATH` defaults into the worktree's own directory; for
  heavy analysis reuse the main workspace's cache by pointing at it explicitly:
  `MARKET_DB_PATH=../../market_data.sqlite` (read-mostly usage is safe under WAL).
- **E2E**: `pip install pytest-playwright && playwright install chromium` inside
  the worktree's venv only when that task needs it (kept out of `requirements.txt`).

## 4. Finish and clean up

After the task's branch is **merged** (or abandoned with confirmation):

```bash
python scripts/worktree.py remove fix-rate-limiter
#   refuses if uncommitted changes exist or the branch is not merged;
#   use --force only when you consciously discard work
python scripts/worktree.py clean          # sweep ALL merged worktrees at once
```

Equivalent manual commands:

```bash
git -C .worktrees/fix-rate-limiter status          # must be clean first
git worktree remove .worktrees/fix-rate-limiter
git branch -d fix-rate-limiter                      # -d only works if merged
git worktree prune                                  # drop stale admin entries
```

Cleanup discipline:

- Delete a worktree **promptly** after merge — do not let `.worktrees/` accumulate.
- `git branch -d` (lowercase) is used on purpose: it refuses unmerged branches.
- `.venv` and local data live inside the worktree and vanish with it.

## 5. Helper script reference

`scripts/worktree.py` wraps the above with safety guards:

| Command | Effect |
|---|---|
| `create <name> [--base <ref>] [--no-venv]` | branch + worktree + `.venv`/`.env` bootstrap |
| `list` | worktrees + branch + dirty flag |
| `remove <name> [--force]` | delete one worktree (guards: dirty tree, unmerged branch) |
| `clean [--dry-run]` | remove every worktree whose branch is merged into `main` |

## 6. What never goes through a worktree

- Repo-level config edits that must apply globally (e.g. `.github/workflows`,
  baselines under `.github/data/`) can still be done on a task branch — via a
  worktree as usual; just merge before other tasks rebase.
- Do not point a task worktree's `MARKET_DB_PATH` at the same file while running
  the scheduler (`AUTO_UPDATE_TICKERS`) in both places — only one writer per DB.

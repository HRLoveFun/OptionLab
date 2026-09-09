"""Per-task git worktree manager (ADR 0009).

Domain:  developer workflow tooling.
Context: OptionLab isolates every dev task in its own git worktree under
         ``.worktrees/<task-name>/`` with a dedicated branch, its own ``.venv``
         and a copy of ``.env``. The main workspace stays on ``main`` and clean.
Contracts:
    create <name> [--base REF] [--no-venv]   branch + worktree + bootstrap
    list                                     table of worktrees
    remove <name> [--force]                  guarded deletion of one worktree
    clean [--dry-run]                        sweep all worktrees merged into main
Dependencies: stdlib only (subprocess, argparse, pathlib, venv module optional).

All git history is shared via the repo's ``.git`` dir, so worktrees are cheap.
Deletion is refused when the worktree has uncommitted changes or its branch is
not merged (unless ``--force``), which makes ``clean`` safe to run routinely.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKTREE_ROOT = Path(os.environ.get("WORKTREE_ROOT", str(REPO_ROOT / ".worktrees")))


def _git(*args: str, cwd: Path | None = None) -> str:
    """Run a git command and return stripped stdout; raise SystemExit on failure."""
    result = subprocess.run(
        ["git", "-C", str(cwd or REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"[worktree] git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def _worktree_path(name: str) -> Path:
    return WORKTREE_ROOT / name


def _is_dirty(path: Path) -> bool:
    return bool(_git("status", "--porcelain", cwd=path))


def _is_merged(branch: str) -> bool:
    merged = _git("branch", "--merged", "main")
    # prefixes: `*` = current branch, `+` = checked out in another worktree
    return any(line.strip().lstrip("*+ ").rstrip() == branch for line in merged.splitlines())


def _bootstrap(path: Path) -> None:
    """Create .venv, install requirements, copy .env — best effort, isolated per worktree."""
    import venv

    print(f"[worktree] bootstrapping .venv in {path} ...")
    venv.EnvBuilder(with_pip=True, clear=False).create(path / ".venv")
    pip = path / ".venv" / "bin" / "pip"
    req = REPO_ROOT / "requirements.txt"
    if req.exists():
        subprocess.run([str(pip), "install", "-q", "-r", str(req)], check=False)
    env_src = REPO_ROOT / ".env"
    if env_src.exists() and not (path / ".env").exists():
        (path / ".env").write_text(env_src.read_text())
        print("[worktree] copied .env")


def cmd_create(args: argparse.Namespace) -> None:
    path = _worktree_path(args.name)
    if path.exists():
        sys.exit(f"[worktree] worktree already exists: {path}")
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", str(path), "-b", args.name, args.base)
    print(f"[worktree] created {path} on branch {args.name}")
    if not args.no_venv:
        _bootstrap(path)
    print(f"[worktree] done. cd {path} && source .venv/bin/activate")


def cmd_list(_: argparse.Namespace) -> None:
    out = _git("worktree", "list", "--porcelain")
    entry: dict[str, str] = {}
    for line in out.splitlines():
        if not line:
            wt = entry.get("worktree", "")
            if wt:
                dirty = _is_dirty(Path(wt))
                flag = " (dirty)" if dirty else ""
                print(f"{wt}  branch={entry.get('branch', '-').replace('refs/heads/', '')}{flag}")
            entry = {}
            continue
        key, _, value = line.partition(" ")
        entry[key] = value
    if entry.get("worktree"):
        dirty = _is_dirty(Path(entry["worktree"]))
        print(
            f"{entry['worktree']}  branch={entry.get('branch', '-').replace('refs/heads/', '')}"
            f"{' (dirty)' if dirty else ''}"
        )


def _remove(path: Path, branch: str, force: bool) -> None:
    if _is_dirty(path) and not force:
        sys.exit(f"[worktree] {path} has uncommitted changes; commit them or use --force")
    if branch and not _is_merged(branch) and not force:
        sys.exit(f"[worktree] branch {branch} is not merged into main; merge it first or use --force")
    remove_args = ["worktree", "remove"] + (["--force"] if force else []) + [str(path)]
    _git(*remove_args)
    if branch:
        _git("branch", "-d", branch)  # -d refuses unmerged branches (second guard)
    print(f"[worktree] removed {path}" + (f" and branch {branch}" if branch else ""))


def cmd_remove(args: argparse.Namespace) -> None:
    path = _worktree_path(args.name)
    if not path.exists():
        sys.exit(f"[worktree] no such worktree: {path}")
    out = _git("worktree", "list", "--porcelain")
    branch = ""
    for line in out.splitlines():
        if line.startswith("worktree ") and path.samefile(Path(line.split(" ", 1)[1])):
            continue
        if line.startswith("branch "):
            branch = line.split(" ", 1)[1].replace("refs/heads/", "")
    _remove(path, branch, args.force)


def cmd_clean(args: argparse.Namespace) -> None:
    out = _git("worktree", "list", "--porcelain")
    entries: list[tuple[Path, str]] = []
    entry: dict[str, str] = {}
    for line in out.splitlines() + [""]:
        if not line:
            wt = entry.get("worktree")
            if wt and Path(wt).parent == WORKTREE_ROOT.resolve():
                entries.append((Path(wt), entry.get("branch", "").replace("refs/heads/", "")))
            entry = {}
            continue
        key, _, value = line.partition(" ")
        entry[key] = value

    if not entries:
        print("[worktree] nothing to clean")
        return
    for path, branch in entries:
        merged = _is_merged(branch) if branch else False
        dirty = _is_dirty(path)
        if args.dry_run:
            state = "MERGED" if merged else ("DIRTY" if dirty else "UNMERGED")
            print(f"[dry-run] {path} branch={branch or '-'} [{state}]")
            continue
        if not merged:
            print(f"[worktree] skip {path} (branch {branch or '?'} not merged into main)")
            continue
        _remove(path, branch, force=False)
    _git("worktree", "prune")


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-task git worktree manager (ADR 0009)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="create a task worktree with its own branch and .venv")
    p.add_argument("name", help="task/branch name (kebab-case)")
    p.add_argument("--base", default="main", help="base ref (default: main)")
    p.add_argument("--no-venv", action="store_true", help="skip .venv/.env bootstrap")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("list", help="list worktrees with branch and dirty flag")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("remove", help="remove one worktree (guarded)")
    p.add_argument("name")
    p.add_argument("--force", action="store_true", help="override dirty/unmerged guards")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("clean", help="remove all worktrees whose branch is merged into main")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

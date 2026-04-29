#!/usr/bin/env python3
"""Find candidates for documentation drift updates.

Output: JSON array on stdout, each entry describing a single doc-drift
candidate that an LLM (or human) could turn into a patch.

This is the *deterministic* half of the doc-drift workflow. The LLM call
in scripts/draft_doc_updates.py reads this output and produces patches.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CONST_RE = re.compile(r"^([A-Z_][A-Z0-9_]{2,})\s*=\s*(-?\d+\.?\d*|-?\d*\.\d+)\s*$", re.MULTILINE)


def _git_changed_since_last_drift_pr() -> list[Path]:
    """Files changed on main since this branch was last opened — best effort."""
    try:
        # Default: look at last 2 weeks of changes
        out = subprocess.check_output(
            ["git", "log", "--since=2.weeks", "--name-only", "--pretty=format:", "--", "core", "data_pipeline", "services"],
            cwd=REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []
    seen = set()
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line in seen:
            continue
        seen.add(line)
        p = REPO_ROOT / line
        if p.exists() and p.suffix == ".py":
            files.append(p)
    return files


def _candidates_untagged_constants(files: list[Path]) -> list[dict]:
    out = []
    tag_re = re.compile(r"#\s*(WHY|CONSTRAINT|TRADEOFF|INVARIANT|DOMAIN):")
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = CONST_RE.match(line)
            if not m:
                continue
            if m.group(2) in {"0", "1", "-1", "0.0", "1.0"}:
                continue
            if any(tag_re.search(lines[j]) for j in range(max(0, i - 5), i)):
                continue
            out.append(
                {
                    "kind": "untagged-constant",
                    "file": str(path.relative_to(REPO_ROOT)),
                    "line": i + 1,
                    "name": m.group(1),
                    "value": m.group(2),
                    "suggestion": f"Add a # DOMAIN: comment explaining why {m.group(1)}={m.group(2)} is a domain constant.",
                }
            )
    return out


def _candidates_missing_module_docstring(files: list[Path]) -> list[dict]:
    out = []
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(getattr(tree.body[0], "value", None), ast.Constant):
            continue
        out.append(
            {
                "kind": "missing-module-docstring",
                "file": str(path.relative_to(REPO_ROOT)),
                "line": 1,
                "suggestion": "Generate a Context: ... docstring summarising the module's responsibility.",
            }
        )
    return out


def _candidates_terse_test_names(_files: list[Path]) -> list[dict]:
    out = []
    test_dir = REPO_ROOT / "tests"
    if not test_dir.is_dir():
        return out
    bad_re = re.compile(r"^def\s+(test_[a-z_]{1,8})\s*\(", re.MULTILINE)
    for path in test_dir.rglob("test_*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in bad_re.finditer(text):
            name = m.group(1)
            # Only flag if name <= 12 chars (very terse)
            if len(name) > 12:
                continue
            line = text.count("\n", 0, m.start()) + 1
            out.append(
                {
                    "kind": "terse-test-name",
                    "file": str(path.relative_to(REPO_ROOT)),
                    "line": line,
                    "name": name,
                    "suggestion": "Rename to express the asserted behaviour, not just the symbol under test.",
                }
            )
    return out


def main() -> int:
    files = _git_changed_since_last_drift_pr()
    candidates = []
    candidates += _candidates_untagged_constants(files)
    candidates += _candidates_missing_module_docstring(files)
    candidates += _candidates_terse_test_names([])  # always scans tests/
    # Cap output for readability
    cap = 50
    json.dump(candidates[:cap], sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

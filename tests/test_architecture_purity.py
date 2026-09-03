"""Architecture contract tests: core/ subpackages stay pure.

Domain:    Tests — Architecture Purity Contracts
Context:
  - doc_guard.py blocks violating *edits*, but a suppressed violation
    (``# doc-guard: allow=core-purity``) can otherwise persist silently.
    These tests assert the same invariant at the test layer, so every
    remaining violation stays visible in the test report and can be counted
    down to zero instead of being forgotten.
  - The violation registry lives in docs/architecture_review.md §2.
Contracts:
  - test_core_subpackage_has_no_io_or_framework_imports: for every core/
    subpackage, no absolute import of an I/O or framework package, except
    lines explicitly carrying ``doc-guard: allow=core-purity``.
Dependencies UPWARD:
  - (none — stdlib + pytest only)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "core"

# INVARIANT: core/ is pure computation — no DB, no network, no Flask, no app.
FORBIDDEN_ROOTS = {
    "data_pipeline",
    "flask",
    "services",
    "routes",
    "app",
    "sqlite3",
    "yfinance",
    "requests",
}

SUBPACKAGES = sorted(p.name for p in CORE.iterdir() if p.is_dir() and not p.name.startswith("__"))


def _absolute_import_heads(path: Path) -> list[tuple[int, str]]:
    """Every absolutely-imported top-level package with its 1-based line."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        mods: list[str] = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods = [node.module]
        for m in mods:
            out.append((getattr(node, "lineno", 1), m.split(".", 1)[0]))
    return out


@pytest.mark.parametrize("pkg", SUBPACKAGES)
def test_core_subpackage_has_no_io_or_framework_imports(pkg):
    offenders: list[str] = []
    for py in sorted((CORE / pkg).rglob("*.py")):
        lines = py.read_text(encoding="utf-8").splitlines()
        for lineno, head in _absolute_import_heads(py):
            if head not in FORBIDDEN_ROOTS:
                continue
            line = lines[lineno - 1] if lineno - 1 < len(lines) else ""
            if "doc-guard: allow=core-purity" in line:
                # Registered tech debt — tracked in docs/architecture_review.md §2.
                continue
            offenders.append(f"{py.relative_to(REPO_ROOT)}:{lineno} imports '{head}'")
    assert not offenders, "core/ purity violated (fetch upstream and pass data in, ADR 0001):\n" + "\n".join(offenders)

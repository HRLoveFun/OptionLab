"""Architecture contract tests: core/ purity and the data_pipeline layer graph.

Domain:    Tests — Architecture Purity Contracts
Context:
  - doc_guard.py blocks violating *edits*, but a suppressed violation
    (``# doc-guard: allow=core-purity``) can otherwise persist silently.
    These tests assert the same invariant at the test layer, so every
    remaining violation stays visible in the test report and can be counted
    down to zero instead of being forgotten.
  - The violation registry lives in docs/architecture_review.md §2.
  - Batch B3 (ADR 0011) split ``data_pipeline/`` into six layers
    (providers / store / ingest / transform / read / orchestrate). The declared
    edges live in ``scripts/doc_guard.py::_ALLOWED_DEPS`` and are mirrored in
    ``scripts/arch_metrics.py`` — two copies, hence the sync test below.
Contracts:
  - test_core_subpackage_has_no_io_or_framework_imports: for every core/
    subpackage, no absolute import of an I/O or framework package, except
    lines explicitly carrying ``doc-guard: allow=core-purity``.
  - test_data_pipeline_import_graph_matches_declared_layers: the real import
    graph conforms to the declared layer table.
  - test_transform_never_imports_providers: processing stays provider-agnostic
    (ADR 0011 §5.2) — it only sees canonical tables.
  - test_layer_tables_are_in_sync: doc_guard and arch_metrics agree.
Dependencies UPWARD:
  - (none — stdlib + pytest only)
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE = REPO_ROOT / "core"
DATA_PIPELINE = REPO_ROOT / "data_pipeline"


def _load_script(name: str):
    """Import a ``scripts/*.py`` module (scripts/ is not a package).

    WHY exec_module: the two guard scripts are standalone (no third-party
    imports, runnable from pre-commit) and must stay that way, so the tests
    reach into them rather than the other way round.
    """
    spec = importlib.util.spec_from_file_location(f"_guard_{name}", REPO_ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # WHY register first: doc_guard defines dataclasses, and @dataclass resolves
    # type hints through sys.modules[cls.__module__] at class-creation time.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def test_core_has_zero_data_pipeline_imports():
    """B4 exit criterion: no suppression markers, no core→data_pipeline edge left.

    Stricter than ``test_core_subpackage_has_no_io_or_framework_imports`` above:
    that one honours ``# doc-guard: allow=core-purity`` for registered debt. Batch
    B4 closed the debt, so this test refuses the marker entirely — re-introducing
    one fails here even if doc_guard would accept it.
    """
    guard = _load_script("doc_guard")
    offenders: list[str] = []
    for py in sorted(CORE.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        for lineno, head in guard._imported_heads(py):
            if head == "data_pipeline" or head in guard.DATA_PIPELINE_SUBLAYERS:
                offenders.append(f"{py.relative_to(REPO_ROOT)}:{lineno} imports {head}")
    assert not offenders, (
        "core/ must not import data_pipeline (fetch upstream and pass data in, ADR 0001):\n" + "\n".join(offenders)
    )


def test_data_pipeline_import_graph_matches_declared_layers():
    """Every data_pipeline/ import must point at an allowed layer.

    This is the test-layer twin of doc_guard's ``import-direction`` rule, with
    sub-package granularity: ``data_pipeline.store.db`` counts as ``store``.
    """
    guard = _load_script("doc_guard")
    offenders: list[str] = []
    for py in sorted(DATA_PIPELINE.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        layer = guard._layer_of(py)
        if layer is None:
            continue
        allowed = guard._ALLOWED_DEPS[layer]
        for lineno, head in guard._imported_heads(py):
            if head not in guard._ALLOWED_DEPS or head == layer:
                continue
            if head in allowed or guard._is_suppressed_at(py, lineno, "import-direction"):
                continue
            offenders.append(f"{py.relative_to(REPO_ROOT)}:{lineno}: {layer} -> {head}")
    assert not offenders, "data_pipeline layer graph violated (see scripts/doc_guard.py::_ALLOWED_DEPS):\n" + "\n".join(
        offenders
    )


def test_transform_never_imports_providers():
    """INVARIANT (ADR 0011 §5.2): processing is provider-agnostic.

    ``transform/`` reads canonical tables only. ``read/`` is allowed to reach
    the provider for the spot fallback (recorded as a deviation in the plan §8).
    """
    guard = _load_script("doc_guard")
    offenders: list[str] = []
    for py in sorted((DATA_PIPELINE / "transform").rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        for lineno, head in guard._imported_heads(py):
            if head == "providers":
                offenders.append(f"{py.relative_to(REPO_ROOT)}:{lineno}")
    assert not offenders, "transform/ must not import providers/:\n" + "\n".join(offenders)


def test_layer_tables_are_in_sync():
    """``doc_guard`` and ``arch_metrics`` each carry a copy of the layer table."""
    doc_guard = _load_script("doc_guard")
    arch_metrics = _load_script("arch_metrics")
    assert doc_guard._ALLOWED_DEPS == arch_metrics.ALLOWED_DEPS
    assert doc_guard.DATA_PIPELINE_SUBLAYERS == arch_metrics.DATA_PIPELINE_SUBLAYERS

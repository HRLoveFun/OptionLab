#!/usr/bin/env python3
"""Architecture metrics for OptionLab — coupling, cycles, drift, dead code.

Run from repo root:

    python scripts/arch_metrics.py                  # human-readable report
    python scripts/arch_metrics.py --json           # machine-readable report
    python scripts/arch_metrics.py --update-baseline  # write .github/data/arch_baseline.json
    python scripts/arch_metrics.py --check          # exit 1 if worse than baseline

Exit code 0 = metrics at or better than baseline (or no baseline). Non-zero =
a tracked metric regressed, so CI can fail the build on architectural drift.

Zero third-party dependencies (stdlib only), mirroring scripts/doc_guard.py,
so it runs in pre-commit and CI without an install step. WHAT IT MEASURES —
the three views the arch review found most diagnostic:

1. fan-in / fan-out per module  (coupling; high fan-out = change-magnet)
2. layer-edge violations        (drift between the declared and real layering)
3. import cycles                (Tarjan SCC over the file-level import graph)

plus god files (>400 lines) and dead-code candidates (fan-in == 0). Baselines
live in .github/data/arch_baseline.json; commit baseline updates together with
the change that caused them.

Domain:    Scripts — Architecture Metrics
Context:
  - Feeds the 8-dimension review scorecard in docs/architecture_review.md.
  - The allowed layer-edge table MUST be kept in sync with
    scripts/doc_guard.py::_ALLOWED_DEPS (same invariant, two consumers:
    doc_guard blocks edits; this script tracks trend).
Dependencies UPWARD:
  - (none — stdlib only)
Dependencies DOWNWARD:
  - CI (arch drift gate), docs/architecture_review.md
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOTS = ("app.py", "routes", "services", "core", "data_pipeline", "utils")
BASELINE_PATH = REPO_ROOT / ".github" / "data" / "arch_baseline.json"

GOD_FILE_LINES = 400

# KEEP IN SYNC with scripts/doc_guard.py::_ALLOWED_DEPS.
ALLOWED_DEPS: dict[str, set[str]] = {
    "app": {"routes", "services", "core", "data_pipeline", "utils"},
    "routes": {"services", "data_pipeline", "utils"},
    "services": {"core", "data_pipeline", "utils"},
    "core": {"data_pipeline", "utils"},
    "data_pipeline": {"utils"},
    "utils": set(),
}
BUSINESS_LAYERS = set(ALLOWED_DEPS)


def collect_files() -> list[Path]:
    out: list[Path] = []
    for sub in SCAN_ROOTS:
        p = REPO_ROOT / sub
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(x for x in p.rglob("*.py") if "__pycache__" not in x.parts)
    return sorted(out)


def layer_of(rel: Path) -> str:
    return "app" if rel.as_posix() == "app.py" else rel.parts[0]


def resolve_import(module: str | None, name: str | None, level: int, src: Path) -> Path | None:
    """Map an import to a repo file, if it points inside the scanned tree."""
    if level:
        base = src.parent
        for _ in range(level - 1):
            base = base.parent
        target_dir = base
        parts: list[str] = []
        if module:
            parts = module.split(".")
    else:
        if not module:
            return None
        head = module.split(".", 1)[0]
        if head not in BUSINESS_LAYERS:
            return None
        target_dir = REPO_ROOT
        parts = module.split(".")

    cand = target_dir.joinpath(*parts) if parts else target_dir
    if name:
        # ``from package import module`` resolves to the submodule when it exists.
        sub = cand / f"{name}.py"
        if sub.is_file():
            return sub
    for c in (cand.with_suffix(".py"), cand / "__init__.py"):
        if c.is_file():
            return c
    return None


def build_graph(files: list[Path]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {f.relative_to(REPO_ROOT).as_posix(): set() for f in files}
    for src in files:
        src_key = src.relative_to(REPO_ROOT).as_posix()
        try:
            tree = ast.parse(src.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    t = resolve_import(a.name, None, 0, src)
                    if t:
                        graph[src_key].add(t.relative_to(REPO_ROOT).as_posix())
            elif isinstance(node, ast.ImportFrom):
                if any(a.name == "*" for a in node.names):
                    # ``from pkg.mod import *`` still creates a real edge to mod.
                    t = resolve_import(node.module, None, node.level, src)
                    if t and t != src:
                        graph[src_key].add(t.relative_to(REPO_ROOT).as_posix())
                    continue
                for a in node.names:
                    if a.name == "*":
                        continue
                    t = resolve_import(node.module, a.name, node.level, src)
                    if t and t != src:
                        graph[src_key].add(t.relative_to(REPO_ROOT).as_posix())
    return graph


def tarjan_scc(graph: dict[str, set[str]]) -> list[list[str]]:
    """Iterative Tarjan — returns SCCs of size > 1 (cycles) plus self-loops."""
    index = {}
    low = {}
    on_stack = set()
    stack: list[str] = []
    counter = [0]
    sccs: list[list[str]] = []

    for root in graph:
        if root in index:
            continue
        work = [(root, iter(sorted(graph[root])))]
        index[root] = low[root] = counter[0]
        counter[0] += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in graph:
                    continue
                if nxt not in index:
                    index[nxt] = low[nxt] = counter[0]
                    counter[0] += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(sorted(graph[nxt]))))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                scc: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1:
                    sccs.append(sorted(scc))
    return sccs


def layer_edges(graph: dict[str, set[str]]) -> list[tuple[str, str, str]]:
    """Disallowed layer-to-layer edges: (src_layer, dst_layer, example_edge)."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str, str]] = []
    for src, dsts in graph.items():
        s = layer_of(Path(src))
        for d in dsts:
            dl = layer_of(Path(d))
            if dl == s or dl in ALLOWED_DEPS.get(s, set()):
                continue
            if (s, dl) in seen:
                continue
            seen.add((s, dl))
            out.append((s, dl, f"{src} -> {d}"))
    return out


def top_by(graph: dict[str, set[str]], key: str, n: int = 5) -> list[tuple[str, int]]:
    if key == "fan-out":
        pairs = [(m, len(d)) for m, d in graph.items()]
    else:  # fan-in
        fan_in: dict[str, int] = defaultdict(int)
        for d in graph.values():
            for t in d:
                fan_in[t] += 1
        pairs = [(m, c) for m, c in fan_in.items() if m in graph]
    return sorted(pairs, key=lambda x: (-x[1], x[0]))[:n]


def god_files() -> list[tuple[str, int]]:
    out = []
    for sub in SCAN_ROOTS:
        p = REPO_ROOT / sub
        files = [p] if p.is_file() else list(p.rglob("*.py"))
        for f in files:
            if "__pycache__" in f.parts:
                continue
            lines = len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
            if lines > GOD_FILE_LINES:
                out.append((f.relative_to(REPO_ROOT).as_posix(), lines))
    return sorted(out, key=lambda x: -x[1])


def dead_code_candidates(graph: dict[str, set[str]]) -> list[str]:
    fan_in: dict[str, int] = defaultdict(int)
    for d in graph.values():
        for t in d:
            fan_in[t] += 1
    out = []
    for m in graph:
        p = Path(m)
        if p.name == "__init__.py" or m == "app.py" or len(p.parts) < 2:
            continue
        if fan_in.get(m, 0) == 0:
            out.append(m)
    return sorted(out)


def collect() -> dict:
    files = collect_files()
    graph = build_graph(files)
    cycles = tarjan_scc(graph)
    edges = layer_edges(graph)
    return {
        "modules": len(graph),
        "import_edges": sum(len(d) for d in graph.values()),
        "layer_violations": [{"from": s, "to": t, "example": e} for s, t, e in edges],
        "cycles": cycles,
        "top_fan_out": top_by(graph, "fan-out"),
        "top_fan_in": top_by(graph, "fan-in"),
        "god_files": god_files(),
        "dead_code_candidates": dead_code_candidates(graph),
    }


def tracked(report: dict) -> dict:
    """The small set of numbers --check compares against the baseline."""
    return {
        "layer_violations": len(report["layer_violations"]),
        "cycles": len(report["cycles"]),
        "god_files": len(report["god_files"]),
        "dead_code_candidates": len(report["dead_code_candidates"]),
    }


def render(report: dict) -> str:
    def section(title: str, rows: list[str]) -> list[str]:
        return [title, *(rows or ["  (none)"]), ""]

    parts = [
        f"modules={report['modules']}  import_edges={report['import_edges']}",
        "",
    ]
    parts += section(
        "Layer-edge violations:",
        [f"  {v['from']} -> {v['to']}   e.g. {v['example']}" for v in report["layer_violations"]],
    )
    parts += section(
        f"Import cycles: {len(report['cycles'])}",
        [f"  [{' <-> '.join(c)}]" for c in report["cycles"]],
    )
    parts += section(
        "Top fan-out (change magnets):",
        [f"  {c:>3}  {m}" for m, c in report["top_fan_out"]],
    )
    parts += section(
        "Top fan-in (stability points):",
        [f"  {c:>3}  {m}" for m, c in report["top_fan_in"]],
    )
    parts += section(
        f"God files (>{GOD_FILE_LINES} lines):",
        [f"  {c:>5}  {m}" for m, c in report["god_files"]],
    )
    parts += section(
        "Dead-code candidates (fan-in == 0):",
        [f"  {m}" for m in report["dead_code_candidates"]],
    )
    return "\n".join(parts) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--check", action="store_true", help="compare against baseline; exit 1 on regression")
    ap.add_argument("--update-baseline", action="store_true", help="write the current tracked metrics as baseline")
    args = ap.parse_args()

    report = collect()

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    if args.update_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(tracked(report), indent=2) + "\n")
        print(f"baseline written: {BASELINE_PATH.relative_to(REPO_ROOT)}")
        print(json.dumps(tracked(report), indent=2))
        return 0

    if args.check:
        if not BASELINE_PATH.exists():
            print(
                f"arch-metrics: no baseline at {BASELINE_PATH.relative_to(REPO_ROOT)}; "
                f"create one with --update-baseline"
            )
            return 0
        base = json.loads(BASELINE_PATH.read_text())
        cur = tracked(report)
        regressed = {k: (base.get(k, 0), v) for k, v in cur.items() if v > base.get(k, 0)}
        if regressed:
            print("arch-metrics: REGRESSION vs baseline", file=sys.stderr)
            for k, (b, c) in sorted(regressed.items()):
                print(f"  {k}: {b} -> {c}", file=sys.stderr)
            print(json.dumps(cur, indent=2), file=sys.stderr)
            return 1
        print(f"arch-metrics: ok {json.dumps(cur)}")
        return 0

    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

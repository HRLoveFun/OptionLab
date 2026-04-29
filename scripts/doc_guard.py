#!/usr/bin/env python3
"""Deterministic L1 documentation/tag guards.

Run from repo root:

    python scripts/doc_guard.py            # all rules
    python scripts/doc_guard.py --rule yfinance-throttle
    python scripts/doc_guard.py --files data_pipeline/foo.py core/bar.py

Exit code 0 = clean. Non-zero = violations printed to stderr.

Rules are intentionally simple regex / AST heuristics. False positives are
expected occasionally; suppress with a `# doc-guard: allow=<rule>` comment
on the offending line.

This script must have **no third-party dependencies** so it can run in
pre-commit and CI without an extra install step.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ── Tag vocabulary ────────────────────────────────────────────────
CANONICAL_TAGS = {"WHY", "CONSTRAINT", "TRADEOFF", "INVARIANT", "DOMAIN", "HACK", "WORKAROUND"}
# Anything that looks like a tag but isn't canonical (case-insensitive) — flag it.
TAG_PATTERN = re.compile(r"#\s*([A-Z][A-Z_]{1,15}):")

# Allowed commit type prefixes
COMMIT_TYPES = {"feat", "fix", "refactor", "docs", "test", "chore", "revert", "perf", "ci", "style", "build"}


@dataclass
class Violation:
    rule: str
    path: str
    line: int
    message: str

    def format(self) -> str:
        return f"{self.path}:{self.line}: [{self.rule}] {self.message}"


@dataclass
class Context:
    files: list[Path]
    violations: list[Violation] = field(default_factory=list)

    def add(self, rule: str, path: Path, line: int, msg: str) -> None:
        try:
            rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        except ValueError:
            rel = path
        self.violations.append(Violation(rule, str(rel), line, msg))


def _read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []


def _is_suppressed(line: str, rule: str) -> bool:
    m = re.search(r"doc-guard:\s*allow=([\w,-]+)", line)
    if not m:
        return False
    return rule in {x.strip() for x in m.group(1).split(",")}


# ── Rule: tag-syntax ─────────────────────────────────────────────
def rule_tag_syntax(ctx: Context) -> None:
    for path in ctx.files:
        if path.suffix not in (".py",):
            continue
        for i, line in enumerate(_read(path), 1):
            for m in TAG_PATTERN.finditer(line):
                tag = m.group(1)
                if tag in CANONICAL_TAGS:
                    continue
                # Allow obvious non-tag uses: HTTP, JSON, etc — only flag if line
                # starts with whitespace + '#' (so it's a comment, not e.g. a string)
                if not re.match(r"^\s*#", line):
                    continue
                # Common false positives that look like UPPER:
                if tag in {"TODO", "FIXME", "NOTE", "XXX", "HTTP", "HTTPS", "URL", "API", "ID", "OK", "NB"}:
                    continue
                if _is_suppressed(line, "tag-syntax"):
                    continue
                ctx.add(
                    "tag-syntax",
                    path,
                    i,
                    f"non-canonical tag '{tag}:' — use one of {sorted(CANONICAL_TAGS)} or rewrite as plain comment",
                )


# ── Rule: yfinance-throttle ──────────────────────────────────────
_YF_CALL_RE = re.compile(r"\byf\.(download|Ticker)\s*\(")


def rule_yfinance_throttle(ctx: Context) -> None:
    """Each yf.download / yf.Ticker call outside yf_client.py and downloader.py
    must have a yf_throttle() call within the previous 5 lines, OR be marked
    with `# doc-guard: allow=yfinance-throttle`.
    """
    allowed_files = {
        REPO_ROOT / "data_pipeline" / "yf_client.py",
        REPO_ROOT / "data_pipeline" / "downloader.py",
    }
    for path in ctx.files:
        if path.suffix != ".py":
            continue
        if path.resolve() in allowed_files:
            continue
        if "tests/" in str(path):
            continue
        lines = _read(path)
        for i, line in enumerate(lines, 1):
            if not _YF_CALL_RE.search(line):
                continue
            if _is_suppressed(line, "yfinance-throttle"):
                continue
            window = "\n".join(lines[max(0, i - 6) : i])
            if "yf_throttle()" in window:
                continue
            ctx.add(
                "yfinance-throttle",
                path,
                i,
                "yfinance call without preceding yf_throttle() — see ADR 0005 / docs/constraints.md §2",
            )


# ── Rule: yfinance-session-kwarg ─────────────────────────────────
_YF_SESSION_RE = re.compile(r"\byf\.[A-Za-z_]+\([^)]*session\s*=", re.DOTALL)


def rule_yfinance_session_kwarg(ctx: Context) -> None:
    for path in ctx.files:
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in _YF_SESSION_RE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            ctx.add(
                "yfinance-session-kwarg",
                path,
                line,
                "passing session= to yfinance silently fails (curl_cffi). See docs/constraints.md §2",
            )


# ── Rule: sqlite-bypass ──────────────────────────────────────────
_SQLITE_CONNECT_RE = re.compile(r"\bsqlite3\.connect\(")


def rule_sqlite_bypass(ctx: Context) -> None:
    allowed = {REPO_ROOT / "data_pipeline" / "db.py"}
    for path in ctx.files:
        if path.suffix != ".py":
            continue
        if path.resolve() in allowed:
            continue
        if "tests/" in str(path) or "scripts/" in str(path):
            continue
        for i, line in enumerate(_read(path), 1):
            if _SQLITE_CONNECT_RE.search(line) and not _is_suppressed(line, "sqlite-bypass"):
                ctx.add(
                    "sqlite-bypass",
                    path,
                    i,
                    "direct sqlite3.connect outside data_pipeline/db.py — bypasses WAL pragmas (ADR 0003)",
                )


# ── Rule: import-direction ───────────────────────────────────────
_LAYERS = {"app": 0, "services": 1, "core": 2, "data_pipeline": 3, "utils": 99}


def _layer_of(path: Path) -> int | None:
    try:
        rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
    except ValueError:
        return None
    head = rel.parts[0] if rel.parts else ""
    if head == "app.py":
        return _LAYERS["app"]
    return _LAYERS.get(head)


def rule_import_direction(ctx: Context) -> None:
    for path in ctx.files:
        if path.suffix != ".py":
            continue
        layer = _layer_of(path)
        if layer is None or layer == _LAYERS["utils"]:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            mods = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module]
            for m in mods:
                head = m.split(".", 1)[0]
                target = _LAYERS.get(head)
                if target is None or target == _LAYERS["utils"]:
                    continue
                if target < layer:  # importing a higher layer
                    src_layer = next((name for name, lv in _LAYERS.items() if lv == layer), "?")
                    ctx.add(
                        "import-direction",
                        path,
                        getattr(node, "lineno", 1),
                        f"layer '{src_layer}' must not import from '{head}' (ADR 0001)",
                    )


# ── Rule: module-docstring ───────────────────────────────────────
def rule_module_docstring(ctx: Context) -> None:
    for path in ctx.files:
        if path.suffix != ".py":
            continue
        try:
            rel = path.relative_to(REPO_ROOT) if path.is_absolute() else path
        except ValueError:
            continue
        if rel.parts and rel.parts[0] not in ("core", "data_pipeline", "services"):
            continue
        if rel.name.startswith("__"):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not (tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str)):
            ctx.add(
                "module-docstring",
                path,
                1,
                "module is missing a top-level docstring (Context: ... block expected)",
            )


# ── Rule: adr-link-integrity ─────────────────────────────────────
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def rule_adr_link_integrity(ctx: Context) -> None:
    docs = [
        REPO_ROOT / "docs" / "constraints.md",
        REPO_ROOT / "docs" / "glossary.md",
        *(REPO_ROOT / "docs" / "decisions").glob("*.md"),
    ]
    for path in docs:
        if not path.exists() or path not in ctx.files:
            continue
        for i, line in enumerate(_read(path), 1):
            for m in _LINK_RE.finditer(line):
                target = m.group(1).split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.exists():
                    ctx.add("adr-link-integrity", path, i, f"broken link to '{target}'")


# ── Rule: adr-index-fresh ────────────────────────────────────────
def rule_adr_index_fresh(ctx: Context) -> None:
    decisions_dir = REPO_ROOT / "docs" / "decisions"
    index = decisions_dir / "README.md"
    if not index.exists():
        return
    if index not in ctx.files and not any((decisions_dir / f.name) in ctx.files for f in decisions_dir.glob("*.md")):
        return
    files = sorted(p for p in decisions_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))
    text = index.read_text(encoding="utf-8")
    for f in files:
        if f.name not in text:
            ctx.add(
                "adr-index-fresh",
                index,
                1,
                f"ADR '{f.name}' not listed in README.md — run scripts/regen_adr_index.py",
            )


# ── Driver ───────────────────────────────────────────────────────
ALL_RULES = {
    "tag-syntax": rule_tag_syntax,
    "yfinance-throttle": rule_yfinance_throttle,
    "yfinance-session-kwarg": rule_yfinance_session_kwarg,
    "sqlite-bypass": rule_sqlite_bypass,
    "import-direction": rule_import_direction,
    "module-docstring": rule_module_docstring,
    "adr-link-integrity": rule_adr_link_integrity,
    "adr-index-fresh": rule_adr_index_fresh,
}


def collect_files(paths: list[str] | None) -> list[Path]:
    if paths:
        return [Path(p).resolve() for p in paths if Path(p).exists()]
    out: list[Path] = []
    for sub in ("app.py", "core", "data_pipeline", "services", "utils", "docs"):
        p = REPO_ROOT / sub
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(x for x in p.rglob("*") if x.is_file() and x.suffix in (".py", ".md"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", action="append", help="restrict to specific rule(s)")
    ap.add_argument("--files", nargs="*", help="restrict to specific files")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()

    ctx = Context(files=collect_files(args.files))
    rules = args.rule or list(ALL_RULES.keys())
    for r in rules:
        fn = ALL_RULES.get(r)
        if not fn:
            print(f"unknown rule: {r}", file=sys.stderr)
            return 2
        fn(ctx)

    if args.json:
        print(json.dumps([v.__dict__ for v in ctx.violations], indent=2))
    else:
        for v in ctx.violations:
            print(v.format(), file=sys.stderr)
        if ctx.violations:
            print(f"\ndoc-guard: {len(ctx.violations)} violation(s)", file=sys.stderr)
        else:
            print("doc-guard: clean", file=sys.stderr)
    return 1 if ctx.violations else 0


if __name__ == "__main__":
    sys.exit(main())

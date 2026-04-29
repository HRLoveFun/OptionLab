#!/usr/bin/env python3
"""Regenerate docs/decisions/README.md index from the ADR files.

Source of truth: each ADR file's first-line H1 (`# NNNN. Title`) and its
`- **Status**:` bullet. Rewrites README.md atomically. Idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DECISIONS = REPO_ROOT / "docs" / "decisions"
INDEX = DECISIONS / "README.md"

H1_RE = re.compile(r"^#\s+(\d{4})\.\s+(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^-\s+\*\*Status\*\*\s*:\s*(.+?)\s*$", re.MULTILINE)


def _entry(path: Path) -> tuple[str, str, str] | None:
    text = path.read_text(encoding="utf-8")
    h1 = H1_RE.search(text)
    status = STATUS_RE.search(text)
    if not h1:
        return None
    return h1.group(1), h1.group(2), (status.group(1) if status else "Unknown")


def render(entries: list[tuple[str, str, str, str]]) -> str:
    head = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    # Preserve everything above the "## Index" heading; replace table below.
    marker = "## Index"
    if marker in head:
        prefix = head.split(marker, 1)[0] + marker + "\n\n"
    else:
        prefix = (
            "# Architecture Decision Records\n\n"
            "Auto-generated index. Edit ADR files, not this table.\n\n"
            "## Index\n\n"
        )
    lines = ["| ID | Title | Status |", "|----|-------|--------|"]
    for nnnn, title, status, fname in entries:
        lines.append(f"| [{nnnn}]({fname}) | {title} | {status} |")
    return prefix + "\n".join(lines) + "\n"


def main() -> int:
    if not DECISIONS.is_dir():
        print(f"no decisions dir: {DECISIONS}", file=sys.stderr)
        return 1
    entries = []
    for p in sorted(DECISIONS.glob("[0-9][0-9][0-9][0-9]-*.md")):
        e = _entry(p)
        if e:
            entries.append((*e, p.name))
    new = render(entries)
    if INDEX.exists() and INDEX.read_text(encoding="utf-8") == new:
        print("regen_adr_index: no change")
        return 0
    INDEX.write_text(new, encoding="utf-8")
    print(f"regen_adr_index: rewrote {INDEX.relative_to(REPO_ROOT)} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

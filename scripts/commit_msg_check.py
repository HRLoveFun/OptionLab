#!/usr/bin/env python3
"""Validate commit message subject. Used as a pre-commit `commit-msg` hook.

Argv[1] is the path to the commit-message file. We accept the subject if:
- it starts with one of the canonical types followed by ':'
- OR is a merge / revert / fixup auto-message (passes through)
- OR contains '[skip-format]' anywhere
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CANONICAL = {"feat", "fix", "refactor", "docs", "test", "chore", "revert", "perf", "ci", "style", "build"}
SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(\([\w./-]+\))?!?:\s+\S")


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    msg = Path(sys.argv[1]).read_text(encoding="utf-8")
    subject = msg.lstrip().splitlines()[0] if msg.strip() else ""
    if not subject:
        print("commit-msg: empty message", file=sys.stderr)
        return 1
    if subject.startswith(("Merge ", "Revert ", "fixup!", "squash!")) or "[skip-format]" in msg:
        return 0
    m = SUBJECT_RE.match(subject)
    if not m:
        print(
            f"commit-msg: subject '{subject}' must match '<type>: <description>'",
            file=sys.stderr,
        )
        print(f"            allowed types: {sorted(CANONICAL)}", file=sys.stderr)
        return 1
    if m.group("type") not in CANONICAL:
        print(
            f"commit-msg: type '{m.group('type')}' not in {sorted(CANONICAL)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

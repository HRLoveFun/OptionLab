#!/usr/bin/env python3
"""Tag-coverage audit with regression baseline.

Counts canonical tags across the codebase and produces a report. CI fails
if the count of *uncovered* candidates grows relative to the baseline.

Usage:
    python scripts/audit_tags.py                 # report (exit 1 if regressed)
    python scripts/audit_tags.py --update-baseline   # accept current state
    python scripts/audit_tags.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / ".github" / "data" / "tag_baseline.json"

TAG_RE = re.compile(r"#\s*(WHY|CONSTRAINT|TRADEOFF|INVARIANT|DOMAIN|HACK|WORKAROUND):")

# A "candidate magic number" = module-level UPPER_CASE constant assigned
# to a numeric literal that's not 0/1/-1, in core/ or data_pipeline/.
CANDIDATE_RE = re.compile(r"^([A-Z_][A-Z0-9_]{2,})\s*=\s*(-?\d+\.?\d*|-?\d*\.\d+)\s*(?:#.*)?$", re.MULTILINE)
TRIVIAL = {"0", "1", "-1", "0.0", "1.0", "-1.0"}


def _scan_dirs() -> list[Path]:
    roots = [REPO_ROOT / "core", REPO_ROOT / "data_pipeline", REPO_ROOT / "services", REPO_ROOT / "utils"]
    return [p for r in roots if r.is_dir() for p in r.rglob("*.py")]


def _tag_above(lines: list[str], idx: int) -> bool:
    # consider the 5 preceding lines for any canonical tag
    for j in range(max(0, idx - 5), idx):
        if TAG_RE.search(lines[j]):
            return True
    return False


def collect() -> dict:
    by_tag: dict[str, int] = {t: 0 for t in ("WHY", "CONSTRAINT", "TRADEOFF", "INVARIANT", "DOMAIN", "HACK", "WORKAROUND")}
    uncovered_constants: list[str] = []
    files_scanned = 0
    for path in _scan_dirs():
        files_scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in TAG_RE.finditer(text):
            by_tag[m.group(1)] += 1
        # candidate constants
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = CANDIDATE_RE.match(line)
            if not m:
                continue
            value = m.group(2)
            if value in TRIVIAL:
                continue
            if _tag_above(lines, i):
                continue
            rel = path.relative_to(REPO_ROOT)
            uncovered_constants.append(f"{rel}:{i + 1}: {m.group(1)}={value}")
    return {
        "files_scanned": files_scanned,
        "tags_by_type": by_tag,
        "uncovered_constants_count": len(uncovered_constants),
        "uncovered_constants": sorted(uncovered_constants),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = collect()

    if args.json:
        print(json.dumps(report, indent=2))

    if args.update_baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"audit_tags: baseline updated ({report['uncovered_constants_count']} uncovered)")
        return 0

    if not BASELINE.exists():
        print("audit_tags: no baseline yet — run with --update-baseline once to lock it in", file=sys.stderr)
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    grew = report["uncovered_constants_count"] > baseline.get("uncovered_constants_count", 0)
    if not args.json:
        print(
            f"audit_tags: scanned {report['files_scanned']} files, "
            f"uncovered constants: {report['uncovered_constants_count']} "
            f"(baseline {baseline.get('uncovered_constants_count', 0)})"
        )
    if grew:
        new_items = sorted(set(report["uncovered_constants"]) - set(baseline.get("uncovered_constants", [])))
        print("audit_tags: REGRESSION — new uncovered constants:", file=sys.stderr)
        for it in new_items:
            print(f"  + {it}", file=sys.stderr)
        print("\nFix by adding a # DOMAIN: / # CONSTRAINT: comment above each, or run --update-baseline if intentional.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

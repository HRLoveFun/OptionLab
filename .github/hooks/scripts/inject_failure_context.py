#!/usr/bin/env python3
"""SessionStart hook: inject active failure context at the beginning of each session.

Reads the failure tracker and failure registry, finds unresolved patterns
that have been seen recently, and injects them as a system message so the
agent starts each session aware of recurring issues.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TRACKER_PATH = DATA_DIR / "failure_tracker.json"
REGISTRY_PATH = DATA_DIR / "failure-registry.yaml"

# Only surface patterns seen within the last 14 days
RECENCY_WINDOW_DAYS = 14


def load_tracker() -> dict:
    if TRACKER_PATH.exists():
        try:
            return json.loads(TRACKER_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"failures": {}}


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        try:
            return yaml.safe_load(REGISTRY_PATH.read_text()) or {}
        except (yaml.YAMLError, OSError):
            pass
    return {}


def main():
    tracker = load_tracker()
    registry = load_registry()
    patterns = registry.get("patterns", {})

    now = datetime.utcnow()
    cutoff = now - timedelta(days=RECENCY_WINDOW_DAYS)

    active_warnings = []

    for category, info in tracker.get("failures", {}).items():
        count = info.get("count", 0)
        last_seen_str = info.get("last_seen")
        if count < 1 or not last_seen_str:
            continue

        # Check recency
        try:
            last_seen = datetime.fromisoformat(last_seen_str)
            if last_seen < cutoff:
                continue
        except (ValueError, TypeError):
            continue

        # Enrich with registry data
        reg_entry = patterns.get(category, {})
        skill_pattern = reg_entry.get("skill_pattern", category)
        effective_level = reg_entry.get("effective_level", 1)
        related_files = reg_entry.get("related_files", [])
        resolved = reg_entry.get("resolved", False)

        if resolved:
            continue

        warning = f"- **{category}** ({skill_pattern}): seen {count}x, last {last_seen_str}"
        if count >= 3:
            warning += f" — escalation level {effective_level} recommended"
        if related_files:
            warning += f"\n  Files: {', '.join(related_files)}"

        active_warnings.append(warning)

    if not active_warnings:
        sys.exit(0)

    message = (
        "## Active Failure Patterns\n\n"
        "The following recurring failure patterns are currently active in this project. "
        "Consider these when diagnosing issues or writing tests.\n\n"
        + "\n".join(active_warnings)
        + "\n\nUse `/test-escalation` or `/debug-pipeline` to address these systematically."
    )

    result = {"systemMessage": message}
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()

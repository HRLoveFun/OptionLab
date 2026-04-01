#!/usr/bin/env python3
"""Post-test hook: analyze pytest output for recurring failure patterns.

Reads PostToolUse JSON from stdin. If the tool was a terminal command
containing 'pytest', parses the output for failure patterns and tracks
recurrence in a local JSON file. Uses the failure registry as the central
source of truth for pattern classification and escalation levels.

Features:
- Registry-aware classification (reads hook_regex from failure-registry.yaml)
- Timestamps on all tracker entries
- fcntl file locking for concurrent-safe tracker updates
- 7-day escalation cooldown to avoid repeated suggestions
"""

import fcntl
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TRACKER_PATH = DATA_DIR / "failure_tracker.json"
REGISTRY_PATH = DATA_DIR / "failure-registry.yaml"
ESCALATION_COOLDOWN_DAYS = 7


def load_registry() -> dict:
    """Load the failure registry (patterns, escalation levels, etc.)."""
    if REGISTRY_PATH.exists():
        try:
            return yaml.safe_load(REGISTRY_PATH.read_text()) or {}
        except (yaml.YAMLError, OSError):
            pass
    return {}


def load_tracker_locked(fp) -> dict:
    """Load tracker JSON from an already-locked file handle."""
    fp.seek(0)
    content = fp.read()
    if content.strip():
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
    return {"failures": {}}


def save_tracker_locked(fp, data: dict) -> None:
    """Write tracker JSON to an already-locked file handle."""
    fp.seek(0)
    fp.truncate()
    fp.write(json.dumps(data, indent=2))
    fp.flush()


def build_classifier(registry: dict) -> dict[str, str]:
    """Build category→regex map from the registry, with fallbacks."""
    patterns = {}
    for category, entry in registry.get("patterns", {}).items():
        regex = entry.get("hook_regex")
        if regex:
            patterns[category] = regex

    # Fallback patterns not in registry
    fallbacks = {
        "key-error": r"KeyError|column.*not found|missing.*column",
        "assertion-error": r"AssertionError|assert.*False|!=",
    }
    for cat, regex in fallbacks.items():
        if cat not in patterns:
            patterns[cat] = regex

    return patterns


def classify_failure(error_text: str, classifier: dict[str, str]) -> str:
    """Classify a test failure using registry-driven patterns."""
    for category, pattern in classifier.items():
        if re.search(pattern, error_text, re.IGNORECASE):
            return category
    return "other"


def extract_failures(output: str, classifier: dict[str, str]) -> list[dict]:
    """Extract failure info from pytest output."""
    failures = []
    for match in re.finditer(r"FAILED\s+(tests/\S+)(?:\s+-\s+(\S+):\s*(.*))?", output):
        test_path = match.group(1)
        error_type = match.group(2) or "Unknown"
        message = match.group(3) or ""
        category = classify_failure(f"{error_type}: {message}", classifier)
        failures.append(
            {
                "test": test_path,
                "error_type": error_type,
                "message": message[:200],
                "category": category,
            }
        )
    return failures


def check_cooldown(registry: dict, category: str) -> bool:
    """Return True if escalation for this category is within cooldown period."""
    entry = registry.get("patterns", {}).get(category, {})
    last_escalated = entry.get("last_escalated")
    if not last_escalated:
        return False
    try:
        ts = datetime.fromisoformat(last_escalated)
        return datetime.utcnow() - ts < timedelta(days=ESCALATION_COOLDOWN_DAYS)
    except (ValueError, TypeError):
        return False


def main():
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = hook_input.get("toolName", "")
    if tool_name not in ("run_in_terminal", "runTests"):
        sys.exit(0)

    tool_input = hook_input.get("toolInput", {})
    command = tool_input.get("command", "")
    tool_output = hook_input.get("toolOutput", "")

    is_pytest = "pytest" in command or tool_name == "runTests"
    if not is_pytest:
        sys.exit(0)

    # Load registry for classification
    registry = load_registry()
    classifier = build_classifier(registry)

    # Extract failures from output
    output_text = str(tool_output)
    failures = extract_failures(output_text, classifier)

    if not failures:
        sys.exit(0)

    now_iso = datetime.utcnow().isoformat(timespec="seconds")

    # Update tracker with file locking for concurrency safety
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    escalation_needed = []

    with open(TRACKER_PATH, "a+") as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        try:
            tracker = load_tracker_locked(fp)

            for f in failures:
                cat = f["category"]
                if cat not in tracker["failures"]:
                    tracker["failures"][cat] = {
                        "count": 0,
                        "first_seen": now_iso,
                        "last_seen": now_iso,
                        "recent": [],
                    }
                entry = tracker["failures"][cat]
                entry["count"] += 1
                entry["last_seen"] = now_iso
                entry["recent"].append(
                    {
                        "test": f["test"],
                        "error": f["error_type"],
                        "message": f["message"][:100],
                        "timestamp": now_iso,
                    }
                )
                # Keep only last 10 entries
                entry["recent"] = entry["recent"][-10:]

                if entry["count"] >= 3 and not check_cooldown(registry, cat):
                    escalation_needed.append(cat)

            save_tracker_locked(fp, tracker)
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)

    # Build system message with registry context
    reg_patterns = registry.get("patterns", {})
    messages = []
    for f in failures:
        messages.append(f"FAILED {f['test']} [{f['category']}]: {f['error_type']}")

    if escalation_needed:
        messages.append("")
        for cat in sorted(set(escalation_needed)):
            reg_entry = reg_patterns.get(cat, {})
            level = reg_entry.get("effective_level", 1)
            skill_pattern = reg_entry.get("skill_pattern", cat)
            related = reg_entry.get("related_files", [])
            count = tracker["failures"][cat]["count"]

            messages.append(
                f"⚠️ **{cat}** ({skill_pattern}): {count} occurrences — recommended escalation level {level}"
            )
            if related:
                messages.append(f"   Related files: {', '.join(related)}")

        messages.append("\nUse `/test-escalation` to upgrade testing strategy for these patterns.")

    result = {"systemMessage": "\n".join(messages)}
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()

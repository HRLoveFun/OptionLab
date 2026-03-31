#!/usr/bin/env bash
# Post-edit hook: check for architecture import violations in data_pipeline/ and core/
# Reads PostToolUse JSON from stdin, checks edited file for forbidden imports.
# Filters out commented lines. Logs violations persistently.
# Output: JSON with permissionDecision "ask" if violation found, else empty.

set -euo pipefail

VIOLATION_LOG=".github/data/import_violations.log"

# Read hook input from stdin
INPUT=$(cat)

# Extract the tool name and file path from the hook input
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('toolName',''))" 2>/dev/null || echo "")

# Only check after file edit operations
case "$TOOL_NAME" in
  edit_file|create_file|replace_string_in_file|multi_replace_string_in_file) ;;
  *) exit 0 ;;
esac

# Extract the file path
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Try different possible locations for the file path
for key in ('toolInput', 'input'):
    inp = d.get(key, {})
    if isinstance(inp, dict):
        for fkey in ('filePath', 'file_path', 'path'):
            if fkey in inp:
                print(inp[fkey])
                sys.exit(0)
# For multi_replace, check first replacement
replacements = d.get('toolInput', {}).get('replacements', [])
if replacements:
    print(replacements[0].get('filePath', ''))
" 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Helper: grep for imports in non-comment lines only
# Usage: check_imports FILE_PATH PATTERN
check_imports() {
  local file="$1"
  local pattern="$2"
  if [ -f "$file" ]; then
    # Filter out lines starting with # (with optional leading whitespace)
    grep -n "$pattern" "$file" 2>/dev/null | grep -v '^\s*[0-9]*:\s*#' || true
  fi
}

VIOLATIONS=""

# Check data_pipeline/ files — must not import from services/, core/, or app
if echo "$FILE_PATH" | grep -q "data_pipeline/"; then
  V=$(check_imports "$FILE_PATH" "from services\|from core\|import services\|import core\|from app \|import app")
  if [ -n "$V" ]; then
    VIOLATIONS="Architecture violation in $FILE_PATH (data_pipeline/ must not import from services/, core/, or app):\n$V"
  fi
  # Also check relative imports that go up to forbidden layers
  RV=$(check_imports "$FILE_PATH" "from \.\.\(services\|core\|app\)")
  if [ -n "$RV" ]; then
    VIOLATIONS="${VIOLATIONS}\nRelative import violation in $FILE_PATH:\n$RV"
  fi
fi

# Check core/ files — must not import from services/, flask, or app
if echo "$FILE_PATH" | grep -q "core/"; then
  V=$(check_imports "$FILE_PATH" "from services\|import services\|from flask\|import flask\|from app \|import app")
  if [ -n "$V" ]; then
    VIOLATIONS="${VIOLATIONS}\nArchitecture violation in $FILE_PATH (core/ must not import from services/, flask, or app):\n$V"
  fi
  RV=$(check_imports "$FILE_PATH" "from \.\.\(services\|app\)")
  if [ -n "$RV" ]; then
    VIOLATIONS="${VIOLATIONS}\nRelative import violation in $FILE_PATH:\n$RV"
  fi
fi

# Check services/ files — must not import from app
if echo "$FILE_PATH" | grep -q "services/"; then
  V=$(check_imports "$FILE_PATH" "from app import\|import app")
  if [ -n "$V" ]; then
    VIOLATIONS="${VIOLATIONS}\nArchitecture violation in $FILE_PATH (services/ must not import from app):\n$V"
  fi
fi

if [ -n "$VIOLATIONS" ]; then
  # Log violation persistently
  mkdir -p "$(dirname "$VIOLATION_LOG")"
  echo -e "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $VIOLATIONS" >> "$VIOLATION_LOG"

  # Output JSON to request user confirmation
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "Import direction violation detected:\n${VIOLATIONS}\n\nThe import direction rule is: app.py → services/ → core/ → data_pipeline/ (never reverse).\nProceed anyway?"
  }
}
EOF
fi

exit 0

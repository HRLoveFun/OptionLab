---
name: fix-review
description: "Review a bug fix before committing. Use after applying a fix to verify architecture compliance, error handling consistency, test coverage, and NaN propagation safety."
argument-hint: "Which files were changed?"
---

# Fix Review Checklist

Systematic review of code changes after a bug fix, before committing.

## When to Use
- After fixing a bug and before `git commit`
- After resolving a test failure
- After modifying error handling or data flow

## Procedure

### Step 1: Identify Changed Files

List all modified files and their layer:
```bash
git diff --name-only
```

Map each file to its layer:
| File path | Layer |
|-----------|-------|
| `data_pipeline/*` | Data I/O |
| `core/*` | Computation |
| `services/*` | Orchestration |
| `app.py` | Routes |
| `tests/*` | Tests |
| `utils/*` | Shared utilities |

### Step 2: Check Import Direction

For each changed file, verify imports follow the allowed direction:
- `data_pipeline/` → only `utils/` and stdlib
- `core/` → `data_pipeline/`, `utils/`, stdlib
- `services/` → `core/`, `data_pipeline/`, `utils/`
- `app.py` → `services/`, `utils/`

Search for violations:
```bash
grep -n "from services\|from core\|from app" data_pipeline/*.py
grep -n "from services\|from app\|from flask" core/*.py
```

### Step 3: Check Error Handling Consistency

Verify the fix uses the correct error pattern for its layer:
| Layer | Expected Pattern |
|-------|-----------------|
| `data_pipeline/` | Return `PipelineResult(ok=False, error="...")` |
| `core/` | Raise specific exceptions (`ValueError`, `KeyError`) or return `None` with doc |
| `services/` | Catch core exceptions, return dict with `'error'` key |
| `app.py` | Catch service errors, return HTTP status code + JSON error |

### Step 4: Verify Test Coverage

For each changed production file, check that a corresponding test exists:
```bash
# Map production file to test file
# data_pipeline/downloader.py → tests/test_yf_download.py or tests/test_processing.py
# core/market_analyzer.py → tests/test_market_review.py
# services/validation_service.py → tests/test_validation.py
```

If no test covers the fix:
1. Generate a minimal test that reproduces the original bug
2. Verify the test FAILS without the fix and PASSES with it
3. Follow project test patterns (factory functions, _isolate_db fixture)

### Step 5: Run Tests

```bash
pytest -x --tb=short tests/
```

If any test fails, investigate before committing.

### Step 6: Check NaN Propagation

If the fix touches data flow:
1. Trace the data path from the fix point downstream
2. Verify that NaN/None values are handled at each boundary
3. Key boundaries to check:
   - After `pd.to_numeric()` → are NaN rows filtered?
   - After DB read → is dtype `float64`?
   - Before chart generation → is DataFrame non-empty?

### Step 7: Output Summary

Produce a brief review summary:
```
## Fix Review
- Files changed: [list]
- Import compliance: OK / VIOLATION in [file]
- Error handling: OK / INCONSISTENT in [file]
- Test coverage: OK / MISSING for [file]
- Tests: PASS / FAIL
- NaN safety: OK / RISK in [path]
- Registry updated: YES (pattern) / NO (not applicable)
```

### Step 8: Update Failure Registry

If this fix resolves a known failure pattern:

1. Open `.github/data/failure-registry.yaml`
2. Find the matching pattern entry (e.g., `nan-propagation`, `empty-dataframe`)
3. Update the entry:
   - `resolved: true`
   - `resolution_note:` brief description of the fix
   - `effective_level:` the escalation level that was actually needed
4. If the failure tracker (`.github/data/failure_tracker.json`) has entries for this category, reset its count to 0

This ensures the system remembers what was fixed and at what level, so future recurrences start at the right escalation level.

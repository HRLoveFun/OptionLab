# Escalation Levels Decision Matrix

## Quick Decision Guide

```
Is the bug reproducible with a simple unit test?
├── YES → Level 1: Re-mock at different boundary
└── NO
    ├── Does it involve multiple pipeline stages?
    │   ├── YES → Level 2: Integration with real DB
    │   └── NO
    │       ├── Are the failure inputs unknown/many?
    │       │   ├── YES → Level 3: Property-based (hypothesis)
    │       │   └── NO → Level 4: Fault injection
    │       └── Does it involve partial failures across components?
    │           └── YES → Level 4: Fault injection
    └── Check: are current tests giving false green? → Re-examine mock boundaries
```

## Level Comparison

| Level | Tool | Best For | Cost | Coverage |
|-------|------|----------|------|----------|
| 1: Re-mock | pytest + patch | Wrong mock boundary hiding bugs | Low | Targeted |
| 2: Integration | pytest + real DB | Multi-stage pipeline failures | Medium | Cross-layer |
| 3: Property | hypothesis | Unknown edge cases, math bugs | Medium | Wide |
| 4: Fault injection | monkeypatch | Partial failures, resilience | High | Failure paths |

## OptionView-Specific Failure Patterns

### Pattern A: NaN Propagation Chain
- **Symptom**: Empty charts, 0 historical data points
- **Root cause**: NaN-only filler rows from failed download survive cleaning
- **Effective level**: Level 2 (integration — needs real DB to reproduce the chain)
- **Key assertion**: After pipeline, `processed_prices` has no NaN-only rows

### Pattern B: yfinance Silent Failure
- **Symptom**: Data appears stale, "No new data" in logs
- **Root cause**: Download returns empty DF, cooldown prevents retry
- **Effective level**: Level 1 (re-mock `_download_yf` to return empty DF)
- **Key assertion**: `PipelineResult.ok = True` with `rows = 0` (not error)

### Pattern C: dtype Mismatch from DB
- **Symptom**: `numpy` errors on math operations, "object" dtype
- **Root cause**: SQLite returns Python objects, not numpy types
- **Effective level**: Level 2 (needs data round-trip through DB)
- **Key assertion**: All numeric columns have `float64` dtype after fetch

### Pattern D: Concurrent Update Conflict
- **Symptom**: Intermittent wrong values, especially during multi-ticker updates
- **Root cause**: WAL mode race condition or stale cache read
- **Effective level**: Level 4 (inject delays between concurrent writers)
- **Key assertion**: Final DB state is consistent regardless of execution order

### Pattern E: Greeks Edge Cases
- **Symptom**: NaN in Greeks table, wrong delta/gamma for deep ITM/OTM
- **Root cause**: Black-Scholes inputs at boundary (T≈0, sigma≈0, S/K extreme ratio)
- **Effective level**: Level 3 (hypothesis finds boundary inputs)
- **Key assertion**: No unhandled exceptions; NaN only for genuinely invalid inputs

## Escalation History Template

Track repeated failures to trigger escalation:

```
Date: YYYY-MM-DD
Category: Data / Network / Concurrency / Logic / Integration
Symptom: [brief description]
Times seen: N
Current test level: [1-4]
Root cause found: [yes/no]
Resolution: [description]
```

When "Times seen" reaches 3 and "Root cause found" is still no → escalate to next level.

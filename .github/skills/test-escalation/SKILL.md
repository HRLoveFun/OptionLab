---
name: test-escalation
description: "Escalate testing strategy when existing tests fail to catch root cause. Use when same bug recurs 3+ times, tests pass but production breaks, or current test approach is insufficient. Covers unit, integration, property-based, and fault injection testing levels."
argument-hint: "Describe the recurring failure or test gap"
---

# Test Escalation Strategy

When existing tests don't catch the real problem, systematically escalate the testing approach instead of repeating the same test pattern.

## When to Use
- Same error category appears 3+ times across conversations
- Tests all pass but production still breaks (false green)
- Root cause is in a different layer than where the symptom appears
- Need to discover unknown edge cases (not just test known ones)

## Procedure

### Step 1: Classify the Failure

Determine the failure category:

| Category | Symptoms | Example |
|----------|----------|---------|
| **Data** | Empty DF, wrong dtype, NaN propagation | `features_df` shape (0, N), `object` dtype errors |
| **Network** | 429, timeout, empty response | yfinance download returns empty DataFrame |
| **Concurrency** | DB lock, stale read, race condition | Two tickers update simultaneously, one gets old data |
| **Logic** | Wrong calculation, incorrect filter | Greeks return NaN for valid inputs, wrong moneyness |
| **Integration** | Works in isolation, fails in pipeline | Cleaning produces correct output but processing ignores it |

### Step 2: Check Existing Test Coverage

Search test files for the failure category:
```
grep -r "relevant_function_or_error" tests/
```

Evaluate: Do existing tests cover the **actual failure path**? Common gaps:
- Tests mock too high (hiding the real bug)
- Tests only check happy path (no error injection)
- Tests check return type but not content (`assert result is not None` — weak)
- Tests don't reproduce the data conditions that cause the bug

### Step 3: Choose Escalation Level

Progress through levels until the root cause is found:

#### Level 1: Re-mock at Different Boundary
**When**: Current mocks hide the bug by returning fake data that avoids the failure path.

```python
# BEFORE: mocking yfinance hides the empty-DF problem
@patch("data_pipeline.downloader.yf.download", return_value=pd.DataFrame({"Close": [100]}))
def test_download(mock_dl):
    result = upsert_raw_prices("NVDA")
    assert result.ok  # Always passes — never tests empty case

# AFTER: mock at DB level to test what happens when download actually fails
@patch("data_pipeline.downloader._download_yf", return_value=pd.DataFrame())
def test_download_empty(mock_dl):
    result = upsert_raw_prices("NVDA")
    assert result.ok  # Rows=0 is valid
    assert result.rows == 0
    # Verify no NaN filler rows were created
    df = fetch_df("SELECT * FROM raw_prices WHERE ticker='NVDA'")
    assert df.empty
```

#### Level 2: Integration with Real DB + Seeded Data
**When**: Unit tests pass but the bug occurs during multi-stage pipeline execution.

```python
def test_full_pipeline_with_nan_data(tmp_path, monkeypatch):
    """Seed DB with NaN-only rows, verify pipeline handles them."""
    monkeypatch.setenv("MARKET_DB_PATH", str(tmp_path / "test.sqlite"))
    init_db()

    # Seed NaN-only filler rows (simulates failed download)
    upsert_many("raw_prices", ["ticker", "date", "open", "high", "low", "close"],
                [("NVDA", "2026-03-28", None, None, None, None)])

    # Run cleaning — should NOT propagate NaN rows
    result = clean_range("NVDA", dt.date(2026, 3, 28), dt.date(2026, 3, 28))

    # Verify: clean_prices should be empty (NaN rows filtered)
    df = fetch_df("SELECT * FROM clean_prices WHERE ticker='NVDA'")
    assert df.empty or df["close"].notna().all()
```

#### Level 3: Property-Based Testing (Hypothesis)
**When**: Edge cases are too numerous to enumerate manually. Need to discover unknown failure inputs.

```python
from hypothesis import given, strategies as st

@given(
    close=st.one_of(st.floats(min_value=0.01, max_value=10000), st.just(float("nan")), st.just(0.0)),
    volume=st.one_of(st.integers(min_value=0, max_value=10**9), st.just(0)),
    sigma=st.floats(min_value=0.001, max_value=5.0),
)
def test_greeks_never_crash(close, volume, sigma):
    """Greeks computation should never raise — returns NaN for invalid inputs."""
    from core.options_greeks import calc_greeks
    result = calc_greeks(S=close, K=100, T=0.25, r=0.05, sigma=sigma)
    # Should return dict, never raise
    assert isinstance(result, dict)
    for key in ("delta", "gamma", "theta", "vega"):
        assert key in result
```

#### Level 4: Fault Injection
**When**: Need to simulate partial failures in multi-component flows.

```python
def test_partial_download_failure(monkeypatch):
    """When 2 of 3 tickers fail, successful one should still be processed."""
    call_count = {"n": 0}
    original_download = _download_yf

    def flaky_download(ticker, start, end):
        call_count["n"] += 1
        if ticker in ("FAIL1", "FAIL2"):
            return pd.DataFrame()  # Simulate failure
        return original_download(ticker, start, end)

    monkeypatch.setattr("data_pipeline.downloader._download_yf", flaky_download)

    results = {}
    for t in ("FAIL1", "NVDA", "FAIL2"):
        results[t] = upsert_raw_prices(t)

    assert results["FAIL1"].rows == 0
    assert results["NVDA"].rows > 0
    assert results["FAIL2"].rows == 0
```

### Step 4: Generate the Test

Based on the chosen level:
1. Write the test following project patterns (see `tests/` instructions)
2. Use `_isolate_db` fixture for DB isolation
3. Use factory functions for test data
4. Name it descriptively: `test_{what}_{condition}_{expected}`

### Step 5: Record to Registry

After resolving, update the failure registry so the system learns:

1. **Update `.github/data/failure-registry.yaml`** for the matched pattern:
   - Set `resolved: true` if the fix is permanent
   - Update `effective_level` to the level that actually found the root cause
   - Add `resolution_note` describing what worked
   - Update `times_seen` and `last_seen`

2. **Reset the tracker**: Remove or zero out the count for this category in `.github/data/failure_tracker.json` so escalation suggestions stop.

3. **Update escalation-levels.md** if this represents a new OptionView-specific pattern not yet documented in [escalation levels reference](./references/escalation-levels.md).

4. If the pattern recurs later (resolved → re-appears), the effective_level in the registry ensures escalation starts at the right level instead of Level 1.

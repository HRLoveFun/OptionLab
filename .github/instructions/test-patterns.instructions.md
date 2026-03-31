---
description: "Use when writing or editing pytest test files for the OptionView project."
applyTo: "tests/**"
---

# Test Patterns

## DB Isolation
- `conftest.py` provides `_isolate_db` (autouse) that redirects `MARKET_DB_PATH` to a temp dir
- Every test gets a fresh empty database — never rely on pre-existing data
- To seed data, call `init_db()` then `upsert_many()` within the test

## Data Factories
- Use factory functions with `**overrides` for test data construction:
  ```python
  def _make_contract(**overrides):
      base = {"strike": 100, "bid": 1.0, "ask": 1.5, ...}
      base.update(overrides)
      return base
  ```
- Never hardcode large dicts inline — extract to a factory at module top

## Mocking Strategy
- Mock yfinance at the **module boundary**: `@patch("data_pipeline.downloader.yf.download")` — not deep internal calls
- Mock DB queries when testing core/ or services/ — not the DB engine itself
- Use `monkeypatch.setenv()` for environment variables, not `os.environ` directly

## Assertions
- Assert **specific** exception types: `with pytest.raises(ValueError, match="..."):`
- Test both empty-data AND NaN-data paths — they fail differently
- For DataFrame results, assert shape, dtypes, and key column values — not just `is not None`
- Use `pytest.approx()` for float comparisons in financial calculations

## Parametrize
- Use `@pytest.mark.parametrize` for boundary values: 0, negative, NaN, empty string, None
- Group related edge cases in one parametrized test rather than separate test functions

## Anti-patterns to Avoid
- Don't assert only `result is not None` — check the actual content
- Don't skip error path tests — every `try/except` in production needs a test that triggers it
- Don't use `time.sleep()` in tests — mock time-dependent behavior instead

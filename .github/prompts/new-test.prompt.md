---
description: "Generate a test following OptionView project patterns for a specific module or function."
agent: "agent"
tools: [read, search, edit]
argument-hint: "Module or function to test (e.g., 'data_pipeline/cleaning.py clean_range')"
---

Generate a pytest test for the specified module/function following OptionView test conventions:

1. Read the target function to understand its behavior, inputs, and error paths
2. Check existing tests in `tests/` for related coverage — avoid duplication
3. Generate the test following project patterns:
   - Use `_isolate_db` fixture (autouse from conftest.py) for DB isolation
   - Use factory functions (`_make_contract(**overrides)`, `_base_form(**overrides)`) for test data
   - Mock yfinance at module boundary: `@patch("data_pipeline.downloader.yf.download")`
   - Use `pytest.approx()` for float comparisons
   - Use `@pytest.mark.parametrize` for boundary values
4. Include both happy path AND error path tests:
   - Empty DataFrame input
   - NaN-only data
   - Invalid types / missing keys
5. Name tests descriptively: `test_{what}_{condition}_{expected}`

# OptionLab E2E Tests (Playwright)

Browser-based smoke tests that exercise the real Flask app rendered in
Chromium via Playwright. These complement the existing pytest unit and
integration tests by catching the failure modes that only surface in
a real browser:

- **JS console errors** (typos in selectors, undefined globals, etc.)
- **Tab/panel rendering** (CSS / DOM wiring breaks)
- **Lazy-load wiring** (frontend → `/api/*` calls fire correctly)
- **Race conditions** (AbortController on rapid tab switches)
- **Graceful degradation** when `/api/*` returns 5xx

All `/api/*` requests are intercepted at the **browser** level via
`page.route`, so no real yfinance call is ever made and the SQLite DB
is only used to render `index.html`.

---

## Install

> Not added to `requirements.txt` to keep the default dev install lean.
> Install on demand:

```bash
source .venv/bin/activate
pip install pytest-playwright
playwright install chromium      # downloads ~120 MB browser bundle
```

The `pytest-playwright` package provides the `page` fixture used by these
tests. `playwright install chromium` is required only on first install
(or after a Playwright version bump).

---

## Run

```bash
# All e2e tests (headless Chromium)
pytest tests/e2e/

# Single file
pytest tests/e2e/test_smoke.py

# With browser visible (debugging)
pytest tests/e2e/ --headed

# Slow-mo + headed (great for diagnosing flakes)
pytest tests/e2e/ --headed --slowmo 500

# Trace on failure (open with: playwright show-trace trace.zip)
pytest tests/e2e/ --tracing retain-on-failure
```

The default project pytest config (`pyproject.toml`) uses `-x --tb=short -q`,
which applies here too — the first failing test stops the run.

To **exclude** e2e from the default pytest invocation:

```bash
pytest --ignore=tests/e2e
```

To **scope by directory in pyproject** (recommended for CI), add:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
# Default run skips e2e; enable with: pytest tests/e2e/
addopts = "-x --tb=short -q --ignore=tests/e2e"
```

(Not applied automatically — left as a deliberate decision so that
`pytest` and `pytest tests/` behave the same as today.)

---

## Test inventory

| File                | Flow                                                           |
| ------------------- | -------------------------------------------------------------- |
| `test_smoke.py`     | GET / loads with no JS errors; all 11 sidebar tabs activate.   |
| `test_lazy_tabs.py` | Option-chain tab fires `/api/option_chain`; UI handles 500.    |
| `test_tab_race.py`  | Rapid tab switching: final panel wins, no uncaught exceptions. |

---

## Architecture

`tests/e2e/conftest.py` provides:

- **`_e2e_db`** *(session, autouse)* — points `MARKET_DB_PATH` at a
  session-scoped temp SQLite file before `app` is imported. Overrides
  the parent `tests/conftest.py::_isolate_db` (which is per-function and
  would invalidate the running Flask server).
- **`live_server`** *(session)* — launches the real Flask app on a
  random local port via `werkzeug.serving.make_server` in a daemon thread.
- **`js_errors`** *(function)* — collects `console.error` messages and
  uncaught `pageerror` exceptions. Tests assert `js_errors == []`.
- **`mock_apis`** *(function)* — installs a `page.route("**/api/**", ...)`
  handler returning canned JSON for every `/api/*` endpoint. Returns a
  mutable dict so individual tests can override responses (e.g. inject
  500 errors).

**Why mock at the browser layer instead of patching yfinance?**
Because we want to test the **frontend** end-to-end, including its
fetch wiring, error handling, and DOM updates — not the backend's
yfinance integration (already covered by the unit suite). Browser-level
mocks are deterministic, fast, and don't require touching production code.

---

## Adding a new test

1. Drop a `test_*.py` file in this directory.
2. Use the `page`, `live_server`, `mock_apis`, and `js_errors` fixtures.
3. Always end with `assert js_errors == []` to catch silent JS regressions.
4. To customize a mocked endpoint, mutate `mock_apis` **before** navigation:

   ```python
   mock_apis["/api/option_chain"] = (500, {"error": "boom"})
   page.goto(live_server)
   ```

5. For new endpoints not yet listed in `conftest.py::mock_apis`, add a
   branch to the `_handler` function.

---

## Known limitations

- The form-submit happy path (`POST /`) is **not** covered here — it
  would require seeding the DB with valid synthetic OHLCV and mocking
  yfinance at the Python layer. The existing `tests/test_frontend_api.py`
  covers backend rendering of POST `/` already.
- Mobile viewports / responsive breakpoints are not yet asserted; the
  `page.set_viewport_size({...})` API can be wired in if/when needed.
- Visual regression (screenshot diffing) is intentionally out of scope.

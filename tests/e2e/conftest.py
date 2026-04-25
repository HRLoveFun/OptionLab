"""Pytest fixtures for Playwright e2e tests.

These tests exercise the real Flask app rendered in a real browser
(Chromium via Playwright). All network-bound side effects (yfinance,
the `/api/*` endpoints) are intercepted at the browser level via
`page.route`, so the backend never actually calls Yahoo and the DB
is only used for index.html rendering.

Scopes:
  * `live_server` is session-scoped — one Flask server per test session.
  * The DB is isolated to a session-scoped temp dir so the parent
    `tests/conftest.py::_isolate_db` (function-scoped) is overridden
    here to avoid breaking the running server mid-session.
"""

from __future__ import annotations

import os
import socket
import threading
from collections.abc import Iterator
from typing import Any

import pytest

# Skip the entire e2e directory if Playwright isn't installed so that the
# default `pytest` invocation (which collects everything under `tests/`)
# does not error out for users who haven't installed the optional e2e deps.
# See tests/e2e/README.md for install instructions.
pytest.importorskip("playwright.sync_api", reason="Install pytest-playwright to run e2e tests")
pytest.importorskip("pytest_playwright", reason="Install pytest-playwright to run e2e tests")


# ---------------------------------------------------------------------------
# DB isolation — override the parent autouse fixture with a session-scoped
# no-op variant. The actual isolation happens once in `_e2e_db` below.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _isolate_db():  # noqa: PT004
    """Override parent conftest's per-function DB isolation.

    For e2e tests we set up a single shared DB at session scope (see
    `_e2e_db`). Re-isolating per test would invalidate the running
    Flask server's DB connections.
    """
    yield


@pytest.fixture(scope="session", autouse=True)
def _e2e_db(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """Point the app at a session-scoped temp SQLite DB.

    Must run before `app` is imported by `live_server`. If the `app`
    module was already imported by an earlier test (e.g. test_frontend_api),
    `DataService.initialize()` won't re-run, so we re-init the DB explicitly
    against the new path here.
    """
    db_file = str(tmp_path_factory.mktemp("e2e-db") / "market.sqlite")
    os.environ["MARKET_DB_PATH"] = db_file
    # Patch the module attr in case data_pipeline.db was already imported
    # by a previous test module in the same pytest session (DB_PATH is
    # captured at import time).
    try:
        import data_pipeline.db as db_mod

        db_mod.DB_PATH = db_file
        # Ensure schema exists at the new path even if app was pre-imported.
        if hasattr(db_mod, "init_db"):
            db_mod.init_db()
    except ImportError:
        pass
    yield db_file


# ---------------------------------------------------------------------------
# Flask live server — runs the real app on a random local port.
# ---------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server(_e2e_db: str) -> Iterator[str]:
    """Start the Flask app in a background thread, yield its base URL."""
    # Import app *after* MARKET_DB_PATH is set so init_db() targets the temp DB.
    from werkzeug.serving import make_server

    from app import app as flask_app

    flask_app.config["TESTING"] = True

    port = _free_port()
    server = make_server("127.0.0.1", port, flask_app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, name="e2e-flask", daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Playwright page hardening — capture JS console errors and uncaught
# exceptions so any tests that read `js_errors` can assert on them.
# ---------------------------------------------------------------------------
@pytest.fixture
def js_errors(page) -> list[str]:
    """Collect browser console errors and uncaught page exceptions.

    Tests that should fail on JS errors can simply: `assert js_errors == []`.
    """
    errors: list[str] = []

    def _on_console(msg: Any) -> None:
        if msg.type == "error":
            errors.append(f"[console.error] {msg.text}")

    def _on_pageerror(exc: Any) -> None:
        errors.append(f"[pageerror] {exc}")

    page.on("console", _on_console)
    page.on("pageerror", _on_pageerror)
    return errors


# ---------------------------------------------------------------------------
# Canned JSON responses for `/api/*` interception.
# ---------------------------------------------------------------------------
FAKE_OPTION_CHAIN: dict[str, Any] = {
    "ticker": "^SPX",
    "spot": 5000.0,
    "expirations": ["2026-05-15", "2026-06-19"],
    "chains": {
        "2026-05-15": {
            "calls": [
                {"strike": 5000, "bid": 50.0, "ask": 52.0, "last": 51.0, "iv": 0.18, "volume": 100, "open_interest": 500},
                {"strike": 5050, "bid": 30.0, "ask": 32.0, "last": 31.0, "iv": 0.19, "volume": 80,  "open_interest": 400},
            ],
            "puts": [
                {"strike": 5000, "bid": 48.0, "ask": 50.0, "last": 49.0, "iv": 0.20, "volume": 90,  "open_interest": 450},
                {"strike": 4950, "bid": 28.0, "ask": 30.0, "last": 29.0, "iv": 0.21, "volume": 70,  "open_interest": 350},
            ],
        }
    },
    "as_of": "2026-04-25T12:00:00Z",
}


FAKE_MARKET_REVIEW_TS: dict[str, Any] = {
    "instrument": "^SPX",
    "dates": ["2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01"],
    "assets": [
        {
            "name": "^SPX",
            "prices": [4800, 4850, 4900, 5000],
            "cum_returns": [0.0, 0.0104, 0.0208, 0.0417],
            "rolling_vol": [0.15, 0.16, 0.17, 0.18],
        }
    ],
    "periods": ["1M", "1Q", "YTD", "ETD"],
}


FAKE_REGIME_HISTORY: dict[str, Any] = {
    "ok": True,
    "data": {
        "dates": ["2026-04-01", "2026-04-15", "2026-04-25"],
        "vol_regime": ["normal", "normal", "elevated"],
        "trend_regime": ["up", "up", "up"],
        "vix": [15.0, 16.5, 22.0],
    },
    "source": "synthetic",
}


@pytest.fixture
def mock_apis(page):
    """Intercept all `/api/*` calls and return canned JSON.

    Returns a dict that tests can mutate (before navigation) to override
    individual endpoints, e.g. `mock_apis['/api/option_chain'] = (500, {...})`.
    """
    overrides: dict[str, tuple[int, Any]] = {}

    def _handler(route, request):
        url = request.url
        # Match by path suffix to be resilient to host/port.
        for path, (status, body) in overrides.items():
            if path in url:
                route.fulfill(status=status, content_type="application/json", json=body)
                return

        if "/api/option_chain" in url:
            route.fulfill(status=200, content_type="application/json", json=FAKE_OPTION_CHAIN)
        elif "/api/market_review_ts" in url:
            route.fulfill(status=200, content_type="application/json", json=FAKE_MARKET_REVIEW_TS)
        elif "/api/regime/history" in url or "/api/regime/current" in url:
            route.fulfill(status=200, content_type="application/json", json=FAKE_REGIME_HISTORY)
        elif "/api/odds_with_vol" in url:
            route.fulfill(status=200, content_type="application/json", json={"ok": True, "rows": []})
        elif "/api/game" in url:
            route.fulfill(status=200, content_type="application/json", json={"ok": True, "candidates": []})
        elif "/api/portfolio_analysis" in url:
            route.fulfill(status=200, content_type="application/json", json={"ok": True})
        elif "/api/preload_option_chain" in url:
            route.fulfill(status=200, content_type="application/json", json={"ok": True})
        elif "/api/validate_ticker" in url or "/api/validate_tickers" in url:
            route.fulfill(status=200, content_type="application/json", json={"ok": True, "valid": True})
        else:
            route.fallback()

    page.route("**/api/**", _handler)
    return overrides

"""Pytest fixtures for Playwright e2e tests.

Two interception strategies are supported:

  1. **Browser-level mocks** (default for legacy tests) — `mock_apis` uses
     `page.route` to fulfill `/api/*` calls with canned JSON. The Flask
     backend is bypassed entirely. Fast, deterministic, no yfinance risk.

  2. **Real backend + yfinance stub** (`yf_stub` fixture, session-scoped) —
     The Flask process runs every route normally, but `yfinance.Ticker`,
     `yf.download`, and `fast_info` are monkey-patched in the backend
     process to return synthetic data. Combined with the existing
     `TEST_*` ticker fixture mechanism in `data_pipeline.downloader`, this
     lets e2e tests exercise real form submission, real DataService
     pipeline, real chart rendering — without network.

Tests pick whichever fixture they need: `mock_apis` for tab-routing /
JS-only flows, `yf_stub` (+ no `mock_apis`) for end-to-end form submit.

Scopes:
  * `live_server` is session-scoped — one Flask server per test session.
  * `yf_stub` is session-scoped — backend patches outlive any single test.
  * The DB is isolated to a session-scoped temp dir.
"""

from __future__ import annotations

import datetime as dt
import os
import socket
import threading
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

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
# Backend yfinance stub — installs *once* for the whole session.
#
# Tests that want to exercise real Flask routes (form POST → render endpoints
# → /api/option_chain → /api/validate_tickers) opt in by using the `yf_stub`
# fixture *instead of* `mock_apis`. The patch covers:
#
#   * `yfinance.download`              — used by data_pipeline.downloader and
#                                        core.market_review
#   * `yfinance.Ticker(...).fast_info` — used for spot price lookups
#   * `yfinance.Ticker(...).options`   — option expirations list
#   * `yfinance.Ticker(...).option_chain(exp)` — calls/puts DataFrames
#
# Combined with the existing `TEST_*` ticker bypass in
# `data_pipeline.downloader._download_yf`, real `TEST_AAPL` form submissions
# never hit the network.
# ---------------------------------------------------------------------------
def _synthetic_ohlcv(ticker: str, start: dt.date, end: dt.date):
    """Build a deterministic OHLCV DataFrame mirroring yfinance's shape."""
    import pandas as pd

    idx = pd.bdate_range(start, end)
    if len(idx) == 0:
        # Provide at least one row so downstream slices don't crash.
        idx = pd.bdate_range(end - dt.timedelta(days=7), end)
    base = 100.0 + (sum(ord(c) for c in ticker) % 50)
    closes = [base + i * 0.1 for i in range(len(idx))]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 0.5 for c in closes],
            "Low": [c - 0.5 for c in closes],
            "Close": closes,
            "Adj Close": closes,
            "Volume": [1_000_000] * len(idx),
        },
        index=idx,
    )
    return df


def _make_fake_ticker(symbol: str):
    """Construct a Mock that mimics `yfinance.Ticker(symbol)` enough for tests."""
    import pandas as pd

    today = dt.date.today()
    near = today + dt.timedelta(days=21)
    far = today + dt.timedelta(days=49)
    expirations = [near.isoformat(), far.isoformat()]

    spot = 100.0 + (sum(ord(c) for c in symbol) % 50)

    def _make_chain(expiry: str):
        strikes = [round(spot * m, 2) for m in (0.9, 0.95, 1.0, 1.05, 1.1)]
        rows = []
        for s in strikes:
            rows.append(
                {
                    "strike": s,
                    "lastPrice": max(spot - s, 0.5) + 1.0,
                    "bid": max(spot - s, 0.4) + 0.9,
                    "ask": max(spot - s, 0.4) + 1.1,
                    "volume": 100,
                    "openInterest": 500,
                    "impliedVolatility": 0.25,
                    "inTheMoney": s < spot,
                }
            )
        df = pd.DataFrame(rows)
        result = MagicMock()
        result.calls = df.copy()
        result.puts = df.copy()
        return result

    fast_info = MagicMock()
    fast_info.last_price = spot
    fast_info.regularMarketPrice = spot
    fast_info.get = lambda key, default=None: {
        "lastPrice": spot,
        "regularMarketPrice": spot,
    }.get(key, default)

    tk = MagicMock()
    tk.options = expirations
    tk.fast_info = fast_info
    tk.option_chain = _make_chain
    return tk


@pytest.fixture(scope="session")
def yf_stub() -> Iterator[None]:
    """Patch yfinance in the *backend process* for the whole test session.

    Activated by including `yf_stub` in a test signature. Existing tests
    that use `mock_apis` continue to work unchanged because browser-level
    interception fulfills before any backend code runs.
    """
    import yfinance as yf

    original_download = yf.download
    original_ticker = yf.Ticker

    def fake_download(tickers, start=None, end=None, **kwargs):  # noqa: ARG001
        if isinstance(tickers, str):
            return _synthetic_ohlcv(tickers, start or dt.date.today() - dt.timedelta(days=30),
                                    end or dt.date.today())
        # multi-ticker: return concatenated MultiIndex frame
        import pandas as pd
        frames = {}
        for t in tickers:
            frames[t] = _synthetic_ohlcv(t, start or dt.date.today() - dt.timedelta(days=30),
                                         end or dt.date.today())
        return pd.concat(frames, axis=1)

    fake_ticker = MagicMock(side_effect=lambda sym: _make_fake_ticker(sym))

    p1 = patch.object(yf, "download", fake_download)
    p2 = patch.object(yf, "Ticker", fake_ticker)
    p1.start()
    p2.start()
    try:
        yield
    finally:
        p1.stop()
        p2.stop()
        # Restore is idempotent; assigning back guards against import order.
        yf.download = original_download
        yf.Ticker = original_ticker


@pytest.fixture(scope="session")
def seed_test_data(_e2e_db: str, yf_stub: None) -> Iterator[None]:
    """Pre-populate the DB with `TEST_AAPL` data so render endpoints have
    something to slice without hitting any download path on first request.

    Uses the production downloader's `TEST_*` fixture branch — no network.
    """
    try:
        from data_pipeline.data_service import DataService
        # `manual_update` will route to the synthetic fixture for TEST_*
        DataService.manual_update("TEST_AAPL", days=120)
    except Exception:
        # Don't fail collection on seeding errors — individual tests can
        # decide whether the missing data is fatal.
        pass
    yield


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
    "chain": {
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
        elif "/api/validate_tickers" in url:
            # Echo back the posted tickers as all valid with synthetic prices.
            try:
                payload = request.post_data_json or {}
            except Exception:
                payload = {}
            tickers = payload.get("tickers", []) if isinstance(payload, dict) else []
            results = {t: {"valid": True, "price": 100.0, "message": "valid_ticker"} for t in tickers}
            route.fulfill(
                status=200,
                content_type="application/json",
                json={"status": "ok", "results": results},
            )
        elif "/api/validate_ticker" in url:
            route.fulfill(status=200, content_type="application/json", json={"valid": True, "message": "valid_ticker"})
        else:
            route.fallback()

    page.route("**/api/**", _handler)
    return overrides

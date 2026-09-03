"""Tests for the inbound rate limiter (``utils/rate_limit``).

The global throttle is exercised through a real Flask app and a real test
client — no mocked responses — because the point of ``install()`` is the
response shape it produces when the budget is exhausted.
"""

from __future__ import annotations

import pytest
from flask import Flask

import utils.rate_limit as rate_limit_mod
from utils.rate_limit import install, parse_rate_limit_spec


@pytest.fixture(autouse=True)
def _clear_buckets():
    """Isolate the module-level token buckets between tests."""
    with rate_limit_mod._rate_lock:
        rate_limit_mod._rate_buckets.clear()
    yield
    with rate_limit_mod._rate_lock:
        rate_limit_mod._rate_buckets.clear()


def _make_app() -> Flask:
    app = Flask(__name__)

    @app.get("/api/ping")
    def _ping():
        return {"ok": True}

    return app


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ("120 per minute", (120, 60)),
        ("120/minute", (120, 60)),
        ("120 per 1 minute", (120, 60)),
        ("10 per second", (10, 1)),
        ("5 per hour", (5, 3600)),
        ("200 per day", (200, 86400)),
        ("  3  per  minute  ", (3, 60)),
    ],
)
def test_parse_rate_limit_spec_accepts_supported_formats(spec, expected):
    assert parse_rate_limit_spec(spec) == expected


@pytest.mark.parametrize(
    "spec",
    ["", "banana", "per minute", "0 per minute", "10 per fortnight", "10 per 0 minute", "10/"],
)
def test_parse_rate_limit_spec_rejects_unparseable_input(spec):
    with pytest.raises(ValueError):
        parse_rate_limit_spec(spec)


def test_install_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_DISABLED", "1")

    assert install(_make_app()) is False


def test_install_falls_back_to_default_on_invalid_spec(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "banana")

    app = _make_app()
    assert install(app) is True

    max_calls, _ = parse_rate_limit_spec(rate_limit_mod.DEFAULT_RATE_LIMIT_SPEC)
    client = app.test_client()
    for _ in range(max_calls):
        assert client.get("/api/ping").status_code == 200

    assert client.get("/api/ping").status_code == 429


def test_exhausted_budget_returns_unified_error_envelope(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "3 per minute")

    app = _make_app()
    assert install(app) is True

    client = app.test_client()
    for _ in range(3):
        assert client.get("/api/ping").status_code == 200

    blocked = client.get("/api/ping")

    assert blocked.status_code == 429
    assert blocked.headers["Content-Type"].startswith("application/json")
    payload = blocked.get_json()
    assert payload["status"] == "error"
    assert payload["code"] == "rate_limited"
    assert payload["details"]["retry_after"] >= 1
    assert str(payload["details"]["retry_after"]) in payload["message"]
    assert blocked.headers["Retry-After"] == str(payload["details"]["retry_after"])


def test_static_assets_are_exempt_from_the_budget(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_DISABLED", raising=False)
    monkeypatch.setenv("RATE_LIMIT_DEFAULT", "1 per minute")

    app = _make_app()
    install(app)
    client = app.test_client()

    assert client.get("/api/ping").status_code == 200
    # Budget is exhausted, but static must still be routed (404 because the
    # file doesn't exist — the assertion is that it is *not* a 429).
    assert client.get("/static/does-not-exist.js").status_code == 404

"""Tests for unified error envelope and /api/v1 alias."""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_DISABLED", "1")

import pytest
from app import app as _flask_app

from utils.api_errors import ApiError


@pytest.fixture
def client():
    _flask_app.config["TESTING"] = True
    return _flask_app.test_client()


def test_api_error_payload_shape():
    err = ApiError("nope", code="x", status=418, details={"k": "v"})
    payload = err.to_payload()
    assert payload["status"] == "error"
    assert payload["code"] == "x"
    assert payload["message"] == "nope"
    assert payload["details"] == {"k": "v"}


def test_api_404_returns_json(client):
    resp = client.get("/api/does_not_exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["status"] == "error"
    assert body["code"] == "not_found"


def test_html_404_does_not_jsonify(client):
    resp = client.get("/no_such_html_route")
    # Default Flask 404 renders HTML, not JSON.
    assert resp.status_code == 404
    assert "application/json" not in (resp.content_type or "")


def test_v1_alias_routes_to_legacy(client):
    legacy = client.get("/api/ping")
    aliased = client.get("/api/v1/ping")
    assert legacy.status_code == aliased.status_code == 200
    assert aliased.get_json() == legacy.get_json()


def test_v1_meta_lists_routes(client):
    resp = client.get("/api/v1/_meta")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["version"] == "v1"
    assert any(r.startswith("/api/") for r in body["routes"])

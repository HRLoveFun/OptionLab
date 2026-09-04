"""Tests for GET /api/expiry_calendar (Premium Matrix column source)."""

import os

os.environ.setdefault("RATE_LIMIT_DISABLED", "1")

import pytest
from app import app as _flask_app


@pytest.fixture
def client():
    _flask_app.config["TESTING"] = True
    return _flask_app.test_client()


def test_expiry_calendar_default(client):
    resp = client.get("/api/expiry_calendar")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert len(body["expirations"]) >= 12
    exp = body["expirations"][0]
    assert {"date", "dte", "label", "kind", "cycle"}.issubset(exp.keys())


def test_expiry_calendar_with_ref_and_counts(client):
    resp = client.get("/api/expiry_calendar?ref=2026-09-04&standard=3&daily=2")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["reference_date"] == "2026-09-04"
    # 3 standard + 2 daily, de-duplicated on overlap.
    assert len(body["expirations"]) >= 5
    standards = [e for e in body["expirations"] if e["kind"] == "standard"]
    assert standards[0]["date"] == "2026-09-18"
    assert standards[0]["cycle"] == "quarterly"


def test_expiry_calendar_bad_ref(client):
    resp = client.get("/api/expiry_calendar?ref=not-a-date")
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "error"
    assert resp.get_json()["code"] == "invalid_ref"

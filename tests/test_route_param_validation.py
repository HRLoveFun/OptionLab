"""Regression tests for the unified error contract (batch 3 remediation).

The contract: malformed client input is a 400 ``invalid_parameter`` /
``invalid_*`` ApiError — never a 500 whose message echoes the raw exception.
"""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_DISABLED", "1")

import pytest
from app import app as _flask_app


@pytest.fixture
def client():
    _flask_app.config["TESTING"] = True
    return _flask_app.test_client()


class _FakeResp:
    """Stand-in for the network layer: parsing must fail before this is hit."""

    def __init__(self, *args, **kwargs):  # noqa: ARG002
        raise AssertionError("network must not be reached for invalid params")


class TestOptionChainParamParsing:
    def test_bad_max_dte_is_400_not_500(self, client, monkeypatch):
        monkeypatch.setattr("services.options.chain.OptionsChainService.fetch_records_filtered", _FakeResp)
        resp = client.get("/api/option_chain?ticker=NVDA&max_dte=abc")
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["status"] == "error"
        assert body["code"] == "invalid_parameter"
        # The envelope must not echo the raw ValueError text.
        assert "invalid literal" not in body["message"]

    @pytest.mark.parametrize("param", ["moneyness_low", "moneyness_high"])
    def test_bad_moneyness_is_400(self, client, param, monkeypatch):
        monkeypatch.setattr("services.options.chain.OptionsChainService.fetch_records_filtered", _FakeResp)
        resp = client.get(f"/api/option_chain?ticker=NVDA&{param}=xyz")
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_parameter"

    def test_bad_max_contracts_is_400(self, client, monkeypatch):
        monkeypatch.setattr("services.options.chain.OptionsChainService.fetch_records_filtered", _FakeResp)
        resp = client.get("/api/option_chain?ticker=NVDA&max_contracts=1e999")
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_parameter"


class TestExpiryProbabilityParamValidation:
    def test_target_pct_out_of_range_is_400(self, client):
        resp = client.post("/api/expiry_probability", json={"ticker": "NVDA", "target_pct": -100})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_parameter"

    def test_target_pct_not_a_number_is_400(self, client):
        resp = client.post("/api/expiry_probability", json={"ticker": "NVDA", "target_pct": "lots"})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_parameter"


class TestSimulateExpiryInfinity:
    def test_qty_infinity_is_400_not_500(self, client):
        """int(float('1e999')) raises OverflowError, which used to escape the
        (TypeError, ValueError) net and surface as 500 internal_error."""
        resp = client.post("/api/simulate_expiry", json={"spot": 100, "qty": "1e999"})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_qty"

    def test_n_points_infinity_is_400_not_500(self, client):
        resp = client.post("/api/simulate_expiry", json={"spot": 100, "n_points": "1e999"})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_n_points"


class TestGlobalEnvelope:
    def test_unexpected_500_message_is_fixed(self, client, monkeypatch):
        """The global handler logs the exception but returns a fixed message —
        no str(err) leakage of paths / SQL / upstream URLs."""

        def _boom(*args, **kwargs):  # noqa: ARG001
            raise RuntimeError("/secret/path leaked /etc/passwd")

        monkeypatch.setattr("services.options.chain.OptionsChainService.fetch_records_filtered", _boom)
        resp = client.get("/api/option_chain?ticker=NVDA")
        assert resp.status_code == 500
        body = resp.get_json()
        assert body["code"] in ("option_chain_failed", "internal_error")
        assert "/secret/path" not in body["message"]


class TestReposColumnWhitelist:
    def test_unknown_column_raises_before_sql(self):
        from data_pipeline.repos import select_tracked_strategies

        with pytest.raises(ValueError, match="unknown tracked_strategies columns"):
            select_tracked_strategies(["id", "notes; DROP TABLE tracked_strategies--"], None)

    def test_known_columns_accepted(self):
        from data_pipeline.db import init_db
        from data_pipeline.repos import select_tracked_strategies

        init_db()
        rows = select_tracked_strategies(["id", "ticker", "status"], None)
        assert isinstance(rows, list)


class TestPortfolioCloseValueParsing:
    def test_non_numeric_closed_value_is_400(self, client):
        resp = client.post("/api/portfolio/positions/1/close", json={"closed_value": "abc"})
        assert resp.status_code == 400
        assert resp.get_json()["code"] == "invalid_closed_value"

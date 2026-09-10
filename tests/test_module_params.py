"""Module-scoped parameters travel as query args on each `/render` call (B7).

Domain:    Tests — Module Parameter Contract
Context:
  - Decision gate §8 Q1 chose the **manifest** shape: `POST /` carries the module
    list, and each module's own toolbar appends its parameters to its `/render`
    call (`?from=…&to=…&frequency=…`). This file pins the backend half of that
    contract; the toolbars and the `state/*ParamsState.js` stores land with the
    rest of B7.
Contracts:
  - ``FormService.extract_module_params`` reads **only** the per-module allow-list,
    so a hand-crafted query string cannot inject arbitrary ``form_data`` keys.
  - ``/render/<kind>`` lets the query args override the values recorded on the job
    at POST time, falling back to the job when they are absent (direct URL).
Dependencies UPWARD:
  - (none — stdlib + pytest + the packages under test)
"""

from __future__ import annotations

import datetime as dt

import pytest

from services.market.form import FormService


class TestExtractModuleParams:
    def test_horizon_is_parsed_into_form_data_dates(self):
        out = FormService.extract_module_params("statistical", {"from": "2024-03", "to": "2024-09"})
        assert out["start_time"] == "2024-03"
        assert out["end_time"] == "2024-09"
        assert out["parsed_start_time"] == dt.date(2024, 3, 1)
        assert out["parsed_end_time"] == dt.date(2024, 9, 1)

    def test_market_review_accepts_only_the_horizon(self):
        """market_review declares no frequency, so a stray one is ignored."""
        out = FormService.extract_module_params("market_review", {"from": "2024-03", "frequency": "W"})
        assert set(out) == {"start_time", "parsed_start_time"}

    def test_options_chain_declares_no_parameters(self):
        assert FormService.extract_module_params("options_chain", {"from": "2024-03"}) == {}

    def test_unknown_module_is_inert(self):
        assert FormService.extract_module_params("nope", {"from": "2024-03"}) == {}

    def test_undeclared_keys_are_never_read(self):
        """A query string must not be able to smuggle keys into form_data."""
        out = FormService.extract_module_params(
            "statistical",
            {"from": "2024-03", "option_position": "[]", "ticker": "EVIL", "positions": "x"},
        )
        assert "option_position" not in out
        assert "option_data" not in out
        assert "ticker" not in out
        assert "positions" not in out

    def test_blank_and_malformed_values_are_skipped_not_defaulted(self):
        """Skipping lets the job's POST-time value remain the fallback."""
        assert FormService.extract_module_params("statistical", {"from": "", "frequency": ""}) == {}
        assert FormService.extract_module_params("statistical", {"frequency": "YEARLY"}) == {}
        assert FormService.extract_module_params("assessment", {"risk_threshold": "abc"}) == {}

    def test_assessment_group_parses_its_own_knobs(self):
        out = FormService.extract_module_params(
            "assessment",
            {
                "frequency": "W",
                "side_bias": "Neutral",
                "risk_threshold": "85",
                "rolling_window": "90",
                "account_size": "250000",
                "max_risk_pct": "1.5",
            },
        )
        assert out["frequency"] == "W"
        assert out["side_bias"] == "Neutral"
        assert out["target_bias"] == 0
        assert out["risk_threshold"] == 85
        assert out["rolling_window"] == 90
        assert out["account_size"] == 250000.0
        assert out["max_risk_pct"] == 1.5

    def test_natural_side_bias_keeps_a_null_target_bias(self):
        out = FormService.extract_module_params("assessment", {"side_bias": "Natural"})
        assert out["side_bias"] == "Natural"
        assert out["target_bias"] is None


class TestRenderSliceParameterPrecedence:
    """The query args win over the job; the job is the direct-URL fallback."""

    @staticmethod
    def _render(kind: str, query: str, monkeypatch) -> dict:
        from app import app

        from data_pipeline.orchestrate import job_cache
        from services.market.analysis import AnalysisService
        from services.market.dispatch import render_streaming_slice

        captured: dict = {}

        def _fake_slice(form_data):
            captured.clear()
            captured.update(form_data)
            return {}

        monkeypatch.setattr(AnalysisService, f"generate_{kind}_slice", staticmethod(_fake_slice), raising=False)

        job_cache._reset()
        job_id = job_cache.create_job(
            {
                "ticker": "AAPL",
                "frequency": "ME",
                "start_time": "2020-01",
                "parsed_start_time": dt.date(2020, 1, 1),
                "parsed_end_time": None,
            },
            ["AAPL"],
        )
        with app.test_request_context(f"/render/{kind}?job={job_id}&ticker=AAPL{query}"):
            render_streaming_slice(kind)
        return captured

    @pytest.mark.parametrize(
        ("kind", "slice_name"),
        [("statistical", "generate_statistical_slice"), ("market_review", "generate_market_review_slice")],
    )
    def test_query_params_override_the_job(self, kind, slice_name, monkeypatch):
        captured = self._render(kind, "&from=2024-03&to=2024-09&frequency=W", monkeypatch)
        assert captured["parsed_start_time"] == dt.date(2024, 3, 1)
        assert captured["parsed_end_time"] == dt.date(2024, 9, 1)
        assert captured["ticker"] == "AAPL"
        if kind == "statistical":
            assert captured["frequency"] == "W"
        else:
            # market_review declares no frequency: the job's value survives.
            assert captured["frequency"] == "ME"

    def test_without_query_params_the_job_values_survive(self, monkeypatch):
        captured = self._render("statistical", "", monkeypatch)
        assert captured["frequency"] == "ME"
        assert captured["parsed_start_time"] == dt.date(2020, 1, 1)

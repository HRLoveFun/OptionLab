"""Tests for the streaming render endpoints (/render/<kind>).

These verify:
  - Skeleton-only POST '/' (no heavy compute, returns immediately)
  - Each /render/<kind> returns a fragment when given a valid job
  - Expired/unknown job returns a graceful error fragment (HTTP 200)
  - Slice exceptions are caught and rendered as an error fragment
"""

from unittest.mock import patch

import pytest

from data_pipeline import job_cache as jc


@pytest.fixture
def client():
    from app import app

    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_cache():
    jc._reset()
    yield
    jc._reset()


# Form payload accepted by ValidationService.
VALID_FORM = {
    "ticker": "AAPL",
    "start_time": "202001",
    "frequency": "D",
    "risk_threshold": "50",
    "side_bias": "Natural",
    "rolling_window": "20",
}


# ───────────────────────────────────────────────────────────────────────────
# POST '/' returns a skeleton, not full analysis
# ───────────────────────────────────────────────────────────────────────────


class TestPostSkeleton:
    def test_post_returns_skeleton_with_job_id(self, client):
        resp = client.post("/", data=VALID_FORM)
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # The skeleton must reference the streaming render endpoints.
        assert "/render/market_review" in html
        assert "/render/statistical" in html
        assert "/render/assessment" in html
        assert "/render/options_chain" in html
        # And expose a job id for the JS ticker switcher.
        assert "STREAMING_JOB_ID" in html
        # Exactly one job should be cached after a single POST.
        assert jc._size() == 1

    def test_post_with_invalid_form_does_not_create_job(self, client):
        # Empty ticker should fail validation before job creation.
        resp = client.post("/", data={"ticker": "", "frequency": "D"})
        # Either re-renders form with error or 400 — either way, no job.
        assert jc._size() == 0


# ───────────────────────────────────────────────────────────────────────────
# /render/<kind> happy path + edge cases
# ───────────────────────────────────────────────────────────────────────────


class TestRenderRoutes:
    @pytest.mark.parametrize(
        "kind",
        ["market_review", "statistical", "assessment", "options_chain"],
    )
    def test_missing_job_returns_error_fragment(self, client, kind):
        resp = client.get(f"/render/{kind}?ticker=AAPL")
        assert resp.status_code == 400
        html = resp.get_data(as_text=True)
        assert "missing" in html.lower() or "error" in html.lower()

    @pytest.mark.parametrize(
        "kind",
        ["market_review", "statistical", "assessment", "options_chain"],
    )
    def test_unknown_job_returns_session_expired(self, client, kind):
        resp = client.get(f"/render/{kind}?job=bogus&ticker=AAPL")
        # Return 200 with a graceful "session expired" so HTMX swaps a
        # readable message instead of a hard error.
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "expired" in html.lower() or "error" in html.lower()

    def test_slice_exception_returns_error_fragment(self, client):
        job_id = jc.create_job(VALID_FORM, ["AAPL"])

        def _boom(form_data):
            raise RuntimeError("synthetic failure")

        with patch(
            "services.analysis_service.AnalysisService.generate_market_review_slice",
            side_effect=_boom,
        ):
            resp = client.get(f"/render/market_review?job={job_id}&ticker=AAPL")
        assert resp.status_code == 500
        html = resp.get_data(as_text=True)
        assert "synthetic failure" in html or "error" in html.lower()

    def test_render_uses_jobcache_memoisation(self, client):
        """Two GETs for the same (job, ticker, kind) must invoke the slice once."""
        job_id = jc.create_job(VALID_FORM, ["AAPL"])
        calls = {"n": 0}

        def _ok(form_data):
            calls["n"] += 1
            return {"market_review_chart": None}

        with patch(
            "services.analysis_service.AnalysisService.generate_market_review_slice",
            side_effect=_ok,
        ):
            r1 = client.get(f"/render/market_review?job={job_id}&ticker=AAPL")
            r2 = client.get(f"/render/market_review?job={job_id}&ticker=AAPL")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert calls["n"] == 1

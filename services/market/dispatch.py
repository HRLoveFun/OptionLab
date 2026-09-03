"""Streaming render dispatch for the lazy-tab /render/<kind> endpoints.

Domain:    Services — Streaming Render Dispatch
Context:
  - Central handler behind every ``/render/<kind>`` route. It resolves the job,
    memoises the computed slice, and renders the matching fragment template.
  - WHY this lives in ``services/`` and not ``utils/``: it needs Flask, the job
    cache and two service facades. Keeping it in ``utils/`` made the utils layer
    depend *upward* on services, which in turn made utils un-testable in
    isolation and hid a genuine layering inversion (ADR 0001).
Contracts:
  - render_streaming_slice(kind) -> Response | tuple[str, int]
Dependencies UPWARD:
  - data_pipeline.job_cache, data_pipeline.db
  - services.market.analysis, services.options.chain
  - utils.constants, utils.render_helpers
Dependencies DOWNWARD:
  - routes/core.py
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from flask import render_template, request

from data_pipeline.db import close_thread_conn
from data_pipeline.job_cache import compute_or_get, get_job
from services.market.analysis import AnalysisService
from services.options.chain import OptionsChainService
from utils.constants import (
    DEFAULT_FREQUENCY,
    DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SIDE_BIAS,
    DEFAULT_TICKER,
)
from utils.render_helpers import render_error_fragment

logger = logging.getLogger(__name__)

_RENDER_KIND_SLICES: dict[str, tuple[str | None, str]] = {
    # kind: (slice_fn_attr_name | None, fragment_template)
    # We store the attribute name (not the bound function) so that monkey-
    # patching AnalysisService methods in tests is honoured at call time.
    "market_review": ("generate_market_review_slice", "partials/fragments/market_review.html"),
    "statistical": ("generate_statistical_slice", "partials/fragments/statistical.html"),
    "assessment": ("generate_assessment_slice", "partials/fragments/assessment.html"),
    "options_chain": (None, "partials/fragments/options_chain.html"),  # special-cased below
}


def render_streaming_slice(kind: str) -> Any:
    """Shared handler for /render/<kind>?job=…&ticker=….

    Looks up the job, dispatches to the slice fn, memoises the result in the
    JobCache, and renders the matching fragment template.

    WHY: When a user opens a /render/* URL directly (refresh, bookmark, copy
    link), there is no job in cache. Rather than show a dead-end error, we
    auto-create a job using DEFAULT_TICKER + default form params so the
    page is at least populated; users can then re-submit the form for a
    custom analysis.
    """
    job_id = request.args.get("job", "")
    ticker = (request.args.get("ticker", "") or "").upper()

    # WHY: missing job_id ⇒ direct access (refresh / bookmark / shared link).
    # Auto-bootstrap with default form params so the user lands on a
    # populated page instead of an error fragment. Fallback uses a synthetic
    # job entry held only for the duration of this request.
    fallback_form: dict[str, Any] | None = None
    if not job_id:
        if not ticker:
            ticker = DEFAULT_TICKER
        fallback_form = {
            "ticker": ticker,
            "frequency": DEFAULT_FREQUENCY,
            "start_time": "",
            "end_time": "",
            "parsed_start_time": dt.date.today() - dt.timedelta(days=365 * 2),
            "parsed_end_time": dt.date.today(),
            "rolling_window": DEFAULT_ROLLING_WINDOW,
            "risk_threshold": DEFAULT_RISK_THRESHOLD,
            "side_bias": DEFAULT_SIDE_BIAS,
            "target_bias": 0,
        }

    if not ticker:
        return render_error_fragment(kind, "missing job or ticker", 400)

    job = None
    if fallback_form is None:
        job = get_job(job_id)
        if job is None:
            # Treat as a soft 200 so HTMX swaps a useful message instead of a
            # browser-default error toast — but include the job-expired hint so
            # the user knows to re-submit the form.
            return render_error_fragment(kind, "session expired (job no longer cached); please re-submit the form", 200)

    slice_fn_name, template = _RENDER_KIND_SLICES[kind]

    # The form_data captured at POST time was for the first ticker. When the
    # user switches tickers via the sidebar we re-target by overriding
    # `ticker` in a per-call form_data copy.
    def _compute(form_data: dict[str, Any]) -> dict[str, Any]:
        # Worker-thread cleanup so we don't leak DB connections.
        try:
            local_form = {**form_data, "ticker": ticker}
            if kind == "options_chain":
                # Direct OptionsChainService call — no MarketAnalyzer needed.
                try:
                    return OptionsChainService.generate_options_chain_analysis(ticker) or {}
                except Exception as e:
                    logger.error("options_chain slice failed for %s: %s", ticker, e, exc_info=True)
                    return {"oc_error": str(e)}
            # Late-bind the slice attr so test monkey-patches are honoured.
            slice_fn = getattr(AnalysisService, slice_fn_name)
            return slice_fn(local_form)
        finally:
            close_thread_conn()

    try:
        if fallback_form is not None:
            # No job in cache — compute directly with the synthetic form.
            result = _compute(fallback_form)
        else:
            result = compute_or_get(job_id, ticker, kind, _compute)
    except KeyError:
        return render_error_fragment(kind, "session expired", 200)
    except Exception as e:
        logger.error("/render/%s failed for ticker=%s: %s", kind, ticker, e, exc_info=True)
        return render_error_fragment(kind, str(e), 500)

    # Build the template context. The fragment templates expect form-style
    # variables (frequency, start_time, etc.) so we merge job form_data with
    # the slice result.
    base_form = fallback_form if fallback_form is not None else (job.form_data or {})
    context = {**base_form, "ticker": ticker, **(result or {})}
    return render_template(template, **context)

"""Core dashboard and meta routes.

Routes:
  GET  /                    — main dashboard (form skeleton)
  POST /                    — form submission → streaming skeleton
  GET  /api/ping            — liveness probe
  GET  /api/_meta           — v1 route discovery
  GET  /render/<kind>       — HTMX streaming fragments
  POST /api/validate_ticker — single ticker validation
  POST /api/validate_tickers— bulk ticker validation
"""

from __future__ import annotations

import datetime as dt
import logging

from flask import Blueprint, jsonify, render_template, request

from data_pipeline.job_cache import create_job
from services.form_service import FormService
from services.market_service import MarketService
from services.validation_service import ValidationService
from utils.render_helpers import render_streaming_slice
from utils.ticker_utils import normalize_ticker, parse_tickers
from utils.constants import (
    DEFAULT_FREQUENCY,
    DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SIDE_BIAS,
    DEFAULT_TICKER,
)
from utils.date_helpers import parse_month_str

logger = logging.getLogger(__name__)

bp = Blueprint("core", __name__)


@bp.route("/api/ping", methods=["GET"])
def api_ping():
    """Lightweight liveness probe used by the HTMX scaffold probe in index.html."""
    return jsonify({"ok": True})


@bp.route("/api/_meta", methods=["GET"])
def api_v1_meta():
    """Lightweight discovery endpoint listing v1-stable routes."""
    from flask import current_app

    return jsonify(
        {
            "status": "ok",
            "version": "v1",
            "routes": sorted(
                {
                    r.rule
                    for r in current_app.url_map.iter_rules()
                    if r.rule.startswith("/api/")
                }
            ),
        }
    )


@bp.route("/", methods=["GET", "POST"])
def index():
    """
    Main dashboard route.

    GET:  render the empty form / skeleton.
    POST: validate form, register a JobCache entry, and immediately render the
          *skeleton* index.html with `streaming_mode=True`.
    """
    try:
        if request.method == "POST":
            form_data = FormService.extract_form_data(request)
            validation_error = ValidationService.validate_input_data(form_data)

            if validation_error:
                return render_template("index.html", error=validation_error)

            tickers_raw = form_data.get("ticker", "")
            tickers = parse_tickers(tickers_raw)
            if not tickers:
                return render_template(
                    "index.html", error="Please enter at least one ticker symbol."
                )

            first_ticker = tickers[0]
            job_id = create_job({**form_data, "ticker": first_ticker}, tickers)

            template_data = {
                **form_data,
                "ticker": first_ticker,
                "tickers": tickers,
                "tickers_raw": ", ".join(tickers),
                "streaming_mode": True,
                "job_id": job_id,
                "summary_pending": len(tickers) > 1,
            }
            return render_template("index.html", **template_data)

        return render_template(
            "index.html",
            ticker=DEFAULT_TICKER,
            tickers=[DEFAULT_TICKER],
            tickers_raw=DEFAULT_TICKER,
            start_time=(lambda today: f"{today.year - 5}-{today.month:02d}")(dt.date.today()),
            end_time="",
            frequency=DEFAULT_FREQUENCY,
            risk_threshold=DEFAULT_RISK_THRESHOLD,
            rolling_window=DEFAULT_ROLLING_WINDOW,
            side_bias=DEFAULT_SIDE_BIAS,
        )

    except Exception as e:
        logger.error("Unexpected error in main route: %s", e, exc_info=True)
        return render_template(
            "index.html", error=f"An unexpected error occurred: {str(e)}. Please try again."
        )


# ── HTMX streaming render endpoints ──────────────────────────────────────────


@bp.route("/render/market_review", methods=["GET"])
def render_market_review():
    return render_streaming_slice("market_review")


@bp.route("/render/statistical", methods=["GET"])
def render_statistical():
    return render_streaming_slice("statistical")


@bp.route("/render/assessment", methods=["GET"])
def render_assessment():
    return render_streaming_slice("assessment")


@bp.route("/render/options_chain", methods=["GET"])
def render_options_chain():
    return render_streaming_slice("options_chain")


# ── Ticker validation ──────────────────────────────────────────────


@bp.route("/api/validate_ticker", methods=["POST"])
def validate_ticker():
    """
    API endpoint to validate ticker symbol.
    Request: JSON {"ticker": "AAPL"} or {"ticker": "US.AAPL"}
    Response: {"valid": true/false, "message": "..."}
    """
    try:
        data = request.get_json()
        raw_ticker = data.get("ticker", "").upper()

        if not raw_ticker:
            return jsonify({"valid": False, "message": "Please enter a ticker symbol"})

        yahoo_ticker, _futu = normalize_ticker(raw_ticker)
        is_valid, message = MarketService.validate_ticker(yahoo_ticker)

        return jsonify({"valid": is_valid, "message": message})

    except Exception as e:
        logger.error("Error validating ticker: %s", e)
        return jsonify({"valid": False, "message": f"Error validating ticker: {str(e)}"})


@bp.route("/api/validate_tickers", methods=["POST"])
def validate_tickers_bulk():
    """Validate multiple tickers at once. Returns {status, results: {TICKER: {valid, price, message}}}."""
    data = request.get_json(silent=True) or {}
    tickers = data.get("tickers", [])
    results = {}
    for raw_ticker in tickers[:10]:
        try:
            yahoo_ticker, _futu = normalize_ticker(raw_ticker)
            is_valid, message = MarketService.validate_ticker(yahoo_ticker)
            price = None
            if is_valid:
                try:
                    from data_pipeline.yf_client import fetch_spot

                    price = fetch_spot(yahoo_ticker)
                except Exception:
                    pass
            results[raw_ticker] = {"valid": is_valid, "price": price, "message": message}
        except Exception:
            results[raw_ticker] = {"valid": False, "price": None, "message": "validation error"}
    return jsonify({"status": "ok", "results": results})

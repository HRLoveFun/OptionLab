"""Data health and seed routes.

Routes:
  GET  /health/data
  GET  /health/status
  POST /api/data/seed
"""

from __future__ import annotations

import logging
import os

from flask import Blueprint, jsonify, request

from data_pipeline.data_ops import DataService
from utils.rate_limit import client_ip, rate_limit
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

bp = Blueprint("data", __name__)


@bp.route("/health/data", methods=["GET"])
def health_data():
    """Return data-quality snapshot of the local SQLite cache."""
    try:
        from services.health_service import overall_summary

        full = overall_summary()
        expected = os.environ.get("HEALTH_TOKEN", "").strip()
        provided = (
            request.args.get("token") or request.headers.get("X-Health-Token") or ""
        ).strip()
        if expected and provided != expected:
            return jsonify(
                {
                    "status": full.get("status"),
                    "generated_at": full.get("generated_at"),
                    "ticker_count": full.get("ticker_count"),
                    "total_rows": full.get("total_rows"),
                    "stale_count": len(full.get("stale_tickers", [])),
                    "nan_count": len(full.get("tickers_with_nan_close", [])),
                    "failures_24h_total": sum(
                        full.get("failures_24h_by_class", {}).values()
                    ),
                    "freshness_threshold_days": full.get("freshness_threshold_days"),
                    "redacted": True,
                }
            )
        return jsonify(full)
    except Exception as e:
        logger.error("health_data error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "health_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/health/status", methods=["GET"])
def health_status():
    """Public lightweight status endpoint for frontend degradation banner."""
    try:
        from services.health_service import overall_summary

        full = overall_summary()
        return jsonify(
            {
                "status": full.get("status"),
                "stale_count": len(full.get("stale_tickers", [])),
                "nan_count": len(full.get("tickers_with_nan_close", [])),
                "failures_24h_total": sum(
                    full.get("failures_24h_by_class", {}).values()
                ),
                "generated_at": full.get("generated_at"),
            }
        )
    except Exception as e:
        logger.error("health_status error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "health_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/data/seed", methods=["POST"])
def data_seed():
    """Seed multi-year per-ticker price history."""
    allowed, retry = rate_limit(f"seed:{client_ip()}", max_calls=5, window_sec=3600)
    if not allowed:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "rate_limited",
                    "message": f"Too many seed requests. Retry after {retry}s.",
                    "retry_after": retry,
                }
            ),
            429,
        )

    data = request.get_json(silent=True) or {}
    raw_ticker = (data.get("ticker") or "").strip()
    if not raw_ticker:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "invalid_ticker",
                    "message": "Body must include non-empty 'ticker'.",
                }
            ),
            400,
        )
    try:
        yahoo_ticker, _ = normalize_ticker(raw_ticker)
        ticker = (yahoo_ticker or raw_ticker).upper()
    except (ValueError, ImportError):
        ticker = raw_ticker.upper()
    try:
        years = int(data.get("years", 5))
    except (TypeError, ValueError):
        years = 5
    years = max(1, min(years, 35))
    try:
        DataService.clear_ensure_range_memo(ticker)
        DataService.seed_history(ticker, years=years)
        return jsonify({"status": "ok", "ticker": ticker, "years": years})
    except Exception as e:
        logger.error("data_seed error for %s: %s", ticker, e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "seed_failed", "message": str(e)}
            ),
            500,
        )

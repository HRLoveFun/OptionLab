"""Market regime routes.

Routes:
  GET  /api/regime/current
  GET  /api/regime/history
  POST /api/regime/backfill
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from utils.rate_limit import client_ip, rate_limit

logger = logging.getLogger(__name__)

bp = Blueprint("regime", __name__)


@bp.route("/api/regime/current", methods=["GET"])
def regime_current():
    """Current composite regime label (VIX / SPY)."""
    from services.regime_service import RegimeService

    persist = request.args.get("persist", "0").lower() in ("1", "true", "yes")
    try:
        result = RegimeService.append_today() if persist else RegimeService.compute_current()
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("regime_current error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "regime_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/regime/history", methods=["GET"])
def regime_history():
    """Regime history (persisted log, or live fallback if log is empty)."""
    from services.regime_service import RegimeService

    try:
        days = int(request.args.get("days", 180))
    except (TypeError, ValueError):
        days = 180
    days = max(1, min(days, 3650))
    try:
        result = RegimeService.history(days=days)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("regime_history error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "regime_history_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/regime/backfill", methods=["POST"])
def regime_backfill():
    """Backfill regime log for the last N trading days."""
    from services.regime_service import RegimeService

    allowed, retry = rate_limit(f"backfill:{client_ip()}", max_calls=5, window_sec=3600)
    if not allowed:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "rate_limited",
                    "message": f"Too many backfill requests. Retry after {retry}s.",
                    "retry_after": retry,
                }
            ),
            429,
        )

    data = request.get_json(silent=True) or {}
    try:
        days = int(data.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    days = max(1, min(days, 365))
    try:
        result = RegimeService.backfill(days=days)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("regime_backfill error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "regime_backfill_failed", "message": str(e)}
            ),
            500,
        )

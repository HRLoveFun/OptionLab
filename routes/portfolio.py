"""Portfolio and position-tracking routes.

Routes:
  POST /api/portfolio_analysis
  GET/POST /api/portfolio/positions
  POST /api/portfolio/positions/<id>/close
  GET  /api/portfolio/snapshot
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

bp = Blueprint("portfolio", __name__)


@bp.route("/api/portfolio_analysis", methods=["POST"])
def portfolio_analysis():
    """Analyse a multi-leg option portfolio."""
    data = request.get_json(silent=True) or {}
    positions = data.get("positions", [])
    account_size = data.get("account_size")
    max_risk_pct = data.get("max_risk_pct", 2.0)

    if not positions:
        return (
            jsonify(
                {"status": "error", "code": "no_positions", "message": "No positions provided"}
            ),
            400,
        )

    try:
        from services.portfolio_analysis_service import PortfolioAnalysisService

        result = PortfolioAnalysisService.run(positions, account_size, max_risk_pct)
        return jsonify(result)
    except Exception as e:
        logger.error("portfolio_analysis error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "portfolio_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/portfolio/positions", methods=["GET", "POST"])
def portfolio_positions():
    """List open positions (GET) or create a new one (POST)."""
    from services.portfolio_service import create_position, list_positions

    if request.method == "POST":
        return jsonify(create_position(request.get_json(silent=True) or {}))
    status = request.args.get("status", "open") or None
    return jsonify({"status": "ok", "positions": list_positions(status=status)})


@bp.route("/api/portfolio/positions/<int:position_id>/close", methods=["POST"])
def portfolio_close(position_id: int):
    from services.portfolio_service import close_position

    body = request.get_json(silent=True) or {}
    return jsonify(close_position(position_id, float(body.get("closed_value", 0.0))))


@bp.route("/api/portfolio/snapshot", methods=["GET"])
def portfolio_snapshot_route():
    """Aggregate Greeks + per-position P&L attribution across all open positions."""
    from services.portfolio_service import portfolio_snapshot

    return jsonify(portfolio_snapshot())

"""Multi-leg strategy routes.

Routes:
  GET  /api/strategies
  POST /api/strategy/analyze
  POST /api/strategy/build_from_chain
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from utils.api_errors import ApiError
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

bp = Blueprint("strategies", __name__)


@bp.route("/api/strategies", methods=["GET"])
def list_strategies():
    """Return the catalog of supported multi-leg strategies."""
    from services.strategy_service import list_strategies as _list

    return jsonify({"status": "ok", "strategies": _list()})


@bp.route("/api/strategy/analyze", methods=["POST"])
def analyze_strategy_route():
    """Analyse a multi-leg strategy: payoff, breakevens, Greeks, PoP."""
    data = request.get_json(silent=True) or {}
    try:
        from services.strategy_service import analyze

        return jsonify(analyze(data))
    except Exception as e:
        logger.error("analyze_strategy_route error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "strategy_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/strategy/build_from_chain", methods=["POST"])
def build_strategy_from_chain():
    """Auto-fill a strategy template from the live option chain."""
    from services.strategy_builder import build_from_chain

    data = request.get_json(silent=True) or {}
    raw_ticker = (data.get("ticker") or "").strip().upper()
    if not raw_ticker:
        raise ApiError("ticker is required", code="ticker_required")
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    return jsonify(
        build_from_chain(
            ticker=ticker,
            template=(data.get("template") or data.get("strategy") or "").strip(),
            expiry=data.get("expiry", ""),
            strikes=data.get("strikes", {}) or {},
            qty=int(data.get("qty", 1) or 1),
        )
    )

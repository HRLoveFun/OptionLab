"""Market-data signal and review routes.

Routes:
  GET  /api/signals
  POST /api/market_review_ts
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

bp = Blueprint("market", __name__)


@bp.route("/api/signals", methods=["GET"])
def signals_route():
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return (
            jsonify(
                {"status": "error", "code": "missing_ticker", "message": "ticker is required"}
            ),
            400,
        )
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    iv_pct = request.args.get("iv_pct")
    iv_pct_val = float(iv_pct) if iv_pct not in (None, "") else None
    try:
        from services.signals_service import get_signals

        return jsonify(get_signals(ticker, current_iv_pct=iv_pct_val))
    except Exception as e:
        logger.error("signals_route error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "signals_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/market_review_ts", methods=["POST"])
def market_review_ts():
    """Return time-series data for interactive Market Review chart."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    start_date = data.get("start_date")
    if not raw_ticker:
        return (
            jsonify(
                {"status": "error", "code": "missing_ticker", "message": "No ticker provided"}
            ),
            400,
        )
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    try:
        from core.market_review import market_review_timeseries

        result = market_review_timeseries(ticker, start_date=start_date)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("market_review_ts error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "market_review_failed", "message": str(e)}
            ),
            500,
        )

"""Options-chain routes.

Routes:
  GET  /api/option_chain
  POST /api/preload_option_chain
  GET  /api/options_chart/iv_smile
  GET  /api/options_chart/oi_profile
  POST /api/odds_with_vol
  POST /api/simulate_expiry
"""

from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request

from services.options.chain import OptionsChainService
from services.options.preload import (
    build_preload_payload,
)
from services.options.preload import (
    get_cached as get_preload_cached,
)
from services.options.preload import (
    set_cached as set_preload_cached,
)
from services.options.simulation import generate_expiry_calendar_service, run_simulation
from utils.api_errors import ApiError
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

bp = Blueprint("options", __name__)


@bp.route("/api/option_chain", methods=["GET"])
def option_chain():
    """
    API endpoint to fetch live option chain data via Yahoo Finance.
    Query params: ticker (required), max_dte (default 45),
                  moneyness_low (default 0.7), moneyness_high (default 1.3),
                  max_contracts (default 1000)
    """
    ticker_sym = request.args.get("ticker", "").strip().upper()
    if not ticker_sym:
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "missing_ticker",
                    "message": "ticker is required",
                    "error": "ticker is required",
                }
            ),
            400,
        )

    try:
        ticker_sym, _ = normalize_ticker(ticker_sym)
    except ValueError:
        pass  # keep as-is

    max_dte = int(request.args.get("max_dte", 45))
    moneyness_low = float(request.args.get("moneyness_low", 0.7))
    moneyness_high = float(request.args.get("moneyness_high", 1.3))
    max_contracts = int(request.args.get("max_contracts", 1000))

    try:
        result = OptionsChainService.fetch_records_filtered(
            ticker_sym, max_dte, moneyness_low, moneyness_high, max_contracts
        )
        if not result.get("expirations"):
            msg = f"No options available for {ticker_sym}"
            return (
                jsonify(
                    {
                        "status": "error",
                        "code": "no_options",
                        "message": msg,
                        "error": msg,
                    }
                ),
                404,
            )
        return jsonify(result)
    except Exception as e:
        logger.error("Error fetching option chain for %s: %s", ticker_sym, e, exc_info=True)
        msg = f"获取期权链失败: {str(e)}"
        return (
            jsonify(
                {
                    "status": "error",
                    "code": "option_chain_failed",
                    "message": msg,
                    "error": msg,
                }
            ),
            500,
        )


@bp.route("/api/preload_option_chain", methods=["POST"])
def preload_option_chain():
    """Pre-load option chain for Position module dropdowns."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    if not raw_ticker:
        return (
            jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}),
            400,
        )

    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker

    cached = get_preload_cached(ticker)
    if cached:
        return jsonify({"status": "ok", **cached})

    try:
        payload = build_preload_payload(ticker)
        set_preload_cached(ticker, payload)
        return jsonify({"status": "ok", **payload})
    except Exception as e:
        logger.error("preload_option_chain failed for %s: %s", ticker, e)
        return (
            jsonify({"status": "error", "code": "option_chain_failed", "message": str(e)}),
            500,
        )


@bp.route("/api/options_chart/iv_smile", methods=["GET"])
def iv_smile_json():
    """Return IV smile data points for client-side Chart.js rendering."""
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return (
            jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required"}),
            400,
        )
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    expiry = request.args.get("expiry")
    try:
        points = OptionsChainService.iv_smile_points(ticker, expiry)
        if not points:
            return (
                jsonify({"status": "error", "code": "no_expiries", "message": "no expiries"}),
                404,
            )
        return jsonify({"status": "ok", "ticker": ticker, **points})
    except Exception as e:
        logger.error("iv_smile_json error: %s", e, exc_info=True)
        return (
            jsonify({"status": "error", "code": "iv_smile_failed", "message": str(e)}),
            500,
        )


@bp.route("/api/options_chart/oi_profile", methods=["GET"])
def oi_profile_json():
    """Return OI / Volume profile data for client-side rendering."""
    raw_ticker = (request.args.get("ticker", "") or "").strip().upper()
    if not raw_ticker:
        return (
            jsonify({"status": "error", "code": "missing_ticker", "message": "ticker is required"}),
            400,
        )
    try:
        ticker, _ = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    expiry = request.args.get("expiry")
    try:
        points = OptionsChainService.oi_profile_points(ticker, expiry)
        if not points:
            return (
                jsonify({"status": "error", "code": "no_expiries", "message": "no expiries"}),
                404,
            )
        return jsonify({"status": "ok", "ticker": ticker, **points})
    except Exception as e:
        logger.error("oi_profile_json error: %s", e, exc_info=True)
        return (
            jsonify({"status": "error", "code": "oi_profile_failed", "message": str(e)}),
            500,
        )


@bp.route("/api/odds_with_vol", methods=["POST"])
def odds_with_vol():
    """Return odds data enriched with implied realized vol vs ATM IV."""
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    target_pct = float(data.get("target_pct", 10))
    if not raw_ticker:
        return (
            jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}),
            400,
        )
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    try:
        result = OptionsChainService.odds_with_vol(ticker, target_pct)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("odds_with_vol error: %s", e, exc_info=True)
        return (
            jsonify({"status": "error", "code": "odds_failed", "message": str(e)}),
            500,
        )


@bp.route("/api/simulate_expiry", methods=["POST"])
def simulate_expiry_route():
    """Simulate expiration P&L across strikes × expiries × implied vols.

    Body: {ticker, spot?, option_type, side, strikes?, expiries?, ivs?,
           r?, qty?, multiplier?, n_points?, range_pct?}
    """
    data = request.get_json(silent=True) or {}
    return jsonify(run_simulation(data))


@bp.route("/api/expiry_calendar", methods=["GET"])
def expiry_calendar_route():
    """List standard listed + daily expirations for the Option Pricing Matrix columns.

    Query params: ref (default today in US/Eastern, 'YYYY-MM-DD'),
                   standard (default 12), daily (default 10).
    """
    ref = request.args.get("ref") or dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    n_standard = request.args.get("standard", 12)
    n_daily = request.args.get("daily", 10)
    try:
        result = generate_expiry_calendar_service(ref, n_standard, n_daily)
    except ApiError as e:
        return (
            jsonify({"status": "error", "code": e.code, "message": e.message}),
            e.status or 400,
        )
    return jsonify(result)

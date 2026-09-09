"""Options-chain routes.

Routes:
  GET  /api/option_chain
  POST /api/preload_option_chain
  GET  /api/options_chart/iv_smile
  GET  /api/options_chart/oi_profile
  POST /api/expiry_probability
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


def _num_arg(name: str, default: float, cast=float) -> float:
    """Parse a numeric query param, mapping garbage input to 400 (not 500).

    CONSTRAINT: the unified error contract says malformed client input is a
    400 ``invalid_parameter`` — a bare ``int(request.args[...])`` used to fall
    through to the global 500 ``internal_error`` handler.
    """
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        raise ApiError(f"参数 {name} 不是合法数字", code="invalid_parameter", status=400)


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

    max_dte = _num_arg("max_dte", 45, int)
    moneyness_low = _num_arg("moneyness_low", 0.7)
    moneyness_high = _num_arg("moneyness_high", 1.3)
    max_contracts = _num_arg("max_contracts", 1000, int)

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
        msg = "获取期权链失败，请稍后重试"
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
        logger.error("preload_option_chain failed for %s: %s", ticker, e, exc_info=True)
        return (
            jsonify({"status": "error", "code": "option_chain_failed", "message": "预加载期权链失败，请稍后重试"}),
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
            jsonify({"status": "error", "code": "iv_smile_failed", "message": "获取 IV Smile 失败，请稍后重试"}),
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
            jsonify({"status": "error", "code": "oi_profile_failed", "message": "获取 OI 分布失败，请稍后重试"}),
            500,
        )


@bp.route("/api/expiry_probability", methods=["POST"])
def expiry_probability():
    """Return probability-of-touch data enriched with ATM IV context.

    Vol-adjusted probabilities (touch / ITM), distinct from the Payoff Ratio
    tab's per-strike return multiples. Its DOM container is not currently wired
    into the partial — see ADR 0010.
    """
    data = request.get_json(silent=True) or {}
    raw_ticker = data.get("ticker", "").strip().upper()
    if not raw_ticker:
        return (
            jsonify({"status": "error", "code": "missing_ticker", "message": "No ticker provided"}),
            400,
        )
    try:
        target_pct = float(data.get("target_pct", 10))
    except (TypeError, ValueError):
        raise ApiError("target_pct 必须是数字", code="invalid_parameter", status=400)
    if not (0 < target_pct <= 100):
        raise ApiError("target_pct 必须在 (0, 100] 区间", code="invalid_parameter", status=400)
    try:
        ticker, _futu = normalize_ticker(raw_ticker)
    except ValueError:
        ticker = raw_ticker
    try:
        result = OptionsChainService.expiry_probability(ticker, target_pct)
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("expiry_probability error: %s", e, exc_info=True)
        return (
            jsonify({"status": "error", "code": "probability_failed", "message": "计算胜率失败，请稍后重试"}),
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

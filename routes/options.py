"""Options-chain routes.

Routes:
  GET  /api/option_chain
  POST /api/preload_option_chain
  GET  /api/options_chart/iv_smile
  GET  /api/options_chart/oi_profile
  POST /api/odds_with_vol
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from core.options.chain.filters import filter_option_chain
from core.options_chain_analyzer import OptionsChainAnalyzer
from services.options_chain_preload import (
    build_preload_payload,
)
from services.options_chain_preload import (
    get_cached as get_preload_cached,
)
from services.options_chain_preload import (
    set_cached as set_preload_cached,
)
from services.options_chain_service import OptionsChainService
from utils.ticker_utils import normalize_ticker

logger = logging.getLogger(__name__)

bp = Blueprint("options", __name__)

_IV_LO, _IV_HI = 0.01, 5.0


def _iv_ok(v):
    try:
        return _IV_LO <= float(v) <= _IV_HI
    except (TypeError, ValueError):
        return False


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
        result = OptionsChainService.fetch_records(ticker_sym)
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
        result = filter_option_chain(
            result, max_dte, moneyness_low, moneyness_high, max_contracts
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
            jsonify(
                {"status": "error", "code": "missing_ticker", "message": "No ticker provided"}
            ),
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
            jsonify(
                {"status": "error", "code": "option_chain_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/options_chart/iv_smile", methods=["GET"])
def iv_smile_json():
    """Return IV smile data points for client-side Chart.js rendering."""
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
    expiry = request.args.get("expiry")
    try:
        analyzer = OptionsChainAnalyzer(ticker)
        if not analyzer.expiries:
            return (
                jsonify(
                    {"status": "error", "code": "no_expiries", "message": "no expiries"}
                ),
                404,
            )
        exp = expiry if expiry in analyzer.chain else analyzer.expiries[0]
        calls = analyzer.chain[exp]["calls"].dropna(subset=["impliedVolatility"])
        puts = analyzer.chain[exp]["puts"].dropna(subset=["impliedVolatility"])
        calls = calls[calls["impliedVolatility"].apply(_iv_ok)]
        puts = puts[puts["impliedVolatility"].apply(_iv_ok)]
        return jsonify(
            {
                "status": "ok",
                "ticker": ticker,
                "expiry": exp,
                "spot": round(analyzer.spot, 2),
                "calls": [
                    {"strike": float(r.strike), "iv_pct": float(r.impliedVolatility) * 100}
                    for r in calls.itertuples()
                ],
                "puts": [
                    {"strike": float(r.strike), "iv_pct": float(r.impliedVolatility) * 100}
                    for r in puts.itertuples()
                ],
            }
        )
    except Exception as e:
        logger.error("iv_smile_json error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "iv_smile_failed", "message": str(e)}
            ),
            500,
        )


@bp.route("/api/options_chart/oi_profile", methods=["GET"])
def oi_profile_json():
    """Return OI / Volume profile data for client-side rendering."""
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
    expiry = request.args.get("expiry")
    try:
        analyzer = OptionsChainAnalyzer(ticker)
        if not analyzer.expiries:
            return (
                jsonify(
                    {"status": "error", "code": "no_expiries", "message": "no expiries"}
                ),
                404,
            )
        exp = expiry if expiry in analyzer.chain else analyzer.expiries[0]
        calls = analyzer.chain[exp]["calls"]
        puts = analyzer.chain[exp]["puts"]
        return jsonify(
            {
                "status": "ok",
                "ticker": ticker,
                "expiry": exp,
                "spot": round(analyzer.spot, 2),
                "calls": [
                    {
                        "strike": float(r.strike),
                        "oi": float(r.openInterest or 0),
                        "volume": float(r.volume or 0),
                    }
                    for r in calls.itertuples()
                ],
                "puts": [
                    {
                        "strike": float(r.strike),
                        "oi": float(r.openInterest or 0),
                        "volume": float(r.volume or 0),
                    }
                    for r in puts.itertuples()
                ],
            }
        )
    except Exception as e:
        logger.error("oi_profile_json error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "oi_profile_failed", "message": str(e)}
            ),
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
        from core.options_chain_analyzer import get_odds_with_vol_context

        analyzer = OptionsChainAnalyzer(ticker)
        result = get_odds_with_vol_context(
            spot=analyzer.spot,
            target_pct=target_pct,
            chain=analyzer.chain,
            expiries=analyzer.expiries,
        )
        return jsonify({"status": "ok", **result})
    except Exception as e:
        logger.error("odds_with_vol error: %s", e, exc_info=True)
        return (
            jsonify(
                {"status": "error", "code": "odds_failed", "message": str(e)}
            ),
            500,
        )

"""Strategy service — exposes core/strategies through the API layer."""

from __future__ import annotations

import inspect
import logging
import math

from core import strategies as S

logger = logging.getLogger(__name__)


# Map JSON-friendly names → factory functions.
_FACTORIES: dict[str, callable] = {
    "long_call": S.long_call,
    "long_put": S.long_put,
    "short_call": S.short_call,
    "short_put": S.short_put,
    "bull_call_spread": S.bull_call_spread,
    "bear_put_spread": S.bear_put_spread,
    "bear_call_spread": S.bear_call_spread,
    "bull_put_spread": S.bull_put_spread,
    "long_straddle": S.long_straddle,
    "long_strangle": S.long_strangle,
    "short_straddle": S.short_straddle,
    "short_strangle": S.short_strangle,
    "iron_condor": S.iron_condor,
    "long_butterfly": S.long_butterfly,
    "calendar_spread": S.calendar_spread,
}


def list_strategies() -> list[str]:
    return sorted(_FACTORIES.keys())


def _sanitise(value):
    """Convert NaN/inf to None so JSON serialisation succeeds."""
    if isinstance(value, dict):
        return {k: _sanitise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitise(v) for v in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    return value


def analyze(payload: dict) -> dict:
    """Build strategy from JSON payload, run analysis, return JSON-friendly dict.

    Expected payload shape::

        {
            "strategy": "iron_condor",
            "spot": 450.0,
            "params": {                 # kwargs forwarded to the factory
                "k_put_long": 430, ...
            }
        }

    Returns ``{status: "ok", ...analysis}`` or ``{status: "error", message: ...}``.
    """
    strategy_name = (payload or {}).get("strategy", "").strip()
    spot = payload.get("spot")
    params = payload.get("params", {}) or {}
    if not strategy_name or strategy_name not in _FACTORIES:
        return {
            "status": "error",
            "message": f"unknown strategy '{strategy_name}'. Valid: {list_strategies()}",
        }
    if not isinstance(spot, (int, float)) or spot <= 0:
        return {"status": "error", "message": "spot must be a positive number"}

    factory = _FACTORIES[strategy_name]
    try:
        legs = factory(**params)
    except TypeError as exc:
        # WHY: A bare TypeError message ("iron_condor() missing 8 required
        # positional arguments: 'k_put_long', ...") leaks the Python signature
        # to the API. Replace it with a structured response listing the
        # parameters the factory actually expects so the frontend can drive
        # a form / show a useful hint.
        try:
            sig = inspect.signature(factory)
            expected = [
                {
                    "name": p.name,
                    "required": p.default is inspect.Parameter.empty,
                    "default": None if p.default is inspect.Parameter.empty else p.default,
                }
                for p in sig.parameters.values()
                if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
            ]
            missing = [
                p["name"] for p in expected if p["required"] and p["name"] not in params
            ]
        except (TypeError, ValueError):
            expected, missing = [], []
        return {
            "status": "error",
            "code": "missing_params",
            "message": (
                f"strategy '{strategy_name}' is missing required parameters: "
                f"{', '.join(missing) if missing else exc}"
            ),
            "expected_params": expected,
            "missing": missing,
            "got": list(params.keys()),
        }
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    try:
        result = S.analyze_strategy(legs, spot=float(spot))
    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze_strategy failed: %s", exc)
        return {"status": "error", "message": f"analysis error: {exc}"}

    legs_out = [
        {
            "side": leg.side,
            "option_type": leg.option_type,
            "strike": leg.strike,
            "premium": leg.premium,
            "qty": leg.qty,
            "dte": leg.dte,
            "iv": leg.iv,
        }
        for leg in legs
    ]

    return _sanitise(
        {
            "status": "ok",
            "strategy": strategy_name,
            "spot": float(spot),
            "legs": legs_out,
            **result,
        }
    )

"""
Game Service — Orchestrates the put-option decision process for the Flask route.

Validates user inputs, delegates to core.option_decision, and formats the
response as a dict suitable for JSON serialisation.
"""

import logging

from core.option_decision import run_decision_process

logger = logging.getLogger(__name__)

# Input constraints
_BUDGET_MIN = 100.0
_BUDGET_MAX = 10_000_000.0
_MOVE_PCT_MIN = -0.50
_MOVE_PCT_MAX = -0.001
_HORIZON_MIN = 1
_HORIZON_MAX = 365
_CONVICTION_MIN = 0.0
_CONVICTION_MAX = 1.0
_VALID_VOL_TIMINGS = {"FAST", "MEDIUM", "SLOW"}


def _float_in(val, lo: float, hi: float, name: str) -> float:
    v = float(val)
    if not (lo <= v <= hi):
        raise ValueError(f"{name} must be between {lo} and {hi}")
    return v


def _int_in(val, lo: int, hi: int, name: str) -> int:
    v = int(val)
    if not (lo <= v <= hi):
        raise ValueError(f"{name} must be between {lo} and {hi}")
    return v


class GameService:
    """Thin orchestration layer for the option decision game."""

    @staticmethod
    def run(data: dict) -> dict:
        """Validate inputs from the API request and run the decision process.

        Parameters
        ----------
        data : dict
            Raw JSON body from the /api/game endpoint.

        Returns
        -------
        dict with 'status' key ('ok' or 'error').
        """
        try:
            ticker = (data.get("ticker") or "").strip().upper()
            if not ticker:
                return {"status": "error", "message": "Ticker is required."}

            # Normalize futu-format tickers to yahoo format
            from utils.ticker_utils import normalize_ticker

            try:
                ticker, _futu = normalize_ticker(ticker)
            except ValueError:
                pass

            budget = _float_in(data.get("budget", 5000), _BUDGET_MIN, _BUDGET_MAX, "budget")
            target_move_pct = _float_in(
                data.get("target_move_pct", -0.08), _MOVE_PCT_MIN, _MOVE_PCT_MAX, "target_move_pct"
            )
            time_horizon_days = _int_in(
                data.get("time_horizon_days", 21), _HORIZON_MIN, _HORIZON_MAX, "time_horizon_days"
            )
            directional_conviction = _float_in(
                data.get("directional_conviction", 0.5), _CONVICTION_MIN, _CONVICTION_MAX, "directional_conviction"
            )
            vol_conviction = _float_in(
                data.get("vol_conviction", 0.5), _CONVICTION_MIN, _CONVICTION_MAX, "vol_conviction"
            )
            vol_timing = (data.get("vol_timing") or "MEDIUM").strip().upper()
            if vol_timing not in _VALID_VOL_TIMINGS:
                return {"status": "error", "message": f"vol_timing must be one of {_VALID_VOL_TIMINGS}"}

            result = run_decision_process(
                ticker=ticker,
                budget=budget,
                target_move_pct=target_move_pct,
                time_horizon_days=time_horizon_days,
                directional_conviction=directional_conviction,
                vol_conviction=vol_conviction,
                vol_timing=vol_timing,
            )

            return {"status": "ok", **result}

        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"GameService.run failed: {e}", exc_info=True)
            return {"status": "error", "message": f"Analysis failed: {e}"}

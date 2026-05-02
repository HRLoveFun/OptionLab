"""Portfolio Analysis Service — Module 3

Coordinates Greeks, PnL, theta decay, risk breakdown, and VaR
for a multi-leg option portfolio.
"""

import logging

from core.options.greeks.portfolio import portfolio_greeks_table

from ._charts import _fig_to_base64, _plot_pnl, _plot_theta_decay
from ._normalize import _normalize_position
from ._risk import _calc_var, _find_breakevens, _position_sizing, _risk_breakdown

logger = logging.getLogger(__name__)


def _get_spots(positions: list) -> dict:
    tickers = list({p["ticker"] for p in positions})
    try:
        from data_pipeline.yf_client import fetch_spots_bulk

        return fetch_spots_bulk(tickers)
    except Exception as e:
        logger.warning(f"_get_spots error: {e}")
        return {}


class PortfolioAnalysisService:
    """Facade for portfolio-level option analysis."""

    @staticmethod
    def run(positions: list, account_size=None, max_risk_pct=2.0) -> dict:
        result = {"status": "ok", "warnings": []}

        try:
            positions = [_normalize_position(p) for p in (positions or [])]
        except ValueError as exc:
            return {"status": "error", "code": "bad_position_schema", "message": str(exc)}
        if not positions:
            return {"status": "error", "code": "no_positions", "message": "positions is empty"}

        spots = _get_spots(positions)
        main_ticker = positions[0]["ticker"]
        spot = spots.get(main_ticker, 100)

        # Build position list for greeks engine
        greeks_positions = []
        for pos in positions:
            greeks_positions.append(
                {
                    "type": pos["option_type"],
                    "strike": pos["strike"],
                    "dte": pos.get("dte", 30),
                    "iv": pos.get("iv", 0.25),
                    "qty": pos["quantity"],
                    "premium": pos["price"],
                }
            )

        # Greeks
        totals, detail_df = portfolio_greeks_table(greeks_positions, spot, r=0.05)
        result["greeks_summary"] = {k: round(v, 4) for k, v in totals.items()}
        result["greeks_detail"] = detail_df.to_dict(orient="records")

        # PnL chart
        try:
            pnl_fig = _plot_pnl(positions, spots)
            result["pnl_chart"] = _fig_to_base64(pnl_fig)
        except Exception as e:
            logger.warning("PnL chart failed: %s", e)
            result["pnl_chart"] = None

        # Theta decay
        try:
            theta_fig = _plot_theta_decay(greeks_positions, spot)
            result["theta_decay_chart"] = _fig_to_base64(theta_fig)
        except Exception as e:
            logger.warning("Theta decay chart failed: %s", e)
            result["theta_decay_chart"] = None

        # Risk breakdown
        result["risk_breakdown"] = _risk_breakdown(positions, spots, totals)

        # Breakevens
        result["breakevens"] = _find_breakevens(greeks_positions, spot)

        # Position sizing
        if account_size:
            result["position_sizing"] = _position_sizing(
                greeks_positions, spot, float(account_size), float(max_risk_pct)
            )

        # VaR
        result["portfolio_var_1d"] = _calc_var(positions, spots, totals)

        return result

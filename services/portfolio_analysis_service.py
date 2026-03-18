"""
Portfolio Analysis Service — Module 3

Coordinates Greeks, PnL, theta decay, risk breakdown, and VaR
for a multi-leg option portfolio.
"""

import io
import base64
import logging

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import norm

from core.options_greeks import portfolio_greeks_table, theta_decay_path

logger = logging.getLogger(__name__)


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    result = base64.b64encode(buf.getvalue()).decode()
    plt.close(fig)
    return result


class PortfolioAnalysisService:

    @staticmethod
    def run(positions: list, account_size=None, max_risk_pct=2.0) -> dict:
        result = {"status": "ok", "warnings": []}

        spots = PortfolioAnalysisService._get_spots(positions)
        main_ticker = positions[0]['ticker']
        spot = spots.get(main_ticker, 100)

        # Build position list for greeks engine
        greeks_positions = []
        for pos in positions:
            greeks_positions.append({
                "type": pos["option_type"],
                "strike": pos["strike"],
                "dte": pos.get("dte", 30),
                "iv": pos.get("iv", 0.25),
                "qty": pos["quantity"],
                "premium": pos["price"],
            })

        # Greeks
        totals, detail_df = portfolio_greeks_table(greeks_positions, spot, r=0.05)
        result["greeks_summary"] = {k: round(v, 4) for k, v in totals.items()}
        result["greeks_detail"] = detail_df.to_dict(orient='records')

        # PnL chart
        try:
            pnl_fig = PortfolioAnalysisService._plot_pnl(positions, spots)
            result["pnl_chart"] = _fig_to_base64(pnl_fig)
        except Exception as e:
            logger.warning(f"PnL chart failed: {e}")
            result["pnl_chart"] = None

        # Theta decay
        try:
            theta_fig = PortfolioAnalysisService._plot_theta_decay(greeks_positions, spot)
            result["theta_decay_chart"] = _fig_to_base64(theta_fig)
        except Exception as e:
            logger.warning(f"Theta decay chart failed: {e}")
            result["theta_decay_chart"] = None

        # Risk breakdown
        result["risk_breakdown"] = PortfolioAnalysisService._risk_breakdown(
            positions, spots, totals
        )

        # Breakevens
        result["breakevens"] = PortfolioAnalysisService._find_breakevens(
            greeks_positions, spot
        )

        # Position sizing
        if account_size:
            result["position_sizing"] = PortfolioAnalysisService._position_sizing(
                greeks_positions, spot, float(account_size), float(max_risk_pct)
            )

        # VaR
        result["portfolio_var_1d"] = PortfolioAnalysisService._calc_var(
            positions, spots, totals
        )

        return result

    @staticmethod
    def _get_spots(positions: list) -> dict:
        tickers = list({p['ticker'] for p in positions})
        spots = {}
        try:
            import yfinance as yf
            for t in tickers:
                tk = yf.Ticker(t)
                fi = tk.fast_info
                price = getattr(fi, 'last_price', None) or getattr(fi, 'regularMarketPrice', None)
                if price:
                    spots[t] = float(price)
        except Exception as e:
            logger.warning(f"_get_spots error: {e}")
        return spots

    @staticmethod
    def _plot_pnl(positions, spots):
        """Plot payoff diagram at expiration."""
        main_ticker = positions[0]['ticker']
        spot = spots.get(main_ticker, 100)

        # Price range
        strikes = [p['strike'] for p in positions]
        lo = min(min(strikes), spot) * 0.85
        hi = max(max(strikes), spot) * 1.15
        prices = np.linspace(lo, hi, 500)

        total_pnl = np.zeros_like(prices)
        for pos in positions:
            is_call = pos['option_type'] in ('LC', 'SC')
            is_long = pos['option_type'] in ('LC', 'LP')
            sign = 1 if is_long else -1
            K = pos['strike']
            premium = pos['price']
            qty = pos['quantity']

            if is_call:
                intrinsic = np.maximum(prices - K, 0)
            else:
                intrinsic = np.maximum(K - prices, 0)

            leg_pnl = (intrinsic - premium) * sign * qty * 100
            total_pnl += leg_pnl

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(prices, total_pnl, color='#3b82f6', linewidth=2)
        ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
        ax.axvline(spot, color='#f59e0b', linewidth=1.2, linestyle=':', label=f'Spot {spot:.2f}')
        ax.fill_between(prices, total_pnl, 0,
                        where=total_pnl >= 0, alpha=0.15, color='green')
        ax.fill_between(prices, total_pnl, 0,
                        where=total_pnl < 0, alpha=0.15, color='red')
        ax.set_xlabel('Underlying Price')
        ax.set_ylabel('P&L ($)')
        ax.set_title('Portfolio P&L at Expiration')
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig

    @staticmethod
    def _plot_theta_decay(greeks_positions, spot):
        days, total_theta = theta_decay_path(greeks_positions, spot, r=0.05)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(days, total_theta, color='#ef4444', linewidth=1.8)
        ax.axhline(0, color='grey', linewidth=0.8, linestyle='--')
        ax.set_xlabel('Days from Now')
        ax.set_ylabel('Portfolio Theta ($/day)')
        ax.set_title('Theta Decay Path')
        ax.grid(alpha=0.3)
        fig.tight_layout()
        return fig

    @staticmethod
    def _risk_breakdown(positions, spots, totals):
        by_ticker = {}
        by_side = {"long": 0, "short": 0}
        for pos in positions:
            t = pos['ticker']
            side = pos.get('side', 'long')
            qty = pos['quantity']
            if t not in by_ticker:
                by_ticker[t] = {"delta": 0, "count": 0}
            by_ticker[t]["count"] += qty
            if side == 'long':
                by_side["long"] += qty
            else:
                by_side["short"] += qty
        return {"by_ticker": by_ticker, "by_side": by_side}

    @staticmethod
    def _find_breakevens(greeks_positions, spot):
        """Approximate breakevens from PnL curve."""
        lo = spot * 0.5
        hi = spot * 1.5
        prices = np.linspace(lo, hi, 2000)
        total_pnl = np.zeros_like(prices)

        for pos in greeks_positions:
            is_call = pos['type'] in ('LC', 'SC')
            is_long = pos['type'] in ('LC', 'LP')
            sign = 1 if is_long else -1
            K = pos['strike']
            premium = pos['premium']
            qty = pos['qty']
            if is_call:
                intrinsic = np.maximum(prices - K, 0)
            else:
                intrinsic = np.maximum(K - prices, 0)
            total_pnl += (intrinsic - premium) * sign * qty * 100

        # Find zero crossings
        breakevens = []
        for i in range(len(total_pnl) - 1):
            if total_pnl[i] * total_pnl[i + 1] < 0:
                # Linear interpolation
                p = prices[i] - total_pnl[i] * (prices[i + 1] - prices[i]) / (total_pnl[i + 1] - total_pnl[i])
                breakevens.append(round(float(p), 2))
        return breakevens

    @staticmethod
    def _position_sizing(greeks_positions, spot, account_size, max_risk_pct):
        """Compute position sizing recommendation."""
        lo = spot * 0.5
        hi = spot * 1.5
        prices = np.linspace(lo, hi, 2000)
        total_pnl = np.zeros_like(prices)

        for pos in greeks_positions:
            is_call = pos['type'] in ('LC', 'SC')
            is_long = pos['type'] in ('LC', 'LP')
            sign = 1 if is_long else -1
            K = pos['strike']
            premium = pos['premium']
            qty = pos['qty']
            if is_call:
                intrinsic = np.maximum(prices - K, 0)
            else:
                intrinsic = np.maximum(K - prices, 0)
            total_pnl += (intrinsic - premium) * sign * qty * 100

        max_loss = float(np.min(total_pnl))
        if max_loss >= 0:
            return {"max_contracts": None, "note": "No loss scenario detected"}

        max_dollar_risk = account_size * (max_risk_pct / 100)
        max_lots = max(1, int(max_dollar_risk / abs(max_loss)))
        return {
            "max_contracts": max_lots,
            "max_loss_per_lot": round(abs(max_loss), 2),
            "max_dollar_risk": round(max_dollar_risk, 2),
        }

    @staticmethod
    def _calc_var(positions, spots, greeks_totals, confidence=0.95):
        """Delta-approximate 1-day VaR."""
        if not positions:
            return 0.0

        avg_iv = np.mean([p.get('iv', 0.25) for p in positions]) or 0.25
        main_ticker = positions[0]['ticker']
        S = spots.get(main_ticker, 100)
        delta = greeks_totals.get('delta', 0)
        sigma_1d = avg_iv / np.sqrt(252)
        z = norm.ppf(confidence)
        var_1d = abs(delta) * S * sigma_1d * z * 100
        return round(float(var_1d), 2)

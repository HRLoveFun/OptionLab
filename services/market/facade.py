"""Market data service layer for ticker validation and market review.

Context:
- Thin facade over ``services.market_review`` and ``core.market.analyzer``. WHY:
  routes must not import ``core/`` directly (ADR 0001); this module is the
  designated orchestration point even when the wrapping is shallow.
"""

import datetime as dt
import logging

from core.market.data_context import build_data_context
from data_pipeline.yf_client import fetch_spot as _fetch_spot
from services.market_review import market_review, market_review_timeseries
from utils.date_helpers import exclusive_month_end
from utils.ticker_utils import is_valid_ticker_format

logger = logging.getLogger(__name__)


class MarketService:
    """
    Service for market data operations and market review generation.
    - validate_ticker: Check if ticker is valid (data available)
    - generate_market_review: Produce multi-asset review table for dashboard
    """

    @staticmethod
    def validate_ticker(ticker):
        """
        Validate ticker symbol by attempting to fetch data.
        Returns (is_valid: bool, message: str)
        """
        # WHY: Reject obvious junk (XSS payloads, SQL fragments, lowercase, etc.)
        # before hitting the data layer. Otherwise a single call would
        # trigger DataService.manual_update() which writes one NaN row per
        # business day to clean_prices for the bogus ticker.
        if not is_valid_ticker_format(ticker):
            return False, "invalid_ticker_or_no_data_available"
        try:
            ctx = build_data_context(ticker, dt.date.today() - dt.timedelta(days=30), "D")
            is_valid = ctx.is_valid()
            message = "valid_ticker" if is_valid else "invalid_ticker_or_no_data_available"
            return is_valid, message
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False, f"error_validating_ticker: {str(e)}"

    @staticmethod
    def fetch_spot(ticker):
        """Last traded price for *ticker*, or None when unavailable.

        WHY: routes must not reach into ``data_pipeline`` directly. Routing the
        call through here keeps the single yfinance exit point behind the
        service layer, so proxy setup and throttling are never bypassed.
        """
        try:
            return _fetch_spot(ticker)
        except Exception as e:
            logger.warning("fetch_spot failed for %s: %s", ticker, e)
            return None

    @staticmethod
    def market_review_timeseries(ticker, start_date=None):
        """
        Generate market review time-series data for a ticker.
        Returns dict with prices, cum_return, rolling_vol per asset.
        """
        return market_review_timeseries(ticker, start_date)

    @staticmethod
    def generate_market_review(form_data):
        """
        Generate market review results using services.market_review.market_review.
        Returns dict with HTML table for dashboard display.
        """
        results = {}
        try:
            start_d = form_data.get("parsed_start_time")
            end_exclusive = exclusive_month_end(form_data.get("parsed_end_time"))
            review_table = market_review(form_data["ticker"], start_d, end_exclusive)
            results["market_review_table"] = review_table.to_html(
                classes="table table-striped", index=True, escape=False
            )
        except Exception as e:
            logger.error(f"Error generating market review: {e}", exc_info=True)
        return results

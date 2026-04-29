"""Market data service layer for ticker validation and market review."""
import datetime as dt
import logging

from core.market_analyzer import MarketAnalyzer
from core.market_review import market_review
from utils.ticker_utils import is_valid_ticker_format
from utils.utils import exclusive_month_end

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
        # before instantiating MarketAnalyzer. Otherwise a single call would
        # trigger DataService.manual_update() which writes one NaN row per
        # business day to clean_prices for the bogus ticker.
        if not is_valid_ticker_format(ticker):
            return False, "invalid_ticker_or_no_data_available"
        try:
            analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=30), "D", end_date=None)
            is_valid = analyzer.is_data_valid()
            message = "valid_ticker" if is_valid else "invalid_ticker_or_no_data_available"
            return is_valid, message
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False, f"error_validating_ticker: {str(e)}"


    @staticmethod
    def generate_market_review(form_data):
        """
        Generate market review results using core.market_review.market_review.
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

import pandas as pd
import numpy as np
import datetime as dt
import logging
from core.market_analyzer import MarketAnalyzer
from core.market_review import market_review

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
        try:
            analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=30), 'D')
            is_valid = analyzer.is_data_valid()
            message = 'valid_ticker' if is_valid else 'invalid_ticker_or_no_data_available'
            return is_valid, message
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False, f'error_validating_ticker: {str(e)}'
    
    @staticmethod
    def generate_market_review(form_data):
        """
        Generate market review results using core.market_review.market_review.
        Returns dict with HTML table for dashboard display.
        """
        results = {}
        try:
            review_table = market_review(form_data['ticker'])
            results['market_review_table'] = review_table.to_html(classes='table table-striped', index=True, escape=False)
        except Exception as e:
            logger.error(f"Error generating market review: {e}", exc_info=True)
        return results
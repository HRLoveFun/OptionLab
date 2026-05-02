"""High-level analysis service that orchestrates market data analysis and charting."""

import gc
import logging

from core.market.analyzer import MarketAnalyzer
from services.market_service import MarketService
from utils.utils import exclusive_month_end

from ._assessment import _generate_assessment
from ._sizing import calculate_position_size
from ._statistical import _generate_statistical_analysis
from ._summary import generate_summary_analysis

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for coordinating all analysis operations."""

    @staticmethod
    def generate_complete_analysis(form_data):
        """Generate complete analysis including market review, statistical analysis, and assessment."""
        try:
            end_exclusive = exclusive_month_end(form_data.get("parsed_end_time"))

            analyzer = MarketAnalyzer(
                ticker=form_data["ticker"],
                start_date=form_data["parsed_start_time"],
                frequency=form_data["frequency"],
                end_date=end_exclusive,
            )

            if not analyzer.is_data_valid():
                return {"error": f"Failed to download data for {form_data['ticker']}. Please check the ticker symbol."}

            results = {}

            market_review = MarketService.generate_market_review(form_data)
            results.update(market_review)

            results.update(_generate_statistical_analysis(analyzer, form_data))
            gc.collect()

            results.update(_generate_assessment(analyzer, form_data))
            gc.collect()

            return results

        except Exception as e:
            logger.error(f"Error generating complete analysis: {e}", exc_info=True)
            return {"error": f"analysis_failed: {str(e)}"}

    @staticmethod
    def _build_analyzer_or_error(form_data):
        """Helper: build a MarketAnalyzer or return ({"error": …}, None)."""
        end_exclusive = exclusive_month_end(form_data.get("parsed_end_time"))
        analyzer = MarketAnalyzer(
            ticker=form_data["ticker"],
            start_date=form_data["parsed_start_time"],
            frequency=form_data["frequency"],
            end_date=end_exclusive,
        )
        if not analyzer.is_data_valid():
            return (
                {"error": f"Failed to download data for {form_data['ticker']}. Please check the ticker symbol."},
                None,
            )
        return None, analyzer

    @staticmethod
    def generate_market_review_slice(form_data: dict) -> dict:
        """Slice for /render/market_review."""
        try:
            return MarketService.generate_market_review(form_data) or {}
        except Exception as e:
            logger.error("market_review slice failed for %s: %s", form_data.get("ticker"), e, exc_info=True)
            return {"error": f"market_review_failed: {e}"}

    @staticmethod
    def generate_statistical_slice(form_data: dict) -> dict:
        """Slice for /render/statistical."""
        try:
            err, analyzer = AnalysisService._build_analyzer_or_error(form_data)
            if err is not None:
                return err
            try:
                return _generate_statistical_analysis(analyzer, form_data)
            finally:
                gc.collect()
        except Exception as e:
            logger.error("statistical slice failed for %s: %s", form_data.get("ticker"), e, exc_info=True)
            return {"statistical_error": str(e)}

    @staticmethod
    def generate_assessment_slice(form_data: dict) -> dict:
        """Slice for /render/assessment."""
        try:
            err, analyzer = AnalysisService._build_analyzer_or_error(form_data)
            if err is not None:
                return err
            try:
                return _generate_assessment(analyzer, form_data)
            finally:
                gc.collect()
        except Exception as e:
            logger.error("assessment slice failed for %s: %s", form_data.get("ticker"), e, exc_info=True)
            return {"assessment_error": str(e)}

    @staticmethod
    def calculate_position_size(
        account_size: float, max_risk_pct: float, max_loss_per_contract: float, strategy_type: str
    ) -> dict | None:
        return calculate_position_size(account_size, max_risk_pct, max_loss_per_contract, strategy_type)

    @staticmethod
    def generate_summary_analysis(tickers: list, results_by_ticker: dict) -> dict:
        return generate_summary_analysis(tickers, results_by_ticker)

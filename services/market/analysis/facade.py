"""High-level analysis service that orchestrates market data analysis and charting."""

import gc
import logging

from core.market.analyzer import MarketAnalyzer
from services.market.data_context_fetch import fetch_data_context
from services.market.facade import MarketService
from services.options.chain import OptionsChainService
from utils.date_helpers import exclusive_month_end

from .assessment import _generate_assessment
from .statistical import _generate_statistical_analysis

logger = logging.getLogger(__name__)


def _build_analyzer(form_data, end_exclusive) -> MarketAnalyzer:
    """Build the DataContext (services own I/O) and wrap it in a MarketAnalyzer.

    WHY here and not in core: constructing a context reads the DB and may hit
    the provider — see ADR 0001 and the closed `core-purity` row in
    docs/architecture_review.md §2 (batch B4).
    """
    ctx = fetch_data_context(
        form_data["ticker"],
        form_data["parsed_start_time"],
        form_data["frequency"],
        end_exclusive,
    )
    return MarketAnalyzer(ctx)


class AnalysisService:
    """Service for coordinating all analysis operations."""

    @staticmethod
    def generate_complete_analysis(form_data):
        """One-shot orchestration of all slices.

        WHY kept despite having no production caller (streaming dispatch covers
        the same ground per-slice): tests/test_nvda_analysis.py exercises the
        full pipeline through it. Remove together with that test's migration.
        """
        """Generate complete analysis including market review, statistical analysis, and assessment."""
        try:
            end_exclusive = exclusive_month_end(form_data.get("parsed_end_time"))

            analyzer = _build_analyzer(form_data, end_exclusive)

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
            return {"error": "analysis_failed: 分析生成失败，请稍后重试"}

    @staticmethod
    def _build_analyzer_or_error(form_data):
        """Helper: build a MarketAnalyzer or return ({"error": …}, None)."""
        end_exclusive = exclusive_month_end(form_data.get("parsed_end_time"))
        analyzer = _build_analyzer(form_data, end_exclusive)
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
            return {"error": "market_review_failed: Market Review 生成失败，请稍后重试"}

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
            return {"statistical_error": "统计图表生成失败，请稍后重试"}

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
            return {"assessment_error": "评估图表生成失败，请稍后重试"}

    @staticmethod
    def generate_options_chain_slice(form_data: dict) -> dict:
        """Slice for /render/options_chain — no MarketAnalyzer needed."""
        ticker = form_data.get("ticker", "")
        try:
            return OptionsChainService.generate_options_chain_analysis(ticker) or {}
        except Exception as e:
            logger.error("options_chain slice failed for %s: %s", ticker, e, exc_info=True)
            return {"oc_error": "期权链分析生成失败，请稍后重试"}

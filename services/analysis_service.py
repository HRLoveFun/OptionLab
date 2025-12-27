import logging
from utils.utils import DEFAULT_ROLLING_WINDOW, DEFAULT_RISK_THRESHOLD, exclusive_month_end
from core.market_analyzer import MarketAnalyzer
from core.correlation_validator import CorrelationValidator
from .market_service import MarketService

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for coordinating all analysis operations"""
    
    @staticmethod
    def generate_complete_analysis(form_data):
        """Generate complete analysis including market review, statistical analysis, and assessment"""
        try:
            # 参数命名与前端表单字段保持一致
            # Convert user end month (YYYY-MM) to an exclusive end date (first day of next month)
            end_exclusive = exclusive_month_end(form_data.get('parsed_end_time'))

            analyzer = MarketAnalyzer(
                ticker=form_data['ticker'],
                start_date=form_data['parsed_start_time'],
                frequency=form_data['frequency'],
                end_date=end_exclusive
            )
            
            if not analyzer.is_data_valid():
                return {'error': f"Failed to download data for {form_data['ticker']}. Please check the ticker symbol."}

            results = {}
            
            # Market review
            market_review = MarketService.generate_market_review(form_data)
            results.update(market_review)
            
            # Statistical analysis
            statistical_analysis = AnalysisService._generate_statistical_analysis(analyzer, form_data)
            results.update(statistical_analysis)
            
            # Market assessment
            assessment = AnalysisService._generate_assessment(analyzer, form_data)
            results.update(assessment)
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating complete analysis: {e}", exc_info=True)
            return {'error': f"analysis_failed: {str(e)}"}
    
    @staticmethod
    def _generate_statistical_analysis(analyzer, form_data):
        """Generate statistical analysis results"""
        results = {}
        try:
            # Extract rolling_window and risk_threshold from form_data (apply defaults if blank/missing)
            rolling_window = form_data.get('rolling_window', DEFAULT_ROLLING_WINDOW)
            risk_threshold = form_data.get('risk_threshold', DEFAULT_RISK_THRESHOLD)
            
            # Generate scatter plot with marginal histograms
            top_plot = analyzer.generate_scatter_plots('Oscillation', rolling_window, risk_threshold)
            if top_plot:
                results['feat_ret_scatter_top_url'] = top_plot

            # Generate High-Low scatter plot
            high_low_scatter = analyzer.generate_high_low_scatter()
            if high_low_scatter:
                results['high_low_scatter_url'] = high_low_scatter

            # Generate Return-Osc_high/low line chart with rolling projections
            return_osc_plot = analyzer.generate_return_osc_high_low_chart(rolling_window, risk_threshold)
            if return_osc_plot:
                results['return_osc_high_low_url'] = return_osc_plot
            
            volatility_plot = analyzer.generate_volatility_dynamics()
            if volatility_plot:
                results['volatility_dynamic_url'] = volatility_plot
            else:
                logger.warning("Volatility dynamics plot generation failed")
            
            # Generate correlation validation charts
            try:
                correlation_validator = CorrelationValidator(
                    ticker=form_data['ticker'],
                    start_date=form_data['parsed_start_time'],
                    frequency=form_data['frequency'],
                    end_date=form_data.get('parsed_end_time')
                )
                
                if correlation_validator.is_data_valid():
                    corr_charts = correlation_validator.generate_all_correlation_charts()
                    results.update(corr_charts)
                else:
                    logger.warning("Correlation validator has no valid data")
            except Exception as e:
                logger.error(f"Error generating correlation charts: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Error generating statistical analysis: {e}", exc_info=True)
        return results
    
    @staticmethod
    def _generate_assessment(analyzer, form_data):
        """Generate assessment results including projections and option analysis"""
        results = {}
        try:
            percentile = form_data['risk_threshold'] / 100.0
            target_bias = form_data['target_bias']
            projection_plot, projection_table = analyzer.generate_oscillation_projection(
                percentile=percentile, 
                target_bias=target_bias
            )
            if projection_plot:
                results['feat_projection_url'] = projection_plot
            if projection_table:
                results['feat_projection_table'] = projection_table
            
            # Option analysis is now optional - only run if valid option data exists
            if form_data.get('option_data') and len(form_data['option_data']) > 0:
                valid_options = [
                    option for option in form_data['option_data']
                    if (option.get('strike') and 
                        option.get('quantity') and 
                        option.get('premium') and
                        float(option['strike']) > 0 and
                        int(option['quantity']) != 0 and
                        float(option['premium']) > 0)
                ]
                if valid_options:
                    try:
                        option_analysis = analyzer.analyze_options(valid_options)
                        if option_analysis:
                            results['plot_url'] = option_analysis
                        else:
                            logger.info("Option analysis returned None - no chart generated")
                    except Exception as e:
                        logger.error(f"Error in option analysis: {e}", exc_info=True)
                else:
                    logger.info("No valid option positions found - skipping option analysis")
            else:
                logger.info("No option data provided - skipping option analysis")
        except Exception as e:
            logger.error(f"Error generating assessment: {e}", exc_info=True)
        return results

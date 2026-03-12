import gc
import logging
import numpy as np
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
            gc.collect()  # reclaim matplotlib buffers after chart batch

            # Market assessment
            assessment = AnalysisService._generate_assessment(analyzer, form_data)
            results.update(assessment)
            gc.collect()
            
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
                    end_date=form_data.get('parsed_end_time'),
                    price_dynamic=analyzer.price_dynamic,  # reuse already-loaded data
                )
                
                if correlation_validator.is_data_valid():
                    corr_charts = correlation_validator.generate_all_correlation_charts()
                    results.update(corr_charts)
                else:
                    logger.warning("Correlation validator has no valid data")
            except Exception as e:
                logger.error(f"Error generating correlation charts: {e}", exc_info=True)
            finally:
                gc.collect()  # release matplotlib pixel buffers promptly
                
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

        # Position sizing (only if account_size and option PnL available)
        try:
            account_size = form_data.get('account_size')
            max_risk_pct = form_data.get('max_risk_pct')
            if account_size is not None and max_risk_pct is not None:
                # Derive max_loss from option analysis
                max_loss_per_contract = None
                if form_data.get('option_data'):
                    current_price = analyzer._get_current_price() if analyzer.is_data_valid() else None
                    if current_price is not None:
                        matrix = analyzer._calculate_option_matrix(current_price, form_data['option_data'])
                        if matrix is not None:
                            max_loss_per_contract = float(matrix['PnL'].min())

                strategy_type = 'credit' if (max_loss_per_contract is not None and max_loss_per_contract < 0) else 'debit'
                ps_result = AnalysisService.calculate_position_size(
                    float(account_size), float(max_risk_pct),
                    max_loss_per_contract, strategy_type
                )
                if ps_result:
                    results['position_sizing'] = ps_result
        except Exception as e:
            logger.warning(f"Position sizing failed: {e}")

        return results

    @staticmethod
    def calculate_position_size(account_size: float, max_risk_pct: float,
                                 max_loss_per_contract: float,
                                 strategy_type: str) -> dict | None:
        """Calculate position size with full boundary handling."""
        if not account_size or account_size <= 0:
            return None

        max_dollar_risk = account_size * (max_risk_pct / 100)

        if max_loss_per_contract is None or np.isinf(max_loss_per_contract):
            return {
                'max_contracts': None,
                'warning': 'This portfolio has unlimited risk (naked short call). Add a hedge leg to calculate position limits.',
                'actual_risk': None,
            }

        abs_loss = abs(float(max_loss_per_contract))

        if abs_loss < 0.01:
            return {
                'max_contracts': None,
                'warning': 'Max loss is near zero (pure premium collection). Position size is determined by margin requirements — consult your broker.',
                'actual_risk': None,
            }

        loss_per_contract = abs_loss * 100  # 1 contract = 100 shares

        max_contracts = max(1, int(max_dollar_risk / loss_per_contract))
        actual_risk = loss_per_contract * max_contracts

        margin_note = (
            "Credit spreads require margin — actual capital usage may exceed premium received. "
            "Check broker margin requirements."
            if strategy_type == 'credit' else None
        )

        return {
            'max_contracts': max_contracts,
            'actual_risk':   round(actual_risk, 2),
            'risk_pct':      round(actual_risk / account_size * 100, 3),
            'margin_note':   margin_note,
            'basis':         f"Account ${account_size:,.0f} × {max_risk_pct}% risk / "
                             f"${loss_per_contract:,.0f} max loss per contract",
        }

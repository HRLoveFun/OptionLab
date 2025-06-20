import logging
from core.market_analyzer import MarketAnalyzer
from .market_service import MarketService

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for coordinating all analysis operations"""
    
    @staticmethod
    def generate_complete_analysis(form_data):
        """Generate complete analysis including market review, statistical analysis, and assessment"""
        try:
            # Initialize market analyzer
            analyzer = MarketAnalyzer(
                ticker=form_data['ticker'],
                start_date=form_data['start_date'],
                frequency=form_data['frequency']
            )
            
            # Check if data was successfully loaded
            if not analyzer.is_data_valid():
                return {'error': f"Failed to download data for {form_data['ticker']}. Please check the ticker symbol."}

            # Generate all analysis components
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
            return {'error': f"Analysis failed: {str(e)}"}
    
    @staticmethod
    def _generate_statistical_analysis(analyzer, form_data):
        """Generate statistical analysis results"""
        results = {}
        
        try:
            # Generate feature vs return scatter plot
            scatter_plot = analyzer.generate_scatter_plot('Oscillation')
            if scatter_plot:
                results['feat_ret_scatter_hist_url'] = scatter_plot
            
            # Generate tail statistics
            tail_stats = analyzer.calculate_tail_statistics('Oscillation')
            if tail_stats is not None:
                results['tail_stats_result'] = tail_stats.to_html(classes='table table-striped')
            
            # Generate tail distribution plot
            tail_plot = analyzer.generate_tail_plot('Oscillation')
            if tail_plot:
                results['tail_plot_url'] = tail_plot
            
            # Generate volatility dynamics plot
            volatility_plot = analyzer.generate_volatility_dynamics()
            if volatility_plot:
                results['volatility_dynamic_url'] = volatility_plot
            
            # Generate gap statistics if applicable
            gap_stats = analyzer.calculate_gap_statistics(form_data['frequency'])
            if gap_stats is not None:
                # Format percentages
                formatted_gap_stats = gap_stats.apply(
                    lambda row: row.apply(
                        lambda x: '{:.2%}'.format(x) if isinstance(x, (int, float)) and row.name not in [
                            "skew", "kurt", "p-value"] else '{:.2f}'.format(x) if isinstance(x, (int, float)) else x
                    ), axis=1
                )
                results['gap_stats_result'] = formatted_gap_stats.to_html(classes='table table-striped')
            
        except Exception as e:
            logger.error(f"Error generating statistical analysis: {e}", exc_info=True)
        
        return results
    
    @staticmethod
    def _generate_assessment(analyzer, form_data):
        """Generate assessment results including projections and option analysis"""
        results = {}
        
        try:
            # Generate oscillation projection with risk threshold and bias
            percentile = form_data['risk_threshold'] / 100.0
            target_bias = form_data['target_bias']
            
            projection_plot = analyzer.generate_oscillation_projection(
                percentile=percentile, 
                target_bias=target_bias
            )
            if projection_plot:
                results['feat_projection_url'] = projection_plot
            
            # Generate option analysis if option data provided
            logger.info(f"Option data received: {form_data['option_data']}")
            
            if form_data['option_data'] and len(form_data['option_data']) > 0:
                # Filter out empty option positions
                valid_options = [
                    option for option in form_data['option_data']
                    if (option.get('strike') and 
                        option.get('quantity') and 
                        option.get('premium') and
                        float(option['strike']) > 0 and
                        int(option['quantity']) != 0 and
                        float(option['premium']) > 0)
                ]
                
                logger.info(f"Valid option positions: {valid_options}")
                
                if valid_options:
                    try:
                        option_analysis = analyzer.analyze_options(valid_options)
                        if option_analysis:
                            results['plot_url'] = option_analysis
                            logger.info("Option P&L chart generated successfully")
                        else:
                            logger.warning("Option analysis returned None")
                    except Exception as e:
                        logger.error(f"Error in option analysis: {e}", exc_info=True)
                else:
                    logger.info("No valid option positions found")
            else:
                logger.info("No option data provided")
            
        except Exception as e:
            logger.error(f"Error generating assessment: {e}", exc_info=True)
        
        return results
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
import base64
import numpy as np
import seaborn as sns
import datetime as dt
from flask import Flask, request, render_template, jsonify
import json
import logging

from marketobserve import PriceDynamic, MarketAnalyzer

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        if request.method == 'POST':
            # Extract form data
            form_data = extract_form_data(request)
            
            # Validate input data
            validation_error = validate_input_data(form_data)
            if validation_error:
                return render_template('index.html', error=validation_error)

            # Initialize market analyzer
            analyzer = MarketAnalyzer(
                ticker=form_data['ticker'],
                start_date=form_data['start_date'],
                end_date=form_data['end_date'],
                frequency=form_data['frequency']
            )
            
            # Check if data was successfully loaded
            if not analyzer.is_data_valid():
                return render_template('index.html', 
                    error=f"Failed to download data for {form_data['ticker']}. Please check the ticker symbol.")

            # Generate analysis results
            analysis_results = generate_analysis(analyzer, form_data)
            
            # Generate assessment results
            assessment_results = generate_assessment(analyzer, form_data)
            
            # Combine all results
            template_data = {
                **form_data,
                **analysis_results,
                **assessment_results
            }
            
            return render_template('index.html', **template_data)

        return render_template('index.html')

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return render_template('index.html', 
            error=f"An unexpected error occurred: {str(e)}. Please try again.")

def extract_form_data(request):
    """Extract and process form data from request"""
    ticker = request.form.get('ticker', '').upper()
    frequency = request.form.get('frequency', 'W')
    
    # Parse start date
    start_date_str = request.form.get('start_date', '')
    try:
        start_date = dt.datetime.strptime(start_date_str, '%Y%m%d').date()
    except ValueError:
        start_date = None
    
    # Parse end date (default to today if empty)
    end_date_str = request.form.get('end_date', '')
    try:
        if end_date_str:
            end_date = dt.datetime.strptime(end_date_str, '%Y%m%d').date()
        else:
            end_date = dt.date.today()
    except ValueError:
        end_date = dt.date.today()
    
    # Parse risk threshold and side bias
    risk_threshold = int(request.form.get('risk_threshold', 90))
    side_bias = request.form.get('side_bias', 'Natural')
    
    # Convert side bias to target_bias value
    target_bias = None if side_bias == 'Natural' else 0
    
    # Parse option positions
    option_data = []
    option_position_str = request.form.get('option_position', '')
    if option_position_str:
        try:
            option_rows = json.loads(option_position_str)
            for row in option_rows:
                option_data.append({
                    'option_type': row['option_type'],
                    'strike': float(row['strike']),
                    'quantity': int(row['quantity']),
                    'premium': float(row['premium'])
                })
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error parsing option data: {e}")
    
    return {
        'ticker': ticker,
        'frequency': frequency,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'risk_threshold': risk_threshold,
        'side_bias': side_bias,
        'target_bias': target_bias,
        'option_data': option_data
    }

def validate_input_data(form_data):
    """Validate input data and return error message if invalid"""
    if not form_data['ticker']:
        return "Please enter a ticker symbol."
    
    if not form_data['start_date']:
        return f"Invalid start date format: {form_data['start_date_str']}. Please use YYYYMMDD."
    
    if form_data['frequency'] not in ['D', 'W', 'ME', 'QE']:
        return f"Invalid frequency selected: {form_data['frequency']}"
    
    if not (0 <= form_data['risk_threshold'] <= 100):
        return "Risk threshold must be between 0 and 100."
    
    if form_data['side_bias'] not in ['Natural', 'Neutral']:
        return f"Invalid side bias selected: {form_data['side_bias']}"
    
    return None

def generate_analysis(analyzer, form_data):
    """Generate analysis results including statistics and plots"""
    results = {}
    
    try:
        # Generate market statistics
        market_stats = analyzer.generate_market_statistics()
        if market_stats is not None:
            results['market_stats'] = market_stats.to_html(classes='table table-striped')
        
        # Generate volatility dynamics plot
        volatility_plot = analyzer.generate_volatility_dynamics(form_data['frequency'])
        if volatility_plot:
            results['volatility_dynamic_url'] = volatility_plot
        
        # Generate enhanced feature vs return scatter plot
        scatter_plot = analyzer.generate_enhanced_scatter_plot('Oscillation')
        if scatter_plot:
            results['feat_ret_scatter_hist_url'] = scatter_plot
        
        # Generate tail statistics
        tail_stats = analyzer.calculate_tail_statistics('Oscillation')
        if tail_stats is not None:
            results['tail_stats_result'] = tail_stats.to_html(classes='table table-striped')
        
        # Generate enhanced tail distribution plot
        tail_plot = analyzer.generate_enhanced_tail_plot('Oscillation')
        if tail_plot:
            results['tail_plot_url'] = tail_plot
        
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
        logger.error(f"Error generating analysis: {e}", exc_info=True)
    
    return results

def generate_assessment(analyzer, form_data):
    """Generate assessment results including projections and option analysis"""
    results = {}
    
    try:
        # Generate enhanced oscillation projection
        percentile = form_data['risk_threshold'] / 100.0
        target_bias = form_data['target_bias']
        
        projection_plot = analyzer.generate_enhanced_oscillation_projection(
            percentile=percentile, 
            target_bias=target_bias
        )
        if projection_plot:
            results['feat_projection_url'] = projection_plot
        
        # Generate strategy analysis if option data provided
        if form_data['option_data']:
            strategy_analysis = analyzer.analyze_strategy(form_data['option_data'])
            if strategy_analysis:
                results['strategy_pnl_url'] = strategy_analysis['pnl_chart']
                results['price_probability_url'] = strategy_analysis['probability_chart']
                results['kelly_analysis'] = strategy_analysis['kelly_analysis'].to_html(classes='table table-striped')
        
    except Exception as e:
        logger.error(f"Error generating assessment: {e}", exc_info=True)
    
    return results

@app.route('/api/validate_ticker', methods=['POST'])
def validate_ticker():
    """API endpoint to validate ticker symbol"""
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({'valid': False, 'message': 'Please enter a ticker symbol'})
        
        # Quick validation by trying to fetch recent data
        analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=30), dt.date.today(), 'D')
        
        return jsonify({
            'valid': analyzer.is_data_valid(),
            'message': 'Valid ticker' if analyzer.is_data_valid() else 'Invalid ticker or no data available'
        })
    
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Error validating ticker: {str(e)}'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
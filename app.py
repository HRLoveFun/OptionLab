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
    feature = request.form.get('feature', 'Oscillation')
    frequency = request.form.get('frequency', 'W')
    periods = request.form.getlist('period') or [12, 36, 60, "ALL"]
    
    # Parse start time
    start_time_str = request.form.get('start_time', '')
    try:
        start_date = dt.datetime.strptime(start_time_str, '%Y%m').date()
    except ValueError:
        start_date = None
    
    # Parse option positions
    option_data = []
    option_position_str = request.form.get('option_position', '')
    if option_position_str:
        try:
            option_rows = json.loads(option_position_str)
            for row in option_rows:
                option_data.append({
                    'option_type': row['optionType'],
                    'strike': float(row['strike']),
                    'quantity': int(row['quantity']),
                    'premium': float(row['premium'])
                })
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error parsing option data: {e}")
    
    return {
        'ticker': ticker,
        'feature': feature,
        'frequency': frequency,
        'periods': periods,
        'start_date': start_date,
        'start_time_str': start_time_str,
        'option_data': option_data
    }

def validate_input_data(form_data):
    """Validate input data and return error message if invalid"""
    if not form_data['ticker']:
        return "Please enter a ticker symbol."
    
    if not form_data['start_date']:
        return f"Invalid start time format: {form_data['start_time_str']}. Please use YYYYMM."
    
    if form_data['feature'] not in ['Oscillation']:
        return f"Invalid feature selected: {form_data['feature']}"
    
    if form_data['frequency'] not in ['D', 'W', 'ME', 'QE']:
        return f"Invalid frequency selected: {form_data['frequency']}"
    
    return None

def generate_analysis(analyzer, form_data):
    """Generate analysis results including statistics and plots"""
    results = {}
    
    try:
        # Generate feature vs return scatter plot
        scatter_plot = analyzer.generate_scatter_plot(form_data['feature'])
        if scatter_plot:
            results['feat_ret_scatter_hist_url'] = scatter_plot
        
        # Generate tail statistics
        tail_stats = analyzer.calculate_tail_statistics(form_data['feature'])
        if tail_stats is not None:
            results['tail_stats_result'] = tail_stats.to_html(classes='table table-striped')
        
        # Generate tail distribution plot
        tail_plot = analyzer.generate_tail_plot(form_data['feature'])
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
        # Generate feature projection
        if form_data['feature'] == 'Oscillation':
            projection_plot = analyzer.generate_oscillation_projection()
            if projection_plot:
                results['feat_projection_url'] = projection_plot
        
        # Generate option analysis if option data provided
        if form_data['option_data']:
            option_analysis = analyzer.analyze_options(form_data['option_data'])
            if option_analysis:
                results['plot_url'] = option_analysis
        
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
        analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=30), 'D')
        
        return jsonify({
            'valid': analyzer.is_data_valid(),
            'message': 'Valid ticker' if analyzer.is_data_valid() else 'Invalid ticker or no data available'
        })
    
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Error validating ticker: {str(e)}'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
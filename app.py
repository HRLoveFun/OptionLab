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

            # Generate market review results
            market_review_results = generate_market_review(form_data)
            
            # Generate analysis results
            analysis_results = generate_analysis(analyzer, form_data)
            
            # Generate assessment results
            assessment_results = generate_assessment(analyzer, form_data)
            
            # Combine all results
            template_data = {
                **form_data,
                **market_review_results,
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
    periods = request.form.getlist('period') or [12, 36, 60, "ALL"]
    
    # Parse start time
    start_time_str = request.form.get('start_time', '')
    try:
        start_date = dt.datetime.strptime(start_time_str, '%Y%m').date()
    except ValueError:
        start_date = None
    
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
        'periods': periods,
        'start_date': start_date,
        'start_time_str': start_time_str,
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
        return f"Invalid start time format: {form_data['start_time_str']}. Please use YYYYMM."
    
    if form_data['frequency'] not in ['D', 'W', 'ME', 'QE']:
        return f"Invalid frequency selected: {form_data['frequency']}"
    
    if not (0 <= form_data['risk_threshold'] <= 100):
        return "Risk threshold must be between 0 and 100."
    
    if form_data['side_bias'] not in ['Natural', 'Neutral']:
        return f"Invalid side bias selected: {form_data['side_bias']}"
    
    return None

def generate_market_review(form_data):
    """Generate market review results including market overview table and correlation matrix"""
    results = {}
    
    try:
        # Define market review tickers
        market_tickers = [
            form_data['ticker'],  # User's ticker
            'DX-Y.NYB',  # US Dollar Index
            '^TNX',      # 10-Year Treasury
            '^GSPC',     # S&P 500
            'GC=F',      # Gold
            '000300.SS', # CSI 300
            '^STOXX',    # STOXX Europe 600
            '^HSI',      # Hang Seng
            '^N225'      # Nikkei 225
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tickers = []
        for ticker in market_tickers:
            if ticker not in seen:
                unique_tickers.append(ticker)
                seen.add(ticker)
        
        # Calculate market review data
        market_data = []
        correlation_data = {}
        
        for ticker in unique_tickers:
            try:
                # Get recent extreme change data
                extreme_data = calculate_recent_extreme_change(ticker)
                if extreme_data is not None:
                    market_data.append(extreme_data)
                    
                    # Store price data for correlation calculation
                    analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=365), 'D')
                    if analyzer.is_data_valid():
                        correlation_data[ticker] = analyzer.price_dynamic._data['Close'].pct_change().dropna()
                
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker}: {e}")
                continue
        
        # Create market overview table
        if market_data:
            market_df = pd.DataFrame(market_data)
            
            # Format the dataframe for display
            formatted_df = market_df.copy()
            
            # Format percentage columns
            percentage_cols = ['1M_Return', '1Q_Return', 'YTD_Return', 'ETD_Return', 
                             '1M_Volatility', '1Q_Volatility', 'YTD_Volatility', 'ETD_Volatility']
            
            for col in percentage_cols:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")
            
            # Format last close price
            if 'Last_Close' in formatted_df.columns:
                formatted_df['Last_Close'] = formatted_df['Last_Close'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            
            results['market_overview_table'] = formatted_df.to_html(
                classes='table table-striped',
                index=False,
                escape=False
            )
        
        # Generate correlation matrix chart
        if len(correlation_data) >= 2:
            correlation_chart = generate_correlation_matrix(correlation_data)
            if correlation_chart:
                results['correlation_matrix_url'] = correlation_chart
        
    except Exception as e:
        logger.error(f"Error generating market review: {e}", exc_info=True)
    
    return results

def calculate_recent_extreme_change(ticker):
    """Calculate recent extreme changes for a ticker"""
    try:
        # Create analyzer for the ticker
        analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=365), 'D')
        
        if not analyzer.is_data_valid():
            return None
        
        data = analyzer.price_dynamic._data
        current_price = data['Close'].iloc[-1]
        
        # Calculate returns for different periods
        returns_data = {}
        volatility_data = {}
        
        # Define periods
        periods = {
            '1M': 22,    # ~1 month
            '1Q': 66,    # ~1 quarter
            'YTD': None, # Year to date
            'ETD': None  # Entire time period
        }
        
        for period_name, days in periods.items():
            try:
                if period_name == 'YTD':
                    # Year to date calculation
                    year_start = dt.date(dt.date.today().year, 1, 1)
                    ytd_data = data[data.index.date >= year_start]
                    if len(ytd_data) > 1:
                        period_return = (ytd_data['Close'].iloc[-1] / ytd_data['Close'].iloc[0]) - 1
                        period_volatility = ytd_data['Close'].pct_change().std() * np.sqrt(252)
                    else:
                        period_return = np.nan
                        period_volatility = np.nan
                elif period_name == 'ETD':
                    # Entire time period
                    if len(data) > 1:
                        period_return = (data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1
                        period_volatility = data['Close'].pct_change().std() * np.sqrt(252)
                    else:
                        period_return = np.nan
                        period_volatility = np.nan
                else:
                    # Fixed period calculation
                    if len(data) > days:
                        period_data = data.iloc[-days:]
                        period_return = (period_data['Close'].iloc[-1] / period_data['Close'].iloc[0]) - 1
                        period_volatility = period_data['Close'].pct_change().std() * np.sqrt(252)
                    else:
                        period_return = np.nan
                        period_volatility = np.nan
                
                returns_data[f'{period_name}_Return'] = period_return
                volatility_data[f'{period_name}_Volatility'] = period_volatility
                
            except Exception as e:
                logger.warning(f"Error calculating {period_name} for {ticker}: {e}")
                returns_data[f'{period_name}_Return'] = np.nan
                volatility_data[f'{period_name}_Volatility'] = np.nan
        
        # Combine all data
        result = {
            'Ticker': ticker,
            'Last_Close': current_price,
            **returns_data,
            **volatility_data
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error in calculate_recent_extreme_change for {ticker}: {e}")
        return None

def generate_correlation_matrix(correlation_data):
    """Generate correlation matrix chart"""
    try:
        # Calculate correlations for different periods
        periods = {
            '1M': 22,
            '1Q': 66,
            'YTD': None,
            'ETD': None
        }
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Market Correlation Matrix', fontsize=16, fontweight='bold')
        
        axes = axes.flatten()
        
        for idx, (period_name, days) in enumerate(periods.items()):
            try:
                # Prepare data for correlation calculation
                period_data = {}
                
                for ticker, returns in correlation_data.items():
                    if period_name == 'YTD':
                        # Year to date
                        year_start = dt.date(dt.date.today().year, 1, 1)
                        period_returns = returns[returns.index.date >= year_start]
                    elif period_name == 'ETD':
                        # Entire time period
                        period_returns = returns
                    else:
                        # Fixed period
                        period_returns = returns.iloc[-days:] if len(returns) > days else returns
                    
                    if len(period_returns) > 10:  # Minimum data points
                        period_data[ticker] = period_returns
                
                if len(period_data) >= 2:
                    # Create correlation matrix
                    corr_df = pd.DataFrame(period_data).corr()
                    
                    # Plot heatmap
                    sns.heatmap(
                        corr_df,
                        annot=True,
                        cmap='RdYlBu_r',
                        center=0,
                        fmt='.2f',
                        square=True,
                        ax=axes[idx],
                        cbar_kws={'shrink': 0.8}
                    )
                    axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
                    axes[idx].tick_params(axis='x', rotation=45)
                    axes[idx].tick_params(axis='y', rotation=0)
                else:
                    axes[idx].text(0.5, 0.5, f'Insufficient data for {period_name}', 
                                 ha='center', va='center', transform=axes[idx].transAxes)
                    axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
                
            except Exception as e:
                logger.warning(f"Error generating correlation for {period_name}: {e}")
                axes[idx].text(0.5, 0.5, f'Error: {period_name}', 
                             ha='center', va='center', transform=axes[idx].transAxes)
                axes[idx].set_title(f'{period_name} Correlation', fontweight='bold')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        plot_data = buffer.getvalue()
        buffer.close()
        plt.close()
        
        return base64.b64encode(plot_data).decode()
        
    except Exception as e:
        logger.error(f"Error generating correlation matrix: {e}")
        return None

def generate_analysis(analyzer, form_data):
    """Generate analysis results including statistics and plots"""
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
        logger.error(f"Error generating analysis: {e}", exc_info=True)
    
    return results

def generate_assessment(analyzer, form_data):
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

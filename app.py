from flask import Flask, request, render_template, jsonify
import logging
import os
import datetime as dt
from dotenv import load_dotenv
load_dotenv()  # 加载.env文件


from services.form_service import FormService
from services.analysis_service import AnalysisService
from services.market_service import MarketService
from services.validation_service import ValidationService
from services.options_chain_service import OptionsChainService
from data_pipeline.data_service import DataService
from data_pipeline.scheduler import UpdateScheduler
from utils.utils import (
    DEFAULT_TICKER, DEFAULT_FREQUENCY, DEFAULT_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW, DEFAULT_SIDE_BIAS
)

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DB
DataService.initialize()
_scheduler = None
try:
    auto_update = os.environ.get("AUTO_UPDATE_TICKERS", "").strip()
    if auto_update:
        tickers = [t.strip().upper() for t in auto_update.split(",") if t.strip()]
        if tickers:
            _scheduler = UpdateScheduler()
            _scheduler.start_daily_update(tickers)
            _scheduler.start_monthly_correlation_update(tickers)
            logger.info(f"Auto-update scheduler started for: {tickers}")
            logger.info(f"Monthly correlation update scheduler started for: {tickers}")
except Exception as e:
    logger.warning(f"Scheduler init failed: {e}")

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Main dashboard route.
    GET: Render dashboard form.
    POST: Extracts form data, validates, runs analysis, returns results or error.
    """
    try:
        if request.method == 'POST':
            # Extract and validate form data
            form_data = FormService.extract_form_data(request)
            validation_error = ValidationService.validate_input_data(form_data)
            
            if validation_error:
                return render_template('index.html', error=validation_error)

            # Generate analysis results
            analysis_results = AnalysisService.generate_complete_analysis(form_data)
            
            if 'error' in analysis_results:
                return render_template('index.html', error=analysis_results['error'])
            
            # Combine form data with results
            template_data = {**form_data, **analysis_results}

            # Options chain analysis (non-blocking)
            try:
                oc_results = OptionsChainService.generate_options_chain_analysis(
                    form_data['ticker']
                )
                template_data.update(oc_results)
            except Exception as e:
                logger.warning(f"Options chain analysis failed: {e}")

            return render_template('index.html', **template_data)

        return render_template('index.html',
            ticker=DEFAULT_TICKER,
            start_time=(
                lambda today: f"{today.year - 5}-{today.month:02d}"
            )(dt.date.today()),
            end_time='',
            frequency=DEFAULT_FREQUENCY,
            risk_threshold=DEFAULT_RISK_THRESHOLD,
            rolling_window=DEFAULT_ROLLING_WINDOW,
            side_bias=DEFAULT_SIDE_BIAS,
        )

    except Exception as e:
        logger.error(f"Unexpected error in main route: {e}", exc_info=True)
        return render_template('index.html', 
            error=f"An unexpected error occurred: {str(e)}. Please try again.")

@app.route('/api/option_chain', methods=['GET'])
def option_chain():
    """
    API endpoint to fetch live option chain data from Yahoo Finance.
    Query params: ticker (required)
    Response: { expirations: [...], chain: { date: { calls: [...], puts: [...] } } }
    """
    import yfinance as yf
    import math

    ticker_sym = request.args.get('ticker', '').strip().upper()
    if not ticker_sym:
        return jsonify({'error': 'ticker is required'}), 400

    def clean(v):
        """Convert NaN / inf to None for JSON serialisation."""
        try:
            if v is None:
                return None
            fv = float(v)
            return None if (math.isnan(fv) or math.isinf(fv)) else round(fv, 4)
        except Exception:
            return str(v) if v is not None else None

    try:
        tkr = yf.Ticker(ticker_sym)
        expirations = list(tkr.options)
        if not expirations:
            return jsonify({'error': f'No options available for {ticker_sym}'}), 404

        CALL_COLS = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest',
                     'impliedVolatility', 'inTheMoney']
        PUT_COLS  = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest',
                     'impliedVolatility', 'inTheMoney']

        chain_data = {}
        for exp in expirations:
            opt = tkr.option_chain(exp)
            calls_df = opt.calls[CALL_COLS].sort_values('strike') if hasattr(opt, 'calls') else None
            puts_df  = opt.puts[PUT_COLS].sort_values('strike')  if hasattr(opt, 'puts')  else None

            def df_to_records(df):
                if df is None or df.empty:
                    return []
                rows = []
                for _, r in df.iterrows():
                    rows.append({
                        'strike':        clean(r.get('strike')),
                        'lastPrice':     clean(r.get('lastPrice')),
                        'bid':           clean(r.get('bid')),
                        'ask':           clean(r.get('ask')),
                        'volume':        clean(r.get('volume')),
                        'openInterest':  clean(r.get('openInterest')),
                        'iv':            clean((r.get('impliedVolatility') or 0) * 100),
                        'itm':           bool(r.get('inTheMoney', False)),
                    })
                return rows

            chain_data[exp] = {
                'calls': df_to_records(calls_df),
                'puts':  df_to_records(puts_df),
            }

        # Current price for ATM highlighting
        try:
            fi = tkr.fast_info
            price = getattr(fi, 'last_price', None) or getattr(fi, 'regularMarketPrice', None)
            spot = clean(price)
        except Exception:
            spot = None

        return jsonify({'expirations': expirations, 'chain': chain_data, 'spot': spot})

    except Exception as e:
        logger.error(f"Error fetching option chain for {ticker_sym}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate_ticker', methods=['POST'])
def validate_ticker():
    """
    API endpoint to validate ticker symbol.
    Request: JSON {"ticker": "AAPL"}
    Response: {"valid": true/false, "message": "..."}
    """
    try:
        data = request.get_json()
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({'valid': False, 'message': 'Please enter a ticker symbol'})
        
        # Validate ticker using market service
        is_valid, message = MarketService.validate_ticker(ticker)
        
        return jsonify({
            'valid': is_valid,
            'message': message
        })
    
    except Exception as e:
        logger.error(f"Error validating ticker: {e}")
        return jsonify({'valid': False, 'message': f'Error validating ticker: {str(e)}'})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

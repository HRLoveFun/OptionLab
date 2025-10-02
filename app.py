from flask import Flask, request, render_template, jsonify
import logging
import os
from dotenv import load_dotenv
load_dotenv()  # 加载.env文件


from services.form_service import FormService
from services.analysis_service import AnalysisService
from services.market_service import MarketService
from services.validation_service import ValidationService
from data_pipeline.data_service import DataService
from data_pipeline.scheduler import UpdateScheduler

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
            logger.info(f"Auto-update scheduler started for: {tickers}")
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
            return render_template('index.html', **template_data)

        return render_template('index.html')

    except Exception as e:
        logger.error(f"Unexpected error in main route: {e}", exc_info=True)
        return render_template('index.html', 
            error=f"An unexpected error occurred: {str(e)}. Please try again.")

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
    # app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False) 

# application = app

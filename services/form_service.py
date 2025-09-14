import json
import datetime as dt
import logging

logger = logging.getLogger(__name__)

class FormService:
    """
    Service for handling form data extraction and processing from Flask request.
    - extract_form_data: Extracts and parses all dashboard form fields.
    - parse_option_data: Parses option positions from JSON string.
    """
    @staticmethod
    def extract_form_data(request):
        """
        Extract and process form data from request.
        Args:
            request (flask.Request): Incoming request
        Returns:
            dict: Parsed form data (ticker, frequency, periods, start_time, etc.)
        """
        ticker = request.form.get('ticker', '').upper()
        frequency = request.form.get('frequency', 'W')
        periods = request.form.getlist('period') or [12, 36, 60, "ALL"]
        start_time = request.form.get('start_time', '')
        try:
            parsed_start_time = dt.datetime.strptime(start_time, '%Y%m').date()
        except ValueError:
            parsed_start_time = None
        risk_threshold = int(request.form.get('risk_threshold', 90))
        side_bias = request.form.get('side_bias', 'Natural')
        target_bias = None if side_bias == 'Natural' else 0
        option_data = FormService.parse_option_data(request)
        return {
            'ticker': ticker,
            'frequency': frequency,
            'periods': periods,
            'start_time': start_time,
            'parsed_start_time': parsed_start_time,
            'risk_threshold': risk_threshold,
            'side_bias': side_bias,
            'target_bias': target_bias,
            'option_data': option_data
        }
    
    @staticmethod
    def parse_option_data(request):
        """
        Parse option positions from form data (JSON string in 'option_position').
        Returns list of dicts with option_type, strike, quantity, premium.
        """
        option_data = []
        option_position_str = request.form.get('option_position', '')
        if option_position_str:
            try:
                option_rows = json.loads(option_position_str)
                for row in option_rows:
                    if (row.get('option_type') and 
                        row.get('strike') and 
                        row.get('quantity') and 
                        row.get('premium')):
                        try:
                            option_entry = {
                                'option_type': row['option_type'],
                                'strike': float(row['strike']),
                                'quantity': int(row['quantity']),
                                'premium': float(row['premium'])
                            }
                            if (option_entry['strike'] > 0 and 
                                option_entry['quantity'] != 0 and 
                                option_entry['premium'] > 0):
                                option_data.append(option_entry)
                            else:
                                logger.warning(f"Skipped invalid option values: {option_entry}")
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error converting option values: {row}, error: {e}")
                    else:
                        logger.warning(f"Skipped incomplete option row: {row}")
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                logger.error(f"Error parsing option data: {e}")
        return option_data
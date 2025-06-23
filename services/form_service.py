import json
import datetime as dt
import logging

logger = logging.getLogger(__name__)

class FormService:
    """Service for handling form data extraction and processing"""
    
    @staticmethod
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
        option_data = FormService._parse_option_data(request)
        
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
    
    @staticmethod
    def _parse_option_data(request):
        """Parse option positions from form data"""
        option_data = []
        option_position_str = request.form.get('option_position', '')
        
        if option_position_str:
            try:
                option_rows = json.loads(option_position_str)
                
                for row in option_rows:
                    # Validate required fields
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
                            
                            # Only add if all values are valid
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
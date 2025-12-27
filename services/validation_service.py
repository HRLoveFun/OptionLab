class ValidationService:
    """
    Service for validating input data from dashboard form.
    - validate_input_data: Checks ticker, start_time, frequency, risk_threshold, side_bias.
    Returns error message string if invalid, else None.
    """
    
    @staticmethod
    def validate_input_data(form_data):
        """
        Validate input data and return error message if invalid.
        
        Args:
            form_data (dict): Extracted form data
            
        Returns:
            str or None: Error message if invalid, else None
        """
        if not form_data['ticker']:
            return "please_enter_a_ticker_symbol."
        
        if not form_data['parsed_start_time']:
            return f"invalid_start_time_format: {form_data['start_time']}. please_use_yyyymm."
        # end time is optional; if provided, must be valid and >= start
        if form_data.get('end_time'):
            if not form_data.get('parsed_end_time'):
                return f"invalid_end_time_format: {form_data['end_time']}. please_use_yyyymm."
            if form_data['parsed_end_time'] < form_data['parsed_start_time']:
                return "end_time_must_be_on_or_after_start_time."
        
        if form_data['frequency'] not in ['D', 'W', 'ME', 'QE']:
            return f"invalid_frequency_selected: {form_data['frequency']}"
        
        if not (0 <= form_data['risk_threshold'] <= 100):
            return "risk_threshold_must_be_between_0_and_100."
        
        if form_data.get('rolling_window') is not None and form_data['rolling_window'] < 1:
            return "rolling_window_must_be_a_positive_integer."
        
        if form_data['side_bias'] not in ['Natural', 'Neutral']:
            return f"invalid_side_bias_selected: {form_data['side_bias']}"
        
        return None
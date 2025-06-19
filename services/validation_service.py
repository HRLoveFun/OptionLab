class ValidationService:
    """Service for validating input data"""
    
    @staticmethod
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
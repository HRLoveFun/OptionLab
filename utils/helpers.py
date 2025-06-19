"""General utility helper functions"""

import datetime as dt
from typing import List, Any

class DateHelper:
    """Helper functions for date operations"""
    
    @staticmethod
    def parse_date_string(date_str, format_str='%Y%m'):
        """Parse date string to date object"""
        try:
            return dt.datetime.strptime(date_str, format_str).date()
        except ValueError:
            return None
    
    @staticmethod
    def get_year_start():
        """Get the start of current year"""
        return dt.date(dt.date.today().year, 1, 1)
    
    @staticmethod
    def days_ago(days):
        """Get date N days ago"""
        return dt.date.today() - dt.timedelta(days=days)

class ListHelper:
    """Helper functions for list operations"""
    
    @staticmethod
    def remove_duplicates_preserve_order(items: List[Any]) -> List[Any]:
        """Remove duplicates from list while preserving order"""
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result
    
    @staticmethod
    def safe_get(items: List[Any], index: int, default=None):
        """Safely get item from list by index"""
        try:
            return items[index]
        except (IndexError, TypeError):
            return default

class ValidationHelper:
    """Helper functions for validation"""
    
    @staticmethod
    def is_valid_ticker(ticker):
        """Basic ticker validation"""
        if not ticker or not isinstance(ticker, str):
            return False
        return len(ticker.strip()) > 0 and len(ticker.strip()) <= 10
    
    @staticmethod
    def is_valid_percentage(value):
        """Validate percentage value (0-100)"""
        try:
            num_value = float(value)
            return 0 <= num_value <= 100
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_frequency(frequency):
        """Validate frequency value"""
        valid_frequencies = ['D', 'W', 'ME', 'QE']
        return frequency in valid_frequencies
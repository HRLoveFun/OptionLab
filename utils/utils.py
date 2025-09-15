"""Unified utility module for market analysis application"""

DEFAULT_RISK_THRESHOLD = 90
DEFAULT_FREQUENCY = 'W'
DEFAULT_PERIODS = [12, 36, 60, "ALL"]

FREQUENCY_DISPLAY = {
    'D': 'Daily',
    'W': 'Weekly',
    'ME': 'Monthly',
    'QE': 'Quarterly'
}

import datetime as dt
from typing import List, Any

class DateHelper:
    @staticmethod
    def parse_date_string(date_str, format_str='%Y%m'):
        try:
            return dt.datetime.strptime(date_str, format_str).date()
        except ValueError:
            return None

import pandas as pd
import numpy as np

class DataFormatter:
    @staticmethod
    def format_percentage(value, decimal_places=2):
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}%}"

    @staticmethod
    def format_currency(value, decimal_places=2):
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}f}"

    @staticmethod
    def format_number(value, decimal_places=2):
        if pd.isna(value) or not isinstance(value, (int, float)):
            return "N/A"
        return f"{value:.{decimal_places}f}"

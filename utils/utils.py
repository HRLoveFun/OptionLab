"""Unified utility module for market analysis application"""

DEFAULT_RISK_THRESHOLD = 90
DEFAULT_ROLLING_WINDOW = 120
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


def parse_month_str(value: str) -> dt.date | None:
    """Parse a YYYYMM or YYYY-MM string into a date (first of month)."""
    if not value:
        return None
    for fmt in ("%Y%m", "%Y-%m"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def exclusive_month_end(month_date: dt.date | None) -> dt.date | None:
    """Return the first day of the next month for horizon end handling."""
    if month_date is None:
        return None
    year = month_date.year + (1 if month_date.month == 12 else 0)
    month = 1 if month_date.month == 12 else month_date.month + 1
    return dt.date(year, month, 1)

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

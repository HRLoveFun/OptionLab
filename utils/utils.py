"""Unified utility module for market analysis application"""

# ---- constants ----
# Application constants and configuration
DEFAULT_RISK_THRESHOLD = 90
DEFAULT_FREQUENCY = 'W'
DEFAULT_PERIODS = [12, 36, 60, "ALL"]

MARKET_REVIEW_TICKERS = [
    'DX-Y.NYB',  # US Dollar Index
    '^TNX',      # 10-Year Treasury
    '^GSPC',     # S&P 500
    'GC=F',      # Gold
    '000300.SS', # CSI 300
    '^STOXX',    # STOXX Europe 600
    '^HSI',      # Hang Seng
    '^N225'      # Nikkei 225
]

FREQUENCY_DISPLAY = {
    'D': 'Daily',
    'W': 'Weekly',
    'ME': 'Monthly',
    'QE': 'Quarterly'
}

TIME_PERIODS = {
    '1M': 22,    # ~1 month in trading days
    '1Q': 66,    # ~1 quarter in trading days
    'YTD': None, # Year to date
    'ETD': None  # Entire time period
}

CHART_CONFIG = {
    'dpi': 300,
    'format': 'png',
    'bbox_inches': 'tight',
    'correlation_matrix_size': (16, 12),
    'default_figsize': (12, 8)
}

TABLE_CLASSES = 'table table-striped'

OPTION_TYPES = {
    'SC': 'Short Call',
    'SP': 'Short Put',
    'LC': 'Long Call',
    'LP': 'Long Put'
}

# ---- helpers ----
import datetime as dt
from typing import List, Any

class DateHelper:
    @staticmethod
    def parse_date_string(date_str, format_str='%Y%m'):
        try:
            return dt.datetime.strptime(date_str, format_str).date()
        except ValueError:
            return None
    @staticmethod
    def get_year_start():
        return dt.date(dt.date.today().year, 1, 1)
    @staticmethod
    def days_ago(days):
        return dt.date.today() - dt.timedelta(days=days)

class ListHelper:
    @staticmethod
    def remove_duplicates_preserve_order(items: List[Any]) -> List[Any]:
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                result.append(item)
                seen.add(item)
        return result
    @staticmethod
    def safe_get(items: List[Any], index: int, default=None):
        try:
            return items[index]
        except (IndexError, TypeError):
            return default

class ValidationHelper:
    @staticmethod
    def is_valid_ticker(ticker):
        if not ticker or not isinstance(ticker, str):
            return False
        return len(ticker.strip()) > 0 and len(ticker.strip()) <= 10
    @staticmethod
    def is_valid_percentage(value):
        try:
            num_value = float(value)
            return 0 <= num_value <= 100
        except (ValueError, TypeError):
            return False
    @staticmethod
    def is_valid_frequency(frequency):
        valid_frequencies = ['D', 'W', 'ME', 'QE']
        return frequency in valid_frequencies

# ---- formatters ----
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
    @staticmethod
    def format_dataframe_for_display(df, percentage_columns=None, currency_columns=None):
        if df is None or df.empty:
            return None
        formatted_df = df.copy()
        if percentage_columns:
            for col in percentage_columns:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(DataFormatter.format_percentage)
        if currency_columns:
            for col in currency_columns:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(DataFormatter.format_currency)
        return formatted_df
    @staticmethod
    def format_gap_stats(gap_stats):
        if gap_stats is None:
            return None
        return gap_stats.apply(
            lambda row: row.apply(
                lambda x: DataFormatter.format_percentage(x) if isinstance(x, (int, float)) and row.name not in [
                    "skew", "kurt", "p-value"] else DataFormatter.format_number(x) if isinstance(x, (int, float)) else x
            ), axis=1
        )

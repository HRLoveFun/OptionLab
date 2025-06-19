"""Utility functions for data formatting"""

import pandas as pd
import numpy as np

class DataFormatter:
    """Utility class for formatting data for display"""
    
    @staticmethod
    def format_percentage(value, decimal_places=2):
        """Format a decimal value as percentage"""
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}%}"
    
    @staticmethod
    def format_currency(value, decimal_places=2):
        """Format a value as currency"""
        if pd.isna(value):
            return "N/A"
        return f"{value:.{decimal_places}f}"
    
    @staticmethod
    def format_number(value, decimal_places=2):
        """Format a number with specified decimal places"""
        if pd.isna(value) or not isinstance(value, (int, float)):
            return "N/A"
        return f"{value:.{decimal_places}f}"
    
    @staticmethod
    def format_dataframe_for_display(df, percentage_columns=None, currency_columns=None):
        """Format a dataframe for HTML display"""
        if df is None or df.empty:
            return None
        
        formatted_df = df.copy()
        
        # Format percentage columns
        if percentage_columns:
            for col in percentage_columns:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(DataFormatter.format_percentage)
        
        # Format currency columns
        if currency_columns:
            for col in currency_columns:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(DataFormatter.format_currency)
        
        return formatted_df
    
    @staticmethod
    def format_gap_stats(gap_stats):
        """Format gap statistics for display"""
        if gap_stats is None:
            return None
        
        return gap_stats.apply(
            lambda row: row.apply(
                lambda x: DataFormatter.format_percentage(x) if isinstance(x, (int, float)) and row.name not in [
                    "skew", "kurt", "p-value"] else DataFormatter.format_number(x) if isinstance(x, (int, float)) else x
            ), axis=1
        )
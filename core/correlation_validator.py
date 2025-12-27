"""
Correlation Validation Module

This module calculates and visualizes rolling correlations for:
1. Correlation between Consecutive Returns
2. Correlation between Osc_high vs Osc_low 

Charts are generated for 1-year and 5-year rolling windows across different frequencies.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import io
import base64
import logging
import datetime as dt
import os
from pathlib import Path
from typing import Optional, Tuple
from core.price_dynamic import PriceDynamic

logger = logging.getLogger(__name__)



# Plot size constants
PLOT_SIZE_CORRELATION = (14, 6)

# Color constants
COLOR_1Y = '#1f77b4'  # Blue
COLOR_5Y = '#ff7f0e'  # Orange


class CorrelationValidator:
    """Validates market patterns through rolling correlation analysis."""
    
    def __init__(self, ticker: str, start_date: dt.date = dt.date(2016, 12, 1), 
                 frequency: str = 'W', end_date: Optional[dt.date] = None):
        """
        Initialize the correlation validator.
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for output filtering (horizon start)
            frequency: Frequency for analysis ('D', 'W', 'ME', 'QE')
            end_date: End date for output filtering (horizon end, defaults to today)
        """
        self.ticker = ticker
        self.user_start_date = start_date  # Store for output filtering
        self.frequency = frequency
        self.user_end_date = end_date or dt.date.today()  # Store for output filtering
        self._user_provided_end = end_date is not None
        
        # Use PriceDynamic to get full historical data (it now fetches all data)
        self.price_dynamic = PriceDynamic(ticker, start_date, frequency, end_date)
        
        # Build data DataFrame with calculated values from full dataset
        self.data = self._build_data()
        
    def _build_data(self) -> Optional[pd.DataFrame]:
        """Build data DataFrame from FULL underlying dataset (no horizon filtering).

        Computes:
        - log_return from percentage returns based on Close and LastClose
        - osc_high and osc_low from High/Low relative to LastClose
        """
        try:
            if not self.price_dynamic.is_valid():
                logger.warning(f"No valid data for {self.ticker}")
                return None
            
            full_df = getattr(self.price_dynamic, "_data", None)
            if full_df is None or full_df.empty:
                logger.warning("PriceDynamic has no full dataset available")
                return None

            data = pd.DataFrame(index=full_df.index)
            try:
                # Percentage returns then convert to log returns
                ret_pct = ((full_df["Close"] - full_df["LastClose"]) / full_df["LastClose"]) * 100
                data['log_return'] = np.log1p(ret_pct / 100.0)
            except Exception as e:
                logger.warning(f"Failed computing log_return: {e}")
            try:
                data['osc_high'] = (full_df['High'] / full_df['LastClose'] - 1) * 100
            except Exception as e:
                logger.warning(f"Failed computing osc_high: {e}")
            try:
                data['osc_low'] = (full_df['Low'] / full_df['LastClose'] - 1) * 100
            except Exception as e:
                logger.warning(f"Failed computing osc_low: {e}")

            data = data.dropna(how='all')
            return data if not data.empty else None
            
        except Exception as e:
            logger.error(f"Error building data: {e}")
            return None
    
    def is_data_valid(self) -> bool:
        """Check if validator has valid data."""
        return self.data is not None and not self.data.empty
    
    def _apply_horizon(self, series: pd.Series | None) -> pd.Series | None:
        """Apply horizon filtering to output series (same logic as PriceDynamic)."""
        if series is None or series.empty:
            return series
        try:
            start_ts = pd.Timestamp(self.user_start_date)
            # Determine effective end timestamp
            if self._user_provided_end:
                end_ts = pd.Timestamp(self.user_end_date)
            else:
                end_ts = self._compute_effective_end_ts()
            idx = series.index
            # Match timezone if necessary
            if hasattr(idx, 'tz') and idx.tz is not None:
                if start_ts.tz is None:
                    start_ts = start_ts.tz_localize(idx.tz)
                if end_ts.tz is None:
                    end_ts = end_ts.tz_localize(idx.tz)
            # Include the end timestamp in results (inclusive end date)
            return series[(idx >= start_ts) & (idx <= end_ts)]
        except Exception:
            return series
    
    def _compute_effective_end_ts(self) -> pd.Timestamp:
        """Compute effective end timestamp when user didn't provide end date."""
        today = pd.Timestamp(dt.date.today())
        if self.frequency == 'D':
            eff = today
        elif self.frequency == 'W':
            weekday = today.weekday()
            days_to_sunday = (6 - weekday) % 7
            eff = today + pd.Timedelta(days=days_to_sunday)
        elif self.frequency == 'ME':
            eff = today + pd.offsets.MonthEnd(0)
        elif self.frequency == 'QE':
            eff = today + pd.offsets.QuarterEnd(0)
        else:
            eff = today
        return pd.Timestamp(eff)
    
    def calculate_return_autocorrelation(self, window_years: int = 1) -> Optional[pd.Series]:
        """
        Calculate rolling correlation between return and return.shift(1) using the FULL historical dataset.
        Horizon filtering is applied only at the output stage so earlier values are retained,
        resulting in more displayed points.
        
        Args:
            window_years: Window size in years (1 or 5)
            
        Returns:
            Series of rolling correlation values (filtered by horizon)
        """
        if self.data is None or self.data.empty:
            return None
            
        try:
            # Get return data - work on full dataset
            returns = self.data['log_return'].dropna()
            
            if len(returns) < 2:
                return None
                
            # Calculate shifted returns
            returns_shifted = returns.shift(1)
            
            # Determine window size based on frequency
            if self.frequency == 'D':
                window = window_years * 252  # Trading days
            elif self.frequency == 'W':
                window = window_years * 52  # Weeks
            elif self.frequency == 'ME':
                window = window_years * 12  # Months
            elif self.frequency == 'QE':
                window = window_years * 4  # Quarters
            else:
                window = window_years * 52  # Default to weekly
                
            # Calculate rolling correlation on FULL dataset
            rolling_corr = returns.rolling(window=window, min_periods=max(10, window // 2)).corr(returns_shifted)
            rolling_corr.name = f'Return_Autocorr_{window_years}Y'
            
            # Apply horizon filtering at output stage
            return self._apply_horizon(rolling_corr.dropna())
        except Exception as e:
            logger.error(f"Error calculating return autocorrelation: {e}")
            return None
    
    def calculate_osc_correlation(self, window_years: int = 1) -> Optional[pd.Series]:
        """
        Calculate rolling correlation between osc_high and osc_low using the FULL historical dataset.
        Horizon filtering is applied only at the output stage so earlier values are retained,
        resulting in more displayed points.
        
        Args:
            window_years: Window size in years (1 or 5)
            
        Returns:
            Series of rolling correlation values (filtered by horizon)
        """
        if self.data is None or self.data.empty:
            return None
            
        try:
            # Get osc_high and osc_low data - work on full dataset
            osc_high = self.data.get('osc_high')
            osc_low = self.data.get('osc_low')
            
            if osc_high is None or osc_low is None:
                logger.warning("osc_high or osc_low not available in processed data")
                return None
                
            osc_high = osc_high.dropna()
            osc_low = osc_low.dropna()
            
            # Determine window size based on frequency
            if self.frequency == 'D':
                window = window_years * 252  # Trading days
            elif self.frequency == 'W':
                window = window_years * 52  # Weeks
            elif self.frequency == 'ME':
                window = window_years * 12  # Months
            elif self.frequency == 'QE':
                window = window_years * 4  # Quarters
            else:
                window = window_years * 52  # Default to weekly
                
            # Calculate rolling correlation on FULL dataset
            rolling_corr = osc_high.rolling(window=window, min_periods=max(10, window // 2)).corr(osc_low)
            rolling_corr.name = f'Osc_Corr_{window_years}Y'
            
            # Apply horizon filtering at output stage
            return self._apply_horizon(rolling_corr.dropna())
        except Exception as e:
            logger.error(f"Error calculating osc correlation: {e}")
            return None
    
    def generate_consolidated_correlation_chart(self) -> Optional[str]:
        """
        Generate consolidated chart showing both Return Autocorrelation and 
        Oscillation Correlation (Osc_high vs Osc_low) in a single visualization.
        
        Returns:
            Base64-encoded chart image or None
        """
        try:
            # Calculate both types of correlations for 1-year and 5-year windows
            return_1y = self.calculate_return_autocorrelation(window_years=1)
            return_5y = self.calculate_return_autocorrelation(window_years=5)
            osc_1y = self.calculate_osc_correlation(window_years=1)
            osc_5y = self.calculate_osc_correlation(window_years=5)
            
            # Check if we have any data
            if all(x is None or x.empty for x in [return_1y, return_5y, osc_1y, osc_5y]):
                return None
                
            # Create figure with larger size to accommodate legend
            fig, ax = plt.subplots(figsize=(16, 7))
            
            # Plot Return Autocorrelation (1Y and 5Y) with blue tones
            if return_1y is not None and not return_1y.empty:
                ax.plot(return_1y.index, return_1y.values, 
                       color='#1f77b4', linewidth=2, label='Consecutive returns (1Y)', 
                       alpha=0.85, linestyle='-')
            
            if return_5y is not None and not return_5y.empty:
                ax.plot(return_5y.index, return_5y.values, 
                       color='#4d94d6', linewidth=2, label='Consecutive returns (5Y)', 
                       alpha=0.7, linestyle='--')
            
            # Plot Oscillation Correlation (1Y and 5Y) with orange/red tones
            if osc_1y is not None and not osc_1y.empty:
                ax.plot(osc_1y.index, osc_1y.values, 
                       color='#ff7f0e', linewidth=2, label='High-Low Corr (1Y)', 
                       alpha=0.85, linestyle='-', marker='o', markersize=3, markevery=10)
            
            if osc_5y is not None and not osc_5y.empty:
                ax.plot(osc_5y.index, osc_5y.values, 
                       color='#ffb366', linewidth=2, label='High-Low Corr (5Y)', 
                       alpha=0.7, linestyle='--', marker='s', markersize=3, markevery=10)
            
            # Add reference line at y=0
            ax.axhline(y=0, color='gray', linestyle=':', linewidth=1.5, alpha=0.6)
            
            # Set labels and grid
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Correlation', fontsize=12, fontweight='bold')
            ax.set_title('Correlation Dynamics', fontsize=14, fontweight='bold', pad=15)
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # Enhanced legend with description
            legend = ax.legend(
                # loc='upper left', 
                fontsize=8, 
                framealpha=0.95,
                edgecolor='gray',
                ncol=2,
                title='Correlation',
                title_fontsize=9
            )
            legend.get_title().set_fontweight('bold')
            
            # Format y-axis to show correlation values
            ax.set_ylim(-1, 1)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.2f}'))
            
            plt.tight_layout()
            
            # Save as PNG file
            # Removed saving PNG to correlation_charts folder
            
            # Convert to base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close(fig)
            
            base64_str = base64.b64encode(plot_data).decode()
            
            return base64_str
            
        except Exception as e:
            logger.error(f"Error generating consolidated correlation chart: {e}")
            return None
    
    def generate_correlation_chart(self, corr_type: str = 'return') -> Optional[str]:
        """
        Generate line chart showing 1-year and 5-year rolling correlations.
        DEPRECATED: Use generate_consolidated_correlation_chart instead.
        
        Args:
            corr_type: Type of correlation ('return' or 'osc')
            
        Returns:
            Base64-encoded chart image or None
        """
        try:
            # Calculate correlations
            if corr_type == 'return':
                corr_1y = self.calculate_return_autocorrelation(window_years=1)
                corr_5y = self.calculate_return_autocorrelation(window_years=5)
                title = 'Correlation between Consecutive Returns'
            elif corr_type == 'osc':
                corr_1y = self.calculate_osc_correlation(window_years=1)
                corr_5y = self.calculate_osc_correlation(window_years=5)
                title = 'Correlation between Osc_high and Osc_low'
            else:
                logger.error(f"Unknown correlation type: {corr_type}")
                return None
                
            if corr_1y is None and corr_5y is None:
                return None
                
            # Create figure
            fig, ax = plt.subplots(figsize=PLOT_SIZE_CORRELATION)
            
            # Plot 1-year correlation
            if corr_1y is not None and not corr_1y.empty:
                ax.plot(corr_1y.index, corr_1y.values, 
                       color=COLOR_1Y, linewidth=1.5, label='1-Year Rolling', alpha=0.8)
            
            # Plot 5-year correlation
            if corr_5y is not None and not corr_5y.empty:
                ax.plot(corr_5y.index, corr_5y.values, 
                       color=COLOR_5Y, linewidth=1.5, label='5-Year Rolling', alpha=0.8)
            
            # Add reference line at y=0
            ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
            
            # Set labels and grid
            ax.set_xlabel('Date', fontsize=11)
            ax.set_ylabel('Correlation', fontsize=11)
            ax.set_title(title, fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=10, framealpha=0.9)
            
            # Format y-axis to show correlation values
            ax.set_ylim(-1, 1)
            
            plt.tight_layout()
            
            # Save as PNG file
            # Removed saving PNG to correlation_charts folder
            
            # Convert to base64
            buffer = io.BytesIO()
            fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close(fig)
            
            base64_str = base64.b64encode(plot_data).decode()
            
            return base64_str
            
        except Exception as e:
            logger.error(f"Error generating correlation chart: {e}")
            return None
    

    
    def generate_all_correlation_charts(self) -> dict:
        """
        Generate consolidated correlation chart combining both return autocorrelation 
        and oscillation correlation.
        
        Returns:
            Dictionary with consolidated chart URL
        """
        results = {}
        
        try:
            # Generate consolidated chart (combines return autocorr and osc corr)
            consolidated_chart = self.generate_consolidated_correlation_chart()
            if consolidated_chart:
                results['correlation_dynamics_chart'] = consolidated_chart
                # For backward compatibility, also provide under old keys
                results['return_autocorr_chart'] = consolidated_chart
                results['osc_corr_chart'] = consolidated_chart
                
        except Exception as e:
            logger.error(f"Error generating correlation charts: {e}")
            
        return results


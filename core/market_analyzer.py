"""
Market Analyzer - Core business logic for market analysis.

This module builds on top of `PriceDynamic` to compute derived features
and generate charts used by the application. It focuses on:
    - Feature preparation (Oscillation, Returns, Difference)
    - Visualization (scatter with marginals, line dynamics, spread bars,
        volatility dynamics, and projection)
    - Lightweight options P&L visualization

Refactoring highlights:
    - Centralized Matplotlib backend setup (Agg)
    - Module-level plotting constants (colors, sizes)
    - Small helpers for repeated logic (date tick labels, group masks)
    - Removed deprecated and unused tail/gap statistic utilities
    - Improved docstrings and inline comments
"""

from core.price_dynamic import PriceDynamic
import pandas as pd
from pandas.tseries.offsets import BDay
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend once at module import
import matplotlib.pyplot as plt
import io
import base64
import logging
import datetime as dt

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

PLOT_SIZE_SCATTER = (10, 8)
PLOT_SIZE_DYNAMICS = (14.5, 7.0)
PLOT_SIZE_SPREAD = (14.5, 5.2)
PLOT_SIZE_VOLATILITY = (16, 10)
PLOT_SIZE_OPTIONS = (12, 8)
PLOT_SIZE_PROJECTION = (16, 10)

COLOR_OSC = 'tab:blue'
COLOR_RET = 'tab:orange'
COLOR_BULL = 'green'
COLOR_BEAR = 'red'
COLOR_VOL = 'orange'

FREQUENCY_LABELS = {'D': 'Daily', 'W': 'Weekly', 'ME': 'Monthly', 'QE': 'Quarterly'}
VOLATILITY_WINDOWS = {'D': 5, 'W': 5, 'ME': 21, 'QE': 63}

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """High-level market analysis using PriceDynamic for calculations and plots."""

    def __init__(self, ticker: str, start_date: dt.date, frequency: str, end_date: dt.date | None = None):
        self.price_dynamic = PriceDynamic(ticker, start_date, frequency, end_date=end_date)
        self.ticker = ticker
        self.frequency = frequency
        self.end_date = end_date
        if self.price_dynamic.is_valid():
            self._calculate_features()

    def _calculate_features(self):
        """Compute feature series and assemble a clean DataFrame.

        Notes:
            - Oscillation uses on_effect=True per domain requirement.
            - All series are aligned and rows with any NaN are dropped.
        """
        try:
            self.oscillation = self.price_dynamic.osc(on_effect=True)
            self.osc_high = self.price_dynamic.osc_high()
            self.osc_low = self.price_dynamic.osc_low()
            self.returns = self.price_dynamic.ret()
            self.difference = self.price_dynamic.dif()
            self.features_df = (
                pd.DataFrame({
                    'Oscillation': self.oscillation,
                    'Osc_high': self.osc_high,
                    'Osc_low': self.osc_low,
                    'Returns': self.returns,
                    'Difference': self.difference,
                })
                .dropna()
            )
        except Exception as e:
            logger.error(f"Error calculating features: {e}")
            self.features_df = pd.DataFrame()

    def is_data_valid(self):
        """Check if analyzer has valid data"""
        return self.price_dynamic.is_valid()

    # Deprecated single-chart scatter kept only for historical reference.
    # Not used by the current application flow.

    def generate_scatter_plots(self, feature_name, rolling_window=20, risk_threshold=90):
        """Generate scatter plot with marginal histograms.

        Args:
            feature_name: Name of the feature to plot
            rolling_window: Number of historical periods for rolling projections (kept for compatibility but not used)
            risk_threshold: Percentile threshold (0-100) for projections (kept for compatibility but not used)

        Returns:
            str|None: top_chart_base64
        """
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return None
        try:
            x = self.features_df[feature_name]
            y = self.features_df['Returns']
            fig_top = self._create_scatter_hist_plot(x, y)
            return self._fig_to_base64(fig_top)
        except Exception as e:
            logger.error(f"Error generating scatter plot: {e}")
            return None

    def generate_high_low_scatter(self):
        """Generate Osc_Low vs Osc_High scatter plot with marginal histograms.

        Returns:
            str|None: base64-encoded chart or None on error
        """
        if not self.is_data_valid():
            return None
        try:
            # Use Osc_low and Osc_high from features_df
            if 'Osc_low' not in self.features_df.columns or 'Osc_high' not in self.features_df.columns:
                logger.error("Osc_low or Osc_high columns not found in features_df")
                return None
            
            osc_low = self.features_df['Osc_low'].dropna()
            osc_high = self.features_df['Osc_high'].dropna()

            # Align indices to ensure pairs match
            common_index = osc_low.index.intersection(osc_high.index)
            osc_low = osc_low.loc[common_index]
            osc_high = osc_high.loc[common_index]
            
            if osc_low.empty or osc_high.empty:
                logger.error("No valid Osc_low-Osc_high data")
                return None
            
            # Set proper names for axis labels
            osc_low.name = 'Osc_low'
            osc_high.name = 'Osc_high'
            
            # Compute spread and select top-5 indices by (Osc_high - Osc_low)
            try:
                spread = (osc_high - osc_low).dropna()
                top5_indices = spread.nlargest(5).index if len(spread) >= 5 else spread.sort_values(ascending=False).index
            except Exception as e:
                logger.warning(f"Failed to compute spread for labeling: {e}")
                top5_indices = []

            fig = self._create_scatter_hist_plot(osc_low, osc_high, label_indices=top5_indices)
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating Osc_low-Osc_high scatter plot: {e}")
            return None

    def generate_return_osc_high_low_chart(self, rolling_window=20, risk_threshold=90):
        """Generate Return-Oscillation line chart with rolling projections.
        
        Args:
            rolling_window: Number of historical periods for rolling projections
            risk_threshold: Percentile threshold (0-100) for projections
        
        Returns:
            str|None: Base64-encoded chart or None on error
        """
        if not self.is_data_valid() or self.features_df.empty:
            return None
        try:
            # Get filtered data for display
            returns = self.features_df['Returns']
            osc_high = self.features_df['Osc_high']
            osc_low = self.features_df['Osc_low']
            
            # Get full unfiltered data for rolling projections calculation
            # Use apply_horizon=False to get complete historical data
            osc_high_full = self.price_dynamic.osc_high(apply_horizon=False)
            osc_low_full = self.price_dynamic.osc_low(apply_horizon=False)
            
            if osc_high_full is None or osc_low_full is None:
                logger.warning("No full osc data available for rolling projections")
                return None
            
            fig = self._create_return_osc_high_low_plot(
                returns, osc_high, osc_low, 
                osc_high_full, osc_low_full,
                rolling_window, risk_threshold
            )
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating Return-Oscillation chart: {e}")
            return None

    def generate_oscillation_projection(self, percentile=0.90, target_bias=None):
        """Generate oscillation projection figure and summary table.

        Args:
            percentile (float): Percentile threshold for oscillation width.
            target_bias (float|None): If provided, aim for this directional bias
                when optimizing the projection weight; otherwise use natural bias.
        """
        if not self.is_data_valid():
            return None, None
        try:
            # Use full unfiltered data for all calculations
            # This ensures we have complete historical context for projections
            data = self.price_dynamic._data.copy()
            # Calculate oscillation on full unfiltered data
            osc_full = self.price_dynamic.osc(on_effect=True, apply_horizon=False)
            data['Oscillation'] = osc_full
            required_cols = ['High', 'Low', 'LastClose', 'Close', 'Oscillation']
            if not all(col in data.columns for col in required_cols):
                logger.error("Missing required columns for oscillation projection")
                return None, None
            return self._create_oscillation_projection_plot(data, percentile, target_bias)
        except Exception as e:
            logger.error(f"Error generating oscillation projection: {e}")
            return None, None

    def _create_oscillation_projection_plot(self, data, percentile, target_bias):
        try:
            proj_volatility = data["Oscillation"].quantile(percentile)
            if target_bias is None:
                proj_high_weight = self._calculate_natural_bias_weight(data, proj_volatility)
            else:
                proj_high_weight = self._optimize_projection_weight(data, proj_volatility, target_bias)
            px_last_close = data["LastClose"].iloc[-1]
            px_last = data["Close"].iloc[-1]
            proj_high_cur = px_last_close + px_last_close * proj_volatility / 100 * proj_high_weight
            proj_low_cur = px_last_close - px_last_close * proj_volatility / 100 * (1 - proj_high_weight)
            proj_high_next = px_last + px_last * proj_volatility / 100 * proj_high_weight
            proj_low_next = px_last - px_last * proj_volatility / 100 * (1 - proj_high_weight)
            proj_df = self._create_projection_dataframe(data, proj_high_cur, proj_low_cur, proj_high_next, proj_low_next)
            fig = self._plot_oscillation_projection(proj_df, percentile, proj_volatility, target_bias)
            chart_base64 = self._fig_to_base64(fig)
            projection_table = (
                proj_df
                .dropna(how='all')
                .fillna("")
                .apply(lambda col: col.apply(self._format_projection_value) if col.name in ['Close', 'High', 'Low', 'iHigh', 'iLow', 'iHigh1', 'iLow1'] else col)
                .to_html(classes='table table-striped table-sm', index=True, escape=False)
            )
            return chart_base64, projection_table
        except Exception as e:
            logger.error(f"Error creating oscillation projection plot: {e}")
            return None, None

    def _format_projection_value(self, value):
        """Format projection values with dynamic precision based on magnitude"""
        if pd.isna(value) or value == "":
            return ""
        
        try:
            # Convert to float if it's not already
            num_value = float(value)
            
            # Handle zero case
            if num_value == 0:
                return "0.00"
            
            # Get absolute value for calculations
            abs_value = abs(num_value)
            
            # If value is >= 0.01, use standard 2 decimal places
            if abs_value >= 0.01:
                return f"{num_value:.2f}"
            
            # For values < 0.01, find first non-zero decimal place
            # and keep 2 decimal places from there
            decimal_places = 2
            temp_value = abs_value
            
            # Count leading zeros after decimal point
            while temp_value < 0.1 and decimal_places < 10:  # Cap at 10 to prevent infinite loop
                temp_value *= 10
                decimal_places += 1
            
            # Add one more decimal place to get 2 significant digits
            decimal_places += 1
            
            return f"{num_value:.{decimal_places}f}"
            
        except (ValueError, TypeError):
            return str(value)

    def _calculate_natural_bias_weight(self, data, proj_volatility):
        try:
            df = data.iloc[:-1].copy()
            df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * 0.5
            df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * 0.5
            weights = np.linspace(0.3, 0.7, 21)
            best_weight = 0.5
            best_accuracy = 0
            for weight in weights:
                df["ProjHighTest"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * weight
                df["ProjLowTest"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - weight)
                within_range = ((df["Close"] >= df["ProjLowTest"]) & (df["Close"] <= df["ProjHighTest"]))
                accuracy = within_range.sum() / len(df)
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_weight = weight
            return best_weight
        except Exception as e:
            logger.error(f"Error calculating natural bias weight: {e}")
            return 0.5

    def _optimize_projection_weight(self, data, proj_volatility, target_bias):
        if target_bias is None:
            return 0.5
        try:
            weights = np.linspace(0.4, 0.6, 21)
            best_weight = 0.5
            min_error = float('inf')
            for weight in weights:
                bias = self._calculate_realized_bias(data, proj_volatility, weight)
                error = abs(bias - target_bias)
                if error < min_error:
                    min_error = error
                    best_weight = weight
            return best_weight
        except Exception as e:
            logger.error(f"Error optimizing projection weight: {e}")
            return 0.5

    def _calculate_realized_bias(self, data, proj_volatility, weight):
        try:
            df = data.iloc[:-1].copy()
            df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * weight
            df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - weight)
            df["Status"] = np.where(df["Close"] > df["ProjHigh"], 1,
                                   np.where(df["Close"] < df["ProjLow"], -1, 0))
            return ((df["Status"] == 1).sum() - (df["Status"] == -1).sum()) / len(df)
        except Exception as e:
            logger.error(f"Error calculating realized bias: {e}")
            return 0

    def _create_projection_dataframe(self, data, proj_high_cur, proj_low_cur, proj_high_next, proj_low_next):
        try:
            # Get daily data for filling historical values
            daily_data = self.price_dynamic._daily_data
            if daily_data is None or daily_data.empty:
                logger.warning("No daily data available for projection DataFrame")
                return pd.DataFrame()
            
            close_dates = data.get("CloseDate")
            if isinstance(close_dates, pd.Series) and len(close_dates) >= 2:
                date_last_close = close_dates.iloc[-2]
                date_last = close_dates.iloc[-1]
            else:
                # Fallback to data index if CloseDate not available
                date_last_close = data.index[-2] if len(data) >= 2 else data.index[-1]
                date_last = data.index[-1]
            
            # Ensure dates are timezone-aware if daily_data is timezone-aware
            if hasattr(daily_data.index, 'tz') and daily_data.index.tz is not None:
                if not hasattr(date_last_close, 'tz') or date_last_close.tz is None:
                    date_last_close = pd.Timestamp(date_last_close).tz_localize(daily_data.index.tz)
                if not hasattr(date_last, 'tz') or date_last.tz is None:
                    date_last = pd.Timestamp(date_last).tz_localize(daily_data.index.tz)
            
            end_date = date_last + pd.DateOffset(months=2)
            all_weekdays = pd.date_range(start=date_last_close, end=end_date, freq='B')
            
            # Match timezone if needed
            if hasattr(daily_data.index, 'tz') and daily_data.index.tz is not None:
                all_weekdays = all_weekdays.tz_localize(daily_data.index.tz)
            
            proj_df = pd.DataFrame(index=all_weekdays, columns=["Close", "High", "Low", "iHigh", "iLow", "iHigh1", "iLow1"])
            
            # Fill historical data from daily_data between date_last_close and date_last
            historical_period = daily_data.loc[date_last_close:date_last]
            
            # Fill Close, High, Low values from daily data
            for date in historical_period.index:
                if date in proj_df.index:
                    proj_df.loc[date, "Close"] = historical_period.loc[date, "Close"]
                    proj_df.loc[date, "High"] = historical_period.loc[date, "High"]
                    proj_df.loc[date, "Low"] = historical_period.loc[date, "Low"]
            
            # Ensure we have the key reference points
            if date_last_close in proj_df.index and date_last_close in historical_period.index:
                proj_df.loc[date_last_close, "Close"] = historical_period.loc[date_last_close, "Close"]
            if date_last in proj_df.index and date_last in historical_period.index:
                proj_df.loc[date_last, "Close"] = historical_period.loc[date_last, "Close"]
                proj_df.loc[date_last, "High"] = historical_period.loc[date_last, "High"]
                proj_df.loc[date_last, "Low"] = historical_period.loc[date_last, "Low"]
            
            # Determine business-day period length based on selected frequency
            # Mapping: W -> 5, ME -> 22, QE -> 65, default -> 21
            try:
                freq = getattr(self, 'frequency', 'W')
                period_days = 5 if freq == 'W' else 22 if freq == 'ME' else 65 if freq == 'QE' else 21
            except Exception:
                period_days = 21

            current_end = date_last_close + period_days * BDay()
            next_end = date_last + period_days * BDay()
            self._fill_projection_data(proj_df, date_last_close, current_end, proj_high_cur, proj_low_cur, "iHigh", "iLow")
            self._fill_projection_data(proj_df, date_last, next_end, proj_high_next, proj_low_next, "iHigh1", "iLow1")

            # Log data for verification
            historical_data_count = proj_df[["Close", "High", "Low"]].notna().sum().sum()
            projection_data_count = proj_df[["iHigh", "iLow", "iHigh1", "iLow1"]].notna().sum().sum()
            logger.info(f"Projection DataFrame created: {len(proj_df)} total dates, "
                       f"{historical_data_count} historical data points, "
                       f"{projection_data_count} projection data points")
            return proj_df
        except Exception as e:
            logger.error(f"Error creating projection DataFrame: {e}")
            return pd.DataFrame()

    def _get_current_month_end(self, date_last):
        """Return the last calendar day of the current month for the given date."""
        if date_last.month < 12:
            return dt.datetime(date_last.year, date_last.month + 1, 1) - pd.Timedelta(days=1)
        else:
            return dt.datetime(date_last.year + 1, 1, 1) - pd.Timedelta(days=1)

    def _fill_projection_data(self, proj_df, start_date, end_date, proj_high, proj_low, high_col, low_col):
        try:
            weekdays = pd.date_range(start=start_date, end=end_date, freq='B')[1:]
            start_price = proj_df.loc[start_date, "Close"]
            for i, date in enumerate(weekdays):
                if date in proj_df.index:
                    progress = np.sqrt((i + 1) / len(weekdays))
                    proj_df.loc[date, high_col] = start_price + (proj_high - start_price) * progress
                    proj_df.loc[date, low_col] = start_price + (proj_low - start_price) * progress
        except Exception as e:
            logger.error(f"Error filling projection data: {e}")

    def _plot_oscillation_projection(self, proj_df, percentile, proj_volatility, target_bias):
        fig, ax = plt.subplots(figsize=PLOT_SIZE_PROJECTION)
        try:
            x_values = np.arange(len(proj_df.index))
            self._plot_projection_points(ax, x_values, proj_df)
            bias_text = "Natural" if target_bias is None else f"Neutral ({target_bias})"
            self._format_projection_plot(ax, proj_df, percentile, proj_volatility, bias_text)
            return fig
        except Exception as e:
            logger.error(f"Error plotting oscillation projection: {e}")
            return fig

    def _plot_projection_points(self, ax, x_values, proj_df):
        # Plot Close values with black circle points
        close_mask = ~proj_df["Close"].isna()
        if close_mask.any():
            ax.scatter(x_values[close_mask], proj_df["Close"][close_mask], 
                      label="Close", color="green", s=50, marker='o', zorder=3)
        
        # Plot High values with purple upward triangle points
        high_mask = ~proj_df["High"].isna()
        if high_mask.any():
            ax.scatter(x_values[high_mask], proj_df["High"][high_mask], 
                      label="High", color="purple", s=50, marker='^', zorder=3)
            # Connect consecutive High points with a purple line
            ax.plot(x_values[high_mask], proj_df["High"][high_mask], 
                    color="purple", linewidth=1.5, alpha=0.8, solid_capstyle='round', label='_nolegend_')
        
        # Plot Low values with blue downward triangle points
        low_mask = ~proj_df["Low"].isna()
        if low_mask.any():
            ax.scatter(x_values[low_mask], proj_df["Low"][low_mask], 
                      label="Low", color="blue", s=50, marker='v', zorder=3)
            # Connect consecutive Low points with a blue line
            ax.plot(x_values[low_mask], proj_df["Low"][low_mask], 
                    color="blue", linewidth=1.5, alpha=0.8, solid_capstyle='round', label='_nolegend_')
        
        # Plot projection lines
        for col, color, label in [("iHigh", "red", "Proj High (Current)"), ("iLow", "red", "Proj Low (Current)"), ("iHigh1", "orange", "Proj High (Next)"), ("iLow1", "orange", "Proj Low (Next)")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], label=label, 
                          facecolors='none', edgecolors=color, s=80, linewidth=2, zorder=3)

    def _format_projection_plot(self, ax, proj_df, percentile, proj_volatility, bias_text):
        """Apply consistent labels, ticks, and legend to the projection chart."""
        # Display all x-axis labels with vertical rotation
        ax.set_xticks(range(len(proj_df.index)))
        ax.set_xticklabels([date.strftime('%m/%d') for date in proj_df.index], 
                          rotation=90, fontsize=8)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)
        ax.set_title('Oscillation Projection', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Create parameter info text box in upper left
        param_text = f'Threshold: {percentile:.0%}\nVolatility: {proj_volatility:.1f}%\nBias: {bias_text}'
        ax.text(0.02, 0.98, param_text, transform=ax.transAxes,
                fontsize=12, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        ax.legend(fontsize=12, loc='upper right')
        plt.tight_layout()

    # Removed legacy tail statistics and cumulative distribution utilities.
    # The current application flow no longer surfaces these views.

    def generate_volatility_dynamics(self):
        if not self.is_data_valid():
            return None
        try:
            daily_data = self.price_dynamic._daily_data
            if daily_data is None or daily_data.empty:
                return None
            volatility = self.price_dynamic.calculate_volatility()
            if volatility is None or volatility.empty:
                return None
            # Align close price series with the Horizon so segments match volatility timeframe
            daily_close = self.price_dynamic._apply_horizon(daily_data['Close'])
            if daily_close is None or daily_close.empty:
                return None
            bull_bear_segments = self.price_dynamic.bull_bear_plot(daily_close)
            fig, ax1 = plt.subplots(figsize=PLOT_SIZE_VOLATILITY)
            ax1.set_xlabel('Date', fontsize=12)
            ax1.set_ylabel('Price ($)', fontsize=12, color='black')
            
            # Plot price data with bull/bear segments
            for segment in bull_bear_segments['bull_segments']:
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color=COLOR_BULL, linewidth=2, alpha=0.5)
            for segment in bull_bear_segments['bear_segments']:
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color=COLOR_BEAR, linewidth=2, alpha=0.5)
            
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.grid(True, alpha=0.3)
            
            # Create second y-axis for volatility
            ax2 = ax1.twinx()
            ax2.set_ylabel('Volatility (%)', fontsize=12, color='blue')
            ax2.plot(volatility.index, volatility.values, color=COLOR_VOL, linewidth=3, alpha=0.7, label='Historical Volatility', linestyle='-')
            ax2.tick_params(axis='y', labelcolor='blue')
            
            # Add current volatility point
            current_vol = volatility.iloc[-1] if len(volatility) > 0 else volatility.mean()
            ax2.scatter(x=volatility.index[-1], y=current_vol, color='purple', s=100, marker='o', linewidth=1.5, alpha=0.8, zorder=5)
            
            # Set title and legend
            frequency_name = FREQUENCY_LABELS.get(self.frequency, self.frequency)
            window = VOLATILITY_WINDOWS.get(self.frequency, 21)
            ax1.set_title(f'{self.ticker} - Price & Volatility Dynamics\nVolatility Window: {window} days ({frequency_name} frequency)', fontsize=14, fontweight='bold', pad=20)
            
            # Create legend
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], color=COLOR_BULL, linewidth=2, label='Bull'),
                Line2D([0], [0], color=COLOR_BEAR, linewidth=2, label='Bear'),
                Line2D([0], [0], color=COLOR_VOL, linewidth=2, label=f'Volatility, *{current_vol:.1f}%'),
            ]
            ax1.legend(handles=legend_elements, loc='upper left', fontsize=10, framealpha=0.8, bbox_to_anchor=(0.0, 1.0), borderaxespad=0.1)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating volatility dynamics: {e}")
            return None

    def analyze_options(self, option_data):
        if not option_data:
            return None
        try:
            current_price = self._get_current_price()
            if current_price is None:
                return None
            option_matrix = self._calculate_option_matrix(current_price, option_data)
            return self._create_option_pnl_chart(option_matrix, current_price)
        except Exception as e:
            logger.error(f"Error analyzing options: {e}")
            return None

    def _get_current_price(self):
        try:
            if self.is_data_valid():
                return self.price_dynamic._data["Close"].iloc[-1]
            return None
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None

    def _calculate_option_matrix(self, current_price, option_data):
        try:
            price_range = np.linspace(current_price * 0.7, current_price * 1.3, 301)
            matrix_df = pd.DataFrame(index=price_range)
            matrix_df['PnL'] = 0.0
            for option in option_data:
                option_type = option['option_type']
                strike = option['strike']
                quantity = option['quantity']
                premium = option['premium']
                pnl = self._calculate_single_option_pnl(
                    price_range, option_type, strike, quantity, premium
                )
                matrix_df['PnL'] += pnl
            return matrix_df
        except Exception as e:
            logger.error(f"Error calculating option matrix: {e}")
            return None

    def _calculate_single_option_pnl(self, prices, option_type, strike, quantity, premium):
        if option_type == 'SC':  # Short Call
            return np.where(prices > strike, (premium - (prices - strike)) * quantity, premium * quantity)
        elif option_type == 'SP':  # Short Put
            return np.where(prices < strike, (premium - (strike - prices)) * quantity, premium * quantity)
        elif option_type == 'LC':  # Long Call
            return np.where(prices > strike, (prices - strike - premium) * quantity, -premium * quantity)
        elif option_type == 'LP':  # Long Put
            return np.where(prices < strike, (strike - prices - premium) * quantity, -premium * quantity)
        else:
            return np.zeros_like(prices)

    def _create_option_pnl_chart(self, matrix_df, current_price):
        try:
            fig, ax = plt.subplots(figsize=PLOT_SIZE_OPTIONS)
            ax.plot(matrix_df.index, matrix_df['PnL'], linewidth=3, color='blue')
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
            ax.axvline(x=current_price, color='red', linestyle='--', alpha=0.8, linewidth=2, label=f'Current Price: ${current_price:.2f}')
            ax.fill_between(matrix_df.index, matrix_df['PnL'], 0, where=(matrix_df['PnL'] > 0), color='green', alpha=0.3, label='Profit')
            ax.fill_between(matrix_df.index, matrix_df['PnL'], 0, where=(matrix_df['PnL'] < 0), color='red', alpha=0.3, label='Loss')
            ax.set_xlabel('Stock Price ($)', fontsize=12)
            ax.set_ylabel('P&L ($)', fontsize=12)
            ax.set_title('Options Portfolio P&L Analysis', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11)
            max_profit = matrix_df['PnL'].max()
            max_loss = matrix_df['PnL'].min()
            breakeven_points = self._find_breakeven_points(matrix_df)
            stats_text = f'Max Profit: ${max_profit:.0f}\nMax Loss: ${max_loss:.0f}'
            if breakeven_points:
                stats_text += f'\nBreakeven: ${breakeven_points[0]:.0f}'
                if len(breakeven_points) > 1:
                    stats_text += f', ${breakeven_points[1]:.0f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=12, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error creating option P&L chart: {e}")
            return None

    def _find_breakeven_points(self, matrix_df):
        try:
            pnl_values = matrix_df['PnL'].values
            prices = matrix_df.index.values
            breakeven_points = []
            for i in range(len(pnl_values) - 1):
                if (pnl_values[i] <= 0 <= pnl_values[i + 1]) or (pnl_values[i] >= 0 >= pnl_values[i + 1]):
                    if pnl_values[i + 1] != pnl_values[i]:
                        breakeven_price = prices[i] - pnl_values[i] * (prices[i + 1] - prices[i]) / (pnl_values[i + 1] - pnl_values[i])
                        breakeven_points.append(breakeven_price)
            return breakeven_points
        except Exception as e:
            logger.error(f"Error finding breakeven points: {e}")
            return []

    # def _create_scatter_hist_plot(self, x, y):
    #     """Backward-compat shim to the top scatter plot."""
    #     fig = self._create_scatter_hist_top_plot(x, y)
    #     return fig

    def _create_scatter_hist_plot(self, x, y, label_indices=None):
        """Create the top main scatter with marginal histograms as a standalone figure.

        Args:
            x (pd.Series): X-axis series
            y (pd.Series): Y-axis series
            label_indices (Iterable|None): Optional iterable of index labels to annotate.
                When provided, only these points are labeled; otherwise falls back to
                labeling the five largest x-values (legacy behavior).
        """
        fig = plt.figure(figsize=PLOT_SIZE_SCATTER)
        gs = fig.add_gridspec(
            2, 2, 
            width_ratios=(3, 1), 
            height_ratios=(1, 3), 
            left=0.05, right=0.95, 
            bottom=0.05, top=0.95, 
            wspace=0.05,  
            hspace=0.05
        )
        ax = fig.add_subplot(gs[1, 0])
        ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
        ax_histx.tick_params(axis="x", labelbottom=False)
        ax_histy.tick_params(axis="y", labelleft=False)

        # Main scatter plot - plot base points first
        ax.scatter(x, y, alpha=0.5, s=20, c="orange")

        ax.axhline(y=0, color='gray', linestyle='-', linewidth=5, alpha=0.05)
        ax.axvline(x=0, color='gray', linestyle='-', linewidth=5, alpha=0.05)

        ax.set_aspect('auto', adjustable='box')

        # Add vertical dashed lines for oscillation percentiles
        osc_percentiles = np.percentile(x, [20, 40, 60, 80])
        for p in osc_percentiles:
            ax.axvline(p, color='blue', linestyle='dashed', linewidth=1, alpha=0.2)

        # Add horizontal dashed lines for return percentiles
        ret_percentiles = np.percentile(y, [20, 40, 60, 80])
        for p in ret_percentiles:
            ax.axhline(p, color='blue', linestyle='dashed', linewidth=1, alpha=0.2)

        # Determine indices to highlight with colors
        try:
            indices_to_label = None
            if label_indices is not None:
                # Filter to indices present in both series
                indices_to_label = [idx for idx in label_indices if idx in x.index and idx in y.index]
            elif len(x) >= 5:
                indices_to_label = x.nlargest(5).index
            
            # Get recent indices
            recent_indices = x.index[-5:] if len(x) >= 5 else []
            
            # Separate into three groups: top only, recent only, and both
            top_only = []
            recent_only = []
            both = []
            
            if indices_to_label is not None:
                for idx in indices_to_label:
                    if idx in recent_indices:
                        both.append(idx)
                    else:
                        top_only.append(idx)
            
            for idx in recent_indices:
                if indices_to_label is None or idx not in indices_to_label:
                    recent_only.append(idx)
            
            # Plot colored spots for top maximums (red) - exclude ones that are also recent
            if len(top_only) > 0:
                ax.scatter([x.loc[idx] for idx in top_only], 
                          [y.loc[idx] for idx in top_only],
                          color='red', s=20, zorder=4, alpha=0.7,  )
            
            # Plot colored spots for recent periods (blue) - exclude ones that are also top
            if len(recent_only) > 0:
                ax.scatter([x.loc[idx] for idx in recent_only], 
                          [y.loc[idx] for idx in recent_only],
                          color='blue', s=20, zorder=4, alpha=0.7, )
            
            # Plot colored spots for both (purple) - points that are both recent and top maximum
            if len(both) > 0:
                ax.scatter([x.loc[idx] for idx in both], 
                          [y.loc[idx] for idx in both],
                          color='purple', s=20, zorder=5, alpha=0.7, )
            
            # Add labels for top maximums
            if indices_to_label is not None and len(indices_to_label) > 0:
                for idx in indices_to_label:
                    ax.annotate(
                        f'{idx.strftime("%y%b")}',
                        xy=(x.loc[idx], y.loc[idx]),
                        xytext=(5, -5), textcoords='offset points',
                        fontsize=6, color='red',
                    )
            
            # Add labels for recent periods
            for idx in recent_indices:
                ax.annotate(
                    f'{idx.strftime("%b")}',
                    xy=(x.loc[idx], y.loc[idx]),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=6, color='blue',
                )
        except Exception as e:
            logger.warning(f"Failed to add labels and colored spots: {e}")

        ax.grid(True, alpha=0.3)
        ax.set_xlabel(f'{x.name} (%)', fontsize=12)
        ax.set_ylabel(f'{y.name} (%)', fontsize=12)

        # Generate bins for x-axis data with fixed length of 1 and boundaries ending with 0.5
        # bins_x, bins_y = None, None
        if len(x) > 0:
            min_x = x.min()
            max_x = x.max()
            # Calculate left boundary (maximum x.5 value <= min_x)
            left_x = np.floor(min_x + 0.5) - 0.5  # Core formula: ensure boundary ends with 0.5
            # Calculate right boundary (minimum x.5 value >= max_x)
            right_x = np.ceil(max_x - 0.5) + 0.5   # Core formula: ensure boundary ends with 0.5
            # Generate bin sequence (step=1, covering all data)
            bins_x = np.arange(left_x, right_x + 1, 1)  # +1 to ensure right boundary is included
        else:
            # Default bins when data is empty (to avoid errors)
            bins_x = np.arange(-0.5, 5.5, 1)

        # Generate bins for y-axis data with fixed length of 1 and boundaries ending with 0.5 (same logic as above)
        if len(y) > 0:
            min_y = y.min()
            max_y = y.max()
            left_y = np.floor(min_y + 0.5) - 0.5
            right_y = np.ceil(max_y - 0.5) + 0.5
            bins_y = np.arange(left_y, right_y + 1, 1)
        else:
            bins_y = np.arange(-0.5, 5.5, 1)

        # Plot top histogram (using custom bins)
        ax_histx.hist(x, bins=bins_x, alpha=0.7, color='skyblue', edgecolor='black')
        # Plot right histogram (using custom bins)
        ax_histy.hist(y, bins=bins_y, alpha=0.7, color='lightcoral', orientation='horizontal', edgecolor='black')

        # ax_histx.hist(x, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        # ax_histy.hist(y, bins=30, alpha=0.7, color='lightcoral', orientation='horizontal', edgecolor='black')

        # Add percentile labels for the latest data point on upper and right charts
        try:
            if len(x) > 0:
                latest_x = x.iloc[-1]
                x_percentile = float(((x <= latest_x).sum() / len(x)) * 100.0)
                ax_histx.text(
                    0.98,
                    0.90,
                    f"Osc Percentile: {x_percentile:.1f}%",
                    transform=ax_histx.transAxes,
                    ha='right', va='top', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                )
            if len(y) > 0:
                latest_y = y.iloc[-1]
                y_percentile = float(((y <= latest_y).sum() / len(y)) * 100.0)
                ax_histy.text(
                    0.05,
                    0.98,
                    f"Ret Percentile: {y_percentile:.1f}%",
                    transform=ax_histy.transAxes,
                    ha='left', va='top', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                )
        except Exception as e:
            logger.warning(f"Failed to add percentile labels: {e}")

        # Add supplementary data table on the main chart (Overall vs Risk)
        self._add_oscillation_analysis_table(ax, x, y)

        fig.suptitle(f'{x.name} vs {y.name} Analysis', fontsize=14, fontweight='bold')
        return fig

    def _calculate_rolling_projections(self, series, rolling_window, risk_threshold):
        """Calculate rolling projections using historical percentiles.
        
        For each data point, calculates the percentile of the previous rolling_window points.
        
        Args:
            series: Time series data (e.g., osc_high or osc_low)
            rolling_window: Number of historical periods to use
            risk_threshold: Percentile threshold (0-100)
            
        Returns:
            pd.Series: Rolling projection values
        """
        percentile = risk_threshold / 100.0
        projections = []
        
        for i in range(len(series)):
            if i < rolling_window:
                # Not enough historical data
                projections.append(np.nan)
            else:
                # Get previous rolling_window points (excluding current point)
                historical_window = series.iloc[i - rolling_window:i]
                proj_value = historical_window.quantile(percentile)
                projections.append(proj_value)
        
        return pd.Series(projections, index=series.index)

    def _create_return_osc_high_low_plot(self, returns, osc_high, osc_low, 
                                          osc_high_full, osc_low_full,
                                          rolling_window=20, risk_threshold=90):
        """Create a line chart showing Returns, Osc_high, Osc_low, and their rolling projections over time.
        
        Args:
            returns: Returns series (filtered to display horizon)
            osc_high: Osc_high series (filtered to display horizon)
            osc_low: Osc_low series (filtered to display horizon)
            osc_high_full: Osc_high series (complete historical dataset, before horizon filtering)
            osc_low_full: Osc_low series (complete historical dataset, before horizon filtering)
            rolling_window: Number of historical periods for rolling projections
            risk_threshold: Percentile threshold (0-100) for projections
            
        Returns:
            matplotlib.figure.Figure: The generated figure
        """
        from matplotlib.lines import Line2D
        fig, ax = plt.subplots(figsize=PLOT_SIZE_DYNAMICS)
        
        # Prepare valid data for display
        valid_mask = returns.notna() & osc_high.notna() & osc_low.notna()
        returns_valid = returns[valid_mask]
        osc_high_valid = osc_high[valid_mask]
        osc_low_valid = osc_low[valid_mask]
        n = len(returns_valid)
        
        if n == 0:
            ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center', va='center')
            ax.axis('off')
            return fig
            
        t_idx = np.arange(n)
        
        # Calculate rolling projections using FULL historical dataset
        # This ensures accurate projections based on complete history
        high_proj_full = self._calculate_rolling_projections(osc_high_full, rolling_window, risk_threshold)
        low_proj_full = self._calculate_rolling_projections(osc_low_full, rolling_window, 100-risk_threshold)
        
        # Filter projections to match display horizon
        high_proj = high_proj_full.reindex(osc_high_valid.index)
        low_proj = low_proj_full.reindex(osc_low_valid.index)
        
        # Plot main series as spots
        ax.scatter(t_idx, returns_valid.values, color=COLOR_RET, s=25, marker='o', label='Returns', alpha=0.8, zorder=3)
        
        ax.scatter(
            t_idx,
            osc_high_valid.values,
            s=40,
            marker='s',
            facecolors='none',
            edgecolors='purple',
            linewidths=1.4,
            label='Osc_high',
            alpha=0.9,
            zorder=4,
        )
        ax.scatter(
            t_idx,
            osc_low_valid.values,
            s=40,
            marker='s',
            facecolors='none',
            edgecolors='blue',
            linewidths=1.4,
            label='Osc_low',
            alpha=0.9,
            zorder=4,
        )
        

        # Plot rolling projections with last value in legend
        last_high_proj = high_proj.iloc[-1] if high_proj is not None and not high_proj.empty else None
        last_low_proj = low_proj.iloc[-1] if low_proj is not None and not low_proj.empty else None
        if high_proj is not None and not high_proj.empty:
            label_high = f'High Proj ({risk_threshold}%)'
            if last_high_proj is not None:
                label_high += f' *{last_high_proj:.2f}'
            ax.plot(t_idx, high_proj.to_numpy(), color='darkgreen', linewidth=1.2, linestyle='--', 
                label=label_high, alpha=0.6)
        if low_proj is not None and not low_proj.empty:
            label_low = f'Low Proj ({risk_threshold}%)'
            if last_low_proj is not None:
                label_low += f' *{last_low_proj:.2f}'
            ax.plot(t_idx, low_proj.to_numpy(), color='darkred', linewidth=1.2, linestyle='--', 
                label=label_low, alpha=0.6)
            
        # Add reference line at y=0
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=1, alpha=0.3)
        
        # Set labels and grid
        ax.set_xlabel('Index', fontsize=11)
        ax.set_ylabel('Percentage (%)', fontsize=11)
        ax.grid(True, alpha=0.3)
        
        # Add date ticks
        try:
            tick_pos, tick_labels = self._build_date_ticks(returns_valid.index, n, approx_ticks=20)
            ax.set_xticks(tick_pos)
            ax.set_xticklabels(tick_labels, rotation=90, fontsize=9)
        except Exception:
            pass
            
        ax.legend(loc='upper left', fontsize=8, framealpha=0.85)
        ax.set_title('Return-Oscillation Dynamics', fontsize=13, fontweight='bold')
        plt.tight_layout()
        return fig

    def _add_oscillation_analysis_table(self, ax, oscillation_data, returns_data):
        """Add a comprehensive table showing Overall and Risk analysis for current oscillation context"""
        try:
            # Ensure we have valid data
            if oscillation_data is None or oscillation_data.empty or returns_data is None or returns_data.empty:
                logger.warning("No oscillation or returns data available for table generation")
                return
            
            # Get the latest oscillation and return values (most recent data points)
            latest_oscillation = oscillation_data.iloc[-1]
            latest_return = returns_data.iloc[-1]
            
            # Align oscillation and returns data by index to ensure consistency
            aligned_data = pd.DataFrame({
                'oscillation': oscillation_data,
                'returns': returns_data
            }).dropna()
            
            if aligned_data.empty:
                logger.warning("No aligned oscillation and returns data available")
                return
            
            # Filter stronger_oscillation: Historical oscillation value >= latest oscillation value
            filter_stronger_oscillation_data = aligned_data[aligned_data['oscillation'] >= latest_oscillation]
            
            if filter_stronger_oscillation_data.empty:
                logger.warning("No data points found meeting stronger_oscillation criteria")
                return
            
            # Filter stronger_returns_momentum: sign(current_return) × historical return >= sign(current_return) × current_return
            # This isolates periods where historical returns moved stronger to current return direction
            latest_return_sign = 1 if latest_return >= 0 else -1
            filter_stronger_returns_momentum_condition = (
                latest_return_sign * filter_stronger_oscillation_data['returns'] 
                >= latest_return_sign * latest_return
            )
    
            filter_stronger_returns_momentum_data = filter_stronger_oscillation_data[
                filter_stronger_returns_momentum_condition
            ]  # stronger momentum (risk scenarios)
            
            # Calculate Overall metrics (Filter 1 only)
            total_points = len(aligned_data)
            overall_counts = len(filter_stronger_oscillation_data)
            overall_frequency = (overall_counts / total_points) * 100 if total_points > 0 else 0
            overall_median_returns = filter_stronger_oscillation_data['returns'].median()
            
            # Calculate Risk metrics (Filter 1 + Filter 2)
            risk_counts = len(filter_stronger_returns_momentum_data)
            risk_frequency = (risk_counts / total_points) * 100 if total_points > 0 else 0
            risk_median_returns = filter_stronger_returns_momentum_data['returns'].median() if not filter_stronger_returns_momentum_data.empty else float('nan')
            
            # Create table data
            table_data = [
                ["#No", f"{overall_counts}", f"{risk_counts}"],
                ["Freq", f"{overall_frequency:.1f}%", f"{risk_frequency:.1f}%"],
                ["Ret Median", f"{overall_median_returns:.2f}%", f"{risk_median_returns:.2f}%" if not pd.isna(risk_median_returns) else "N/A"]
            ]
            
            # Create table in upper left corner with Overall and Risk columns
            table = ax.table(
                cellText=table_data,
                colLabels=["Stronger\nOsc", "Overall", "Risk"],
                cellLoc='left',
                loc='upper left',
                bbox=[0.02, 0.8, 0.20, 0.20]  # [x, y, width, height]
            )
            
            # Style the table
            table.auto_set_font_size(False)
            # Reduce font size for all text within the in-chart table
            table.set_fontsize(6)
            table.scale(1, 1.2)
            
            # Style header
            for i in range(3):  # Now 3 columns
                table[(0, i)].set_facecolor('#E6E6FA')
                table[(0, i)].set_text_props(weight='bold')
            
            # Style data cells
            for i in range(1, len(table_data) + 1):
                table[(i, 0)].set_facecolor('#F8F8FF')
                for j in range(1, 3):  # Overall and Risk columns
                    table[(i, j)].set_facecolor('#FFFFFF')
                    table[(i, j)].set_text_props(weight='bold', color='#333333')
            
            # Add border
            for key, cell in table.get_celld().items():
                cell.set_linewidth(1)
                cell.set_edgecolor('#CCCCCC')
            
            # Add a subtitle to clarify what the table shows with enhanced context
            subtitle_text = (
                f'Historical Analysis\n'
                f'* Osc={latest_oscillation:.1f}%, Ret={latest_return:.1f}%'
                )
            ax.text(0.02, 0.75, subtitle_text, 
                   transform=ax.transAxes, fontsize=7, ha='left', va='top',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
                    
        except Exception as e:
            logger.error(f"Error adding oscillation analysis table: {e}")

    def _fig_to_base64(self, fig):
        """Convert matplotlib figure to base64 string"""
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plot_url = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        return plot_url

    # -----------------------------------------------------------------------
    # Small internal helpers
    # -----------------------------------------------------------------------

    def _build_date_ticks(self, index, n_points: int, approx_ticks: int = 20):
        """Return (positions, labels) for date-like x-axis ticks.

        Args:
            index (pd.Index): Time index to label from.
            n_points (int): Total number of points in the plot.
            approx_ticks (int): Desired rough number of ticks.

        Returns:
            tuple[list[int], list[str]]: positions and string labels like '25Jan'.
        """
        step = max(1, n_points // max(1, approx_ticks))
        positions = list(np.arange(0, n_points, step))
        date_index = index
        labels = [pd.Timestamp(date_index[int(p)]).strftime('%y%b') for p in positions]
        return positions, labels

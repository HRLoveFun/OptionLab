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

PLOT_SIZE_SCATTER_TOP = (12.5, 18)
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

    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='W', end_date: dt.date | None = None):
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
            self.returns = self.price_dynamic.ret()
            self.difference = self.price_dynamic.dif()
            self.features_df = (
                pd.DataFrame({
                    'Oscillation': self.oscillation,
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

    def generate_scatter_plots(self, feature_name):
        """Generate separate top (scatter+marginal histograms) and bottom dynamics charts.

        Returns:
            tuple[str|None, str|None]: (top_chart_base64, bottom_chart_base64)
        """
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return None, None
        try:
            x = self.features_df[feature_name]
            y = self.features_df['Returns']
            fig_top = self._create_scatter_hist_top_plot(x, y)
            fig_bottom = self._create_return_osc_dynamic_plot(x, y)
            return self._fig_to_base64(fig_top), self._fig_to_base64(fig_bottom)
        except Exception as e:
            logger.error(f"Error generating split scatter plots: {e}")
            return None, None

    def generate_osc_ret_spread_plot(self):
        """Generate 'Oscillation-Returns Spread Dynamics' bar chart.

        Notes:
            Spread is computed as Oscillation - Returns and visualized
            with color coding by sign.
        """
        if not self.is_data_valid() or self.features_df.empty:
            return None
        try:
            x = self.features_df['Oscillation']
            y = self.features_df['Returns']
            spread = (x - y).rename('Spread')
            fig = self._create_spread_dynamics_bar_plot(spread)
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating spread dynamics plot: {e}")
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
            data = self.price_dynamic._data.copy()
            data['Oscillation'] = self.oscillation
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
            
            current_month_end = self._get_current_month_end(date_last)
            next_twenty_days = date_last + pd.Timedelta(days=4*7)
            self._fill_projection_data(proj_df, date_last_close, current_month_end, proj_high_cur, proj_low_cur, "iHigh", "iLow")
            self._fill_projection_data(proj_df, date_last, next_twenty_days, proj_high_next, proj_low_next, "iHigh1", "iLow1")
            
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
        ax.set_title(f'Oscillation Projection (Threshold: {percentile:.0%}, Volatility: {proj_volatility:.1f}%, Bias: {bias_text})', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
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
            daily_close = daily_data['Close']
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
                Line2D([0], [0], color=COLOR_BULL, linewidth=2, label='Bull Market'),
                Line2D([0], [0], color=COLOR_BEAR, linewidth=2, label='Bear Market'),
                Line2D([0], [0], color=COLOR_VOL, linewidth=2, label='Volatility'),
                Line2D([0], [0], color=COLOR_VOL, linestyle='--', linewidth=2, label=f'Current Vol: {current_vol:.1f}%'),
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

    def _create_scatter_hist_plot(self, x, y):
        """Backward-compat shim to the top scatter plot."""
        fig = self._create_scatter_hist_top_plot(x, y)
        return fig

    def _create_scatter_hist_top_plot(self, x, y):
        """Create the top main scatter with marginal histograms as a standalone figure."""
        fig = plt.figure(figsize=PLOT_SIZE_SCATTER_TOP)
        gs = fig.add_gridspec(2, 2, width_ratios=(3, 1), height_ratios=(1, 3), left=0.08, right=0.96, bottom=0.10, top=0.92, wspace=0.08, hspace=0.08)
        ax_left = fig.add_subplot(gs[1, 0])
        ax_histx_left = fig.add_subplot(gs[0, 0], sharex=ax_left)
        ax_histy_left = fig.add_subplot(gs[1, 1], sharey=ax_left)
        ax_histx_left.tick_params(axis="x", labelbottom=False)
        ax_histy_left.tick_params(axis="y", labelleft=False)

        # Main scatter (left)
        ax_left.scatter(x, y, alpha=0.6, s=30, c=COLOR_OSC)
        xlim = ax_left.get_xlim()
        ax_left.plot(xlim, [0, 0], 'k--', alpha=0.5, linewidth=1)
        ax_left.set_aspect('equal', adjustable='box')

        # Label the five points with largest oscillation
        if len(x) >= 5:
            largest_osc_indices = x.nlargest(5).index
            for idx in largest_osc_indices:
                ax_left.annotate(
                    f'{idx.strftime("%y%b")}',
                    xy=(x.loc[idx], y.loc[idx]),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, color='red', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                )

        # Label the five most recent points
        if len(x) >= 5:
            recent_indices = x.index[-5:]
            for idx in recent_indices:
                ax_left.annotate(
                    f'{idx.strftime("%y%b")}',
                    xy=(x.loc[idx], y.loc[idx]),
                    xytext=(-5, -15), textcoords='offset points',
                    fontsize=8, color='blue', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7),
                )

        if len(x) > 0 and len(y) > 0:
            ax_left.scatter(x.iloc[-1], y.iloc[-1], color='red', s=100, zorder=5, edgecolors='darkred', linewidth=2)
        ax_left.grid(True, alpha=0.3)
        ax_left.set_xlabel(f'{x.name} (%)', fontsize=12)
        ax_left.set_ylabel(f'{y.name} (%)', fontsize=12)
        ax_histx_left.hist(x, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax_histy_left.hist(y, bins=30, alpha=0.7, color='lightcoral', orientation='horizontal', edgecolor='black')

        # Add percentile labels for the latest data point on upper and right charts
        try:
            if len(x) > 0:
                latest_x = x.iloc[-1]
                x_percentile = float(((x <= latest_x).sum() / len(x)) * 100.0)
                ax_histx_left.text(
                    0.98,
                    0.90,
                    f"Osc Percentile: {x_percentile:.1f}%",
                    transform=ax_histx_left.transAxes,
                    ha='right', va='top', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                )
            if len(y) > 0:
                latest_y = y.iloc[-1]
                y_percentile = float(((y <= latest_y).sum() / len(y)) * 100.0)
                ax_histy_left.text(
                    0.05,
                    0.98,
                    f"Ret Percentile: {y_percentile:.1f}%",
                    transform=ax_histy_left.transAxes,
                    ha='left', va='top', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
                )
        except Exception as e:
            logger.warning(f"Failed to add percentile labels: {e}")

        # Add supplementary data table on the main chart (Overall vs Risk)
        self._add_oscillation_analysis_table(ax_left, x, y)

        fig.suptitle(f'{x.name} vs {y.name} Analysis', fontsize=14, fontweight='bold')
        return fig

    def _create_return_osc_dynamic_plot(self, x, y):
        """Create a 2D line chart: X=Index, Y includes Oscillation (blue) and Returns (orange).

        Grouped points from the original 3D chart are annotated with different marker styles:
        - Stronger oscillation: solid dots
        - Next step of Stronger oscillation: hollow squares
        """
        from matplotlib.lines import Line2D
        # Increased figure size for better readability per request
        fig, ax = plt.subplots(figsize=PLOT_SIZE_DYNAMICS)

        # Prepare valid data
        valid_mask = x.notna() & y.notna()
        x_valid = x[valid_mask]  # Oscillation (%)
        y_valid = y[valid_mask]  # Returns (%)
        n = len(x_valid)
        if n == 0:
            ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center', va='center')
            ax.axis('off')
            return fig
        t_idx = np.arange(n)

        # Plot lines
        ax.plot(t_idx, x_valid.values, color=COLOR_OSC, linewidth=0.5, label=f'{x.name}')
        ax.plot(t_idx, y_valid.values, color=COLOR_RET, linewidth=0.5, label=f'{y.name}')

        # Group definitions based on oscillation
        group1_mask = pd.Series(False, index=x_valid.index)
        group2_mask = pd.Series(False, index=x_valid.index)
        if n >= 2:
            latest_x = x_valid.iloc[-1]
            group1_mask = x_valid > latest_x
            group2_mask = group1_mask.shift(1, fill_value=False)

        # Annotate group points on both series with distinct marker styles
        if group1_mask.any():
            pos = np.where(group1_mask.values)[0]
            # Solid dots for Group 1
            ax.scatter(pos, x_valid[group1_mask].values, c=COLOR_OSC, s=16, marker='o', zorder=5)
            ax.scatter(pos, y_valid[group1_mask].values, c=COLOR_RET, s=16, marker='o', zorder=5)
        if group2_mask.any():
            pos2 = np.where(group2_mask.values)[0]
            # Hollow squares for Group 2
            ax.scatter(pos2, x_valid[group2_mask].values, facecolors='none', edgecolors=COLOR_OSC, s=48, marker='s', linewidth=1.5, zorder=5)
            ax.scatter(pos2, y_valid[group2_mask].values, facecolors='none', edgecolors=COLOR_RET, s=48, marker='s', linewidth=1.5, zorder=5)

        # Labels, ticks, and grid
        ax.set_xlabel('Time', fontsize=11)
        ax.set_ylabel('Percentage (%)', fontsize=11)

        # Map index ticks to date labels for readability
        try:
            tick_pos, tick_labels = self._build_date_ticks(x_valid.index, n, approx_ticks=n // 3 if n >= 9 else n)
            ax.set_xticks(tick_pos)
            ax.set_xticklabels(tick_labels, rotation=90, fontsize=9)
        except Exception:
            pass

        ax.grid(True, alpha=0.3)

        if n > 0:
            last_idx = t_idx[-1]
            last_x_val = x_valid.iloc[-1]
            last_y_val = y_valid.iloc[-1]

            ax.axhline(
                y=last_x_val, xmin=0, xmax=last_idx / len(t_idx),
                linestyle='--', color=COLOR_OSC, alpha=0.6,
            )
            ax.axhline(
                y=last_y_val, xmin=0, xmax=last_idx / len(t_idx),
                linestyle='--', color=COLOR_RET, alpha=0.6,
            )

        line_handles = [
            Line2D([0], [0], color=COLOR_OSC, lw=2, label=f'{x.name}'),
            Line2D([0], [0], color=COLOR_RET, lw=2, label=f'{y.name}'),
        ]
        group_handles = [
            Line2D([0], [0], marker='o', color='black', linestyle='None', markersize=7, label='Stronger Osc'),
            Line2D([0], [0], marker='s', markerfacecolor='none', markeredgecolor='black', linestyle='None', markersize=8, label='Next Step'),
        ]
        ax.legend(handles=line_handles + group_handles, loc='upper left', fontsize=9, framealpha=0.85)

        ax.set_title('Oscillation-Returns Dynamics', fontsize=13, fontweight='bold')
        plt.tight_layout()
        return fig

    def _create_spread_dynamics_bar_plot(self, spread_series: pd.Series):
        """Create the spread dynamics bar chart: spread = Oscillation - Returns, aligned by index."""
        fig, ax = plt.subplots(figsize=PLOT_SIZE_SPREAD)
        spread = spread_series.dropna()
        n = len(spread)
        if n == 0:
            ax.text(0.5, 0.5, 'No data', transform=ax.transAxes, ha='center', va='center')
            ax.axis('off')
            return fig
        t_idx = np.arange(n)
        colors = np.where(spread.values >= 0, COLOR_OSC, COLOR_RET)  # blue for >=0, orange for <0
        ax.bar(t_idx, spread.values, color=colors, width=0.8, alpha=0.9, edgecolor='black', linewidth=0.3)
        ax.axhline(0, color='black', linewidth=1)
        ax.set_xlabel('Index', fontsize=11)
        ax.set_ylabel('Spread (%)', fontsize=11)
        # Ticks -> map to dates at regular intervals for readability
        try:
            tick_pos, tick_labels = self._build_date_ticks(spread.index, n, approx_ticks=20)
            ax.set_xticks(tick_pos)
            ax.set_xticklabels(tick_labels, rotation=90, fontsize=9)
        except Exception:
            pass
        ax.grid(True, axis='y', alpha=0.3)
        ax.set_title('Oscillation-Returns Spread Dynamics', fontsize=13, fontweight='bold')
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
                f'Current: Osc={latest_oscillation:.1f}%, Ret={latest_return:.1f}%'
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

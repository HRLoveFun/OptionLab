"""
Market Analyzer - Core business logic for market analysis
"""
from core.price_dynamic import PriceDynamic
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import logging
import datetime as dt
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    High-level market analysis using PriceDynamic for calculations and visualization.
    """

    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='W'):
        self.price_dynamic = PriceDynamic(ticker, start_date, frequency)
        self.ticker = ticker
        self.frequency = frequency
        if self.price_dynamic.is_valid():
            self._calculate_features()

    def _calculate_features(self):
        try:
            self.oscillation = self.price_dynamic.osc(on_effect=True)
            self.returns = self.price_dynamic.ret()
            self.difference = self.price_dynamic.dif()
            self.features_df = pd.DataFrame({
                'Oscillation': self.oscillation,
                'Returns': self.returns,
                'Difference': self.difference
            }).dropna()
        except Exception as e:
            logger.error(f"Error calculating features: {e}")
            self.features_df = pd.DataFrame()

    def is_data_valid(self):
        """Check if analyzer has valid data"""
        return self.price_dynamic.is_valid()

    def generate_scatter_plot(self, feature_name):
        """Generate scatter plot with histograms"""
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return None
        try:
            feature_data = self.features_df[feature_name]
            returns_data = self.features_df['Returns']
            fig = self._create_scatter_hist_plot(feature_data, returns_data)
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating scatter plot: {e}")
            return None

    def generate_oscillation_projection(self, percentile=0.90, target_bias=None):
        """Generate oscillation projection plot with enhanced bias handling"""
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
                .round(2)
                .to_html(classes='table table-striped table-sm', index=True, escape=False)
            )
            return chart_base64, projection_table
        except Exception as e:
            logger.error(f"Error creating oscillation projection plot: {e}")
            return None, None

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
        fig, ax = plt.subplots(figsize=(16, 10))
        try:
            x_values = np.arange(len(proj_df.index))
            self._plot_projection_points(ax, x_values, proj_df)
            self._add_embedded_values_table(ax, proj_df)
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
                      label="Close", color="black", s=80, marker='o', zorder=3)
        
        # Plot High values with purple upward triangle points
        high_mask = ~proj_df["High"].isna()
        if high_mask.any():
            ax.scatter(x_values[high_mask], proj_df["High"][high_mask], 
                      label="High", color="purple", s=80, marker='^', zorder=3)
        
        # Plot Low values with blue downward triangle points
        low_mask = ~proj_df["Low"].isna()
        if low_mask.any():
            ax.scatter(x_values[low_mask], proj_df["Low"][low_mask], 
                      label="Low", color="blue", s=80, marker='v', zorder=3)
        
        # Plot projection lines
        for col, color, label in [("iHigh", "red", "Proj High (Current)"), ("iLow", "red", "Proj Low (Current)"), ("iHigh1", "orange", "Proj High (Next)"), ("iLow1", "orange", "Proj Low (Next)")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], label=label, 
                          facecolors='none', edgecolors=color, s=80, linewidth=2, zorder=3)

    def _add_embedded_values_table(self, ax, proj_df):
        """Add a table in the bottom-right corner showing historical oscillation analysis"""
        try:
            # Get the latest oscillation value for comparison
            if not hasattr(self, 'oscillation') or self.oscillation is None or self.oscillation.empty:
                logger.warning("No oscillation data available for table generation")
                return
            
            latest_oscillation = self.oscillation.iloc[-1]
            
            # Filter historical data where oscillation >= latest oscillation
            qualifying_mask = self.oscillation >= latest_oscillation
            qualifying_oscillations = self.oscillation[qualifying_mask]
            
            # Get corresponding returns for qualifying data points
            if not hasattr(self, 'returns') or self.returns is None or self.returns.empty:
                logger.warning("No returns data available for table generation")
                return
                
            # Align oscillation and returns data by index
            aligned_data = pd.DataFrame({
                'oscillation': self.oscillation,
                'returns': self.returns
            }).dropna()
            
            if aligned_data.empty:
                logger.warning("No aligned oscillation and returns data available")
                return
            
            # Filter for qualifying data points
            qualifying_data = aligned_data[aligned_data['oscillation'] >= latest_oscillation]
            
            if qualifying_data.empty:
                logger.warning("No qualifying data points found")
                return
            
            # Calculate metrics
            counts = len(qualifying_data)
            total_points = len(aligned_data)
            frequency = (counts / total_points) * 100 if total_points > 0 else 0
            median_returns = qualifying_data['returns'].median()
            
            # Create table data
            table_data = [
                ["Counts", f"{counts}"],
                ["Frequency", f"{frequency:.1f}%"],
                ["Median of Returns", f"{median_returns:.2f}%"]
            ]
            
            # Create table in bottom-right corner
            table = ax.table(
                cellText=table_data,
                colLabels=["Metric", "Value"],
                cellLoc='left',
                loc='lower right',
                bbox=[0.70, 0.02, 0.28, 0.25]  # [x, y, width, height] in axes coordinates
            )
            
            # Style the table
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.2)
            
            # Style header
            for i in range(2):
                table[(0, i)].set_facecolor('#E6E6FA')
                table[(0, i)].set_text_props(weight='bold')
            
            # Style data cells
            for i in range(1, len(table_data) + 1):
                table[(i, 0)].set_facecolor('#F8F8FF')
                table[(i, 1)].set_facecolor('#FFFFFF')
                table[(i, 1)].set_text_props(weight='bold', color='#333333')
            
            # Add border
            for key, cell in table.get_celld().items():
                cell.set_linewidth(1)
                cell.set_edgecolor('#CCCCCC')
            
            # Add a subtitle to clarify what the table shows
            ax.text(0.84, 0.30, f'Historical Analysis\n(Oscillation ≥ {latest_oscillation:.1f}%)', 
                   transform=ax.transAxes, fontsize=8, ha='center', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgray', alpha=0.7))
                    
        except Exception as e:
            logger.error(f"Error adding oscillation analysis table: {e}")

    def _create_projection_table(self, proj_df):
        """Create a table with projection values"""
        try:
            # Get the last few historical points and all projection points
            table_data = []
            
            # Add historical data (last 5 points)
            historical_data = proj_df[["Close", "High", "Low"]].dropna()
            if len(historical_data) > 0:
                last_historical = historical_data.tail(5)
                for date, row in last_historical.iterrows():
                    table_data.append({
                        'Date': date.strftime('%m/%d'),
                        'Type': 'Historical',
                        'Close': f"{row['Close']:.2f}" if pd.notna(row['Close']) else "-",
                        'High': f"{row['High']:.2f}" if pd.notna(row['High']) else "-",
                        'Low': f"{row['Low']:.2f}" if pd.notna(row['Low']) else "-",
                        'Proj_High_Cur': "-",
                        'Proj_Low_Cur': "-",
                        'Proj_High_Next': "-",
                        'Proj_Low_Next': "-"
                    })
            
            # Add projection data
            projection_cols = ["iHigh", "iLow", "iHigh1", "iLow1"]
            projection_data = proj_df[projection_cols].dropna(how='all')
            
            for date, row in projection_data.iterrows():
                table_data.append({
                    'Date': date.strftime('%m/%d'),
                    'Type': 'Projection',
                    'Close': "-",
                    'High': "-",
                    'Low': "-",
                    'Proj_High_Cur': f"{row['iHigh']:.2f}" if pd.notna(row['iHigh']) else "-",
                    'Proj_Low_Cur': f"{row['iLow']:.2f}" if pd.notna(row['iLow']) else "-",
                    'Proj_High_Next': f"{row['iHigh1']:.2f}" if pd.notna(row['iHigh1']) else "-",
                    'Proj_Low_Next': f"{row['iLow1']:.2f}" if pd.notna(row['iLow1']) else "-"
                })

            # Create DataFrame and convert to HTML
            if table_data:
                table_df = pd.DataFrame(table_data)
                return table_df.to_html(classes='table table-striped table-sm', 
                                      index=False, escape=False)
            return None
            
        except Exception as e:
            logger.error(f"Error creating projection table: {e}")
            return None

    def _format_projection_plot(self, ax, proj_df, percentile, proj_volatility, bias_text):
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

    def calculate_tail_statistics(self, feature_name):
        """Calculate tail statistics for different periods"""
        try:
            segments = self.get_period_segments(feature_name)
            if not segments:
                return None
            stats_index = ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th"]
            stats_df = pd.DataFrame(index=stats_index)
            for period_name, data in segments.items():
                if len(data) > 0:
                    stats_df[period_name] = [
                        data.mean(),
                        data.std(),
                        data.skew(),
                        data.kurtosis(),
                        data.max(),
                        data.quantile(0.99),
                        data.quantile(0.95),
                        data.quantile(0.90)
                    ]
            return stats_df.round(2)
        except Exception as e:
            logger.error(f"Error calculating tail statistics: {e}")
            return None
        
    def get_period_segments(self, feature_name, periods=None):
        if periods is None:
            periods = [12, 36, 60, "ALL"]
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return {}
        feature_data = self.features_df[feature_name]
        return self._create_period_segments(feature_data, periods)

    def _create_period_segments(self, data, periods):
        if data is None or data.empty:
            return {}
        last_date = data.index[-1]
        segments = {}
        for period in periods:
            try:
                if isinstance(period, int):
                    start_date = last_date - pd.DateOffset(months=period)
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    segments[col_name] = data.loc[data.index >= start_date]
                elif period == "ALL":
                    start_date = data.index[0]
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    segments[col_name] = data
            except Exception as e:
                logger.error(f"Error creating segment for period {period}: {e}")
        return segments

    def generate_tail_plot(self, feature_name):
        segments = self.get_period_segments(feature_name)
        if not segments:
            return None
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            colors = plt.cm.Set1(np.linspace(0, 1, len(segments)))
            for (period_name, data), color in zip(segments.items(), colors):
                if len(data) > 0:
                    sorted_data = np.sort(data)
                    y_vals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
                    ax.plot(sorted_data, y_vals, label=period_name, linewidth=2, color=color)
            
            for percentile in [0.9, 0.95, 0.99]:
                ax.axhline(y=percentile, color='gray', linestyle='--', alpha=0.7)
                ax.text(ax.get_xlim()[1], percentile, f'{percentile*100:.0f}th', 
                        ha='left', va='center', color='gray', fontweight='bold')
            ax.set_xlabel(f'{feature_name} (%)', fontsize=12)
            ax.set_ylabel('Cumulative Probability', fontsize=12)
            ax.set_title(f'{feature_name} Cumulative Distribution', fontsize=14, fontweight='bold')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating tail plot: {e}")
            return None

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
            fig, ax1 = plt.subplots(figsize=(16, 10))
            ax1.set_xlabel('Date', fontsize=12)
            ax1.set_ylabel('Price ($)', fontsize=12, color='black')
            
            # Plot price data with bull/bear segments
            for segment in bull_bear_segments['bull_segments']:
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color='green', linewidth=2, alpha=0.5)
            for segment in bull_bear_segments['bear_segments']:
                if len(segment) > 1:
                    ax1.plot(segment.index, segment.values, color='red', linewidth=2, alpha=0.5)
            
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.grid(True, alpha=0.3)
            
            # Create second y-axis for volatility
            ax2 = ax1.twinx()
            ax2.set_ylabel('Volatility (%)', fontsize=12, color='blue')
            ax2.plot(volatility.index, volatility.values, color='orange', linewidth=3, alpha=0.7, label='Historical Volatility', linestyle='-')
            ax2.tick_params(axis='y', labelcolor='blue')
            
            # Add current volatility point
            current_vol = volatility.iloc[-1] if len(volatility) > 0 else volatility.mean()
            ax2.scatter(x=volatility.index[-1], y=current_vol, color='purple', s=100, marker='o', linewidth=1.5, alpha=0.8, zorder=5)
            
            # Set title and legend
            frequency_mapping = {'D':'Daily','W':'Weekly','ME':'Monthly','QE':'Quarterly'}
            volatility_windows = {'D':5,'W':5,'ME':21,'QE':63}
            frequency_name = frequency_mapping.get(self.frequency, self.frequency)
            window = volatility_windows.get(self.frequency, 21)
            ax1.set_title(f'{self.ticker} - Price & Volatility Dynamics\nVolatility Window: {window} days ({frequency_name} frequency)', fontsize=14, fontweight='bold', pad=20)
            
            # Create legend
            from matplotlib.lines import Line2D
            legend_elements = [
                Line2D([0], [0], color='green', linewidth=2, label='Bull Market'),
                Line2D([0], [0], color='red', linewidth=2, label='Bear Market'),
                Line2D([0], [0], color='orange', linewidth=2, label='Volatility'),
                Line2D([0], [0], color='orange', linestyle='--', linewidth=2, label=f'Current Vol: {current_vol:.1f}%'),
            ]
            ax1.legend(handles=legend_elements, loc='upper left', fontsize=10, framealpha=0.8, bbox_to_anchor=(0.0, 1.0), borderaxespad=0.1)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
        except Exception as e:
            logger.error(f"Error generating volatility dynamics: {e}")
            return None

    def calculate_gap_statistics(self, frequency):
        if not self.is_data_valid():
            return None, None
        try:
            data = self.price_dynamic._data.copy()
            if "PeriodGap" not in data.columns and "LastClose" in data.columns:
                data["PeriodGap"] = data["Open"] / data["LastClose"] - 1
            if "PeriodGap" not in data.columns:
                return None
            return self._calculate_period_gap_stats(data, frequency)
        except Exception as e:
            logger.error(f"Error calculating gap statistics: {e}")
            return None

    def _calculate_period_gap_stats(self, df, frequency):
        try:
            periods = [12, 36, 60, "ALL"]
            data_sources = self._create_data_sources_for_gaps(df, periods, frequency)
            stats_index = ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th", "10th", "05th", "01st", "min", "p-value"]
            gap_stats_df = pd.DataFrame(index=stats_index)
            for period_name, data in data_sources.items():
                if len(data) > 0:
                    gap_return = data["PeriodGap"]
                    period_return = (data["Close"] / data["LastClose"] - 1)
                    try:
                        _, p_value = ks_2samp(gap_return, period_return)
                    except:
                        p_value = np.nan
                    gap_stats_df[period_name] = [
                        gap_return.mean(),
                        gap_return.std(),
                        gap_return.skew(),
                        gap_return.kurtosis(),
                        gap_return.max(),
                        gap_return.quantile(0.99),
                        gap_return.quantile(0.95),
                        gap_return.quantile(0.90),
                        gap_return.quantile(0.10),
                        gap_return.quantile(0.05),
                        gap_return.quantile(0.01),
                        gap_return.min(),
                        p_value
                    ]
            return gap_stats_df
        except Exception as e:
            logger.error(f"Error in gap statistics calculation: {e}")
            return None

    def _create_data_sources_for_gaps(self, df, periods, frequency):
        current_date = pd.Timestamp.now()
        if frequency == 'ME':
            end_date = current_date.replace(day=1)
        elif frequency == 'W':
            end_date = current_date - pd.DateOffset(days=current_date.weekday())
        elif frequency == 'QE':
            end_date = current_date - pd.tseries.offsets.QuarterBegin()
        else:
            end_date = current_date
        df_filtered = df[df.index < end_date]
        if df_filtered.empty:
            return {}
        last_date = df_filtered.index[-1]
        data_sources = {}
        for period in periods:
            try:
                if isinstance(period, int):
                    start_date = last_date - pd.DateOffset(months=period)
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    data_sources[col_name] = df_filtered.loc[df_filtered.index >= start_date]
                elif period == "ALL":
                    start_date = df_filtered.index[0]
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    data_sources[col_name] = df_filtered
            except Exception as e:
                logger.error(f"Error creating data source for period {period}: {e}")
        return data_sources

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
            fig, ax = plt.subplots(figsize=(12, 8))
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
        """Create scatter plot with marginal histograms"""
        import matplotlib
        matplotlib.use('Agg')  # 强制使用非GUI后端，防止多线程/服务器环境崩溃
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(10, 8))
        gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                              left=0.1, right=0.9, bottom=0.1, top=0.9,
                              wspace=0.05, hspace=0.05)
        ax = fig.add_subplot(gs[1, 0])
        ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
        ax_histx.tick_params(axis="x", labelbottom=False)
        ax_histy.tick_params(axis="y", labelleft=False)
        ax.scatter(x, y, alpha=0.6, s=30)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.plot(xlim, [0, 0], 'k--', alpha=0.5, linewidth=1)
        ax.plot([0, 0], ylim, 'k--', alpha=0.5, linewidth=1)
        
        # Label the five points with largest oscillation
        if len(x) >= 5:
            largest_osc_indices = x.nlargest(5).index
            for idx in largest_osc_indices:
                ax.annotate(f'{idx.strftime("%y%b")}', 
                           xy=(x.loc[idx], y.loc[idx]), 
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='red', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # Label the five most recent points
        if len(x) >= 5:
            recent_indices = x.index[-5:]
            for idx in recent_indices:
                ax.annotate(f'{idx.strftime("%y%b")}', 
                           xy=(x.loc[idx], y.loc[idx]), 
                           xytext=(-5, -15), textcoords='offset points',
                           fontsize=8, color='blue', fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightblue', alpha=0.7))
        
        if len(x) > 0 and len(y) > 0:
            ax.scatter(x.iloc[-1], y.iloc[-1], color='red', s=100, zorder=5, edgecolors='darkred', linewidth=2)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel(f'{x.name} (%)', fontsize=12)
        ax.set_ylabel(f'{y.name} (%)', fontsize=12)
        ax_histx.hist(x, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax_histy.hist(y, bins=30, alpha=0.7, color='lightcoral', orientation='horizontal', edgecolor='black')
        fig.suptitle(f'{x.name} vs {y.name} Analysis', fontsize=14, fontweight='bold')
        return fig

    def _fig_to_base64(self, fig):
        """Convert matplotlib figure to base64 string"""
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plot_url = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)
        return plot_url

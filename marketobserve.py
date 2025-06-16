import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import base64
import numpy as np
import seaborn as sns
import datetime as dt
from matplotlib.ticker import PercentFormatter, MultipleLocator
from scipy.stats import ks_2samp, percentileofscore, norm
import logging

# Configure matplotlib and seaborn
plt.style.use('default')
sns.set_palette("husl")

# Configure logging
logger = logging.getLogger(__name__)

# Constants
PERIODS = [12, 36, 60, "ALL"]
FREQUENCY_MAPPING = {
    'D': 'Daily',
    'W': 'Weekly', 
    'ME': 'Monthly',
    'QE': 'Quarterly'
}

class PriceDynamic:
    """
    A class to handle price data downloading, processing, and basic calculations.
    """
    
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), end_date=None, frequency='D'):
        """
        Initialize the PriceDynamic class.

        Args:
            ticker: Stock ticker symbol
            start_date: The first date the record starts
            end_date: The last date the record ends (default: today)
            frequency: Sampling frequency ('D', 'W', 'ME', 'QE')
        """
        self._validate_inputs(ticker, start_date, end_date, frequency)
        
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date or dt.date.today()
        self.frequency = frequency
        
        # Download and process data
        raw_data = self._download_data()
        self._data = self._refrequency(raw_data) if raw_data is not None else None

    def _validate_inputs(self, ticker, start_date, end_date, frequency):
        """Validate input parameters"""
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Ticker must be a non-empty string")
        
        if not isinstance(start_date, dt.date):
            raise ValueError("start_date must be a datetime.date object")
        
        if end_date and not isinstance(end_date, dt.date):
            raise ValueError("end_date must be a datetime.date object")
        
        if frequency not in ['D', 'W', 'ME', 'QE']:
            raise ValueError("frequency must be one of ['D', 'W', 'ME', 'QE']")

    def __getattr__(self, attr):
        """Delegate attribute access to _data if available"""
        if self._data is not None and hasattr(self._data, attr):
            return getattr(self._data, attr)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def __getitem__(self, item):
        """Support indexing operations"""
        if self._data is not None:
            return self._data[item]
        raise KeyError(f"No data available for key: {item}")

    def _download_data(self):
        """Download stock data from Yahoo Finance"""
        try:
            df = yf.download(
                self.ticker,
                start=self.start_date,
                end=self.end_date + dt.timedelta(days=1),  # Include end date
                interval='1d',
                progress=False,
                auto_adjust=False,
            )
            
            if df.empty:
                logger.warning(f"No data downloaded for {self.ticker}")
                return None
            
            # Handle MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            # Ensure datetime index
            df.index = pd.DatetimeIndex(df.index)
            
            # Select required columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing columns: {missing_columns}")
                return None
            
            return df[required_columns]
            
        except Exception as e:
            logger.error(f"Error downloading data for {self.ticker}: {e}")
            return None

    def _refrequency(self, df):
        """Resample data to specified frequency"""
        if df is None or df.empty:
            return None
        
        try:
            if self.frequency == 'D':
                df['LastClose'] = df["Close"].shift(1)
                return df
            
            # Resample for other frequencies
            resampled = df.resample(self.frequency).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Adj Close': 'last',
                'Volume': 'sum'
            }).dropna()
            
            # Add derived columns
            resampled['LastClose'] = resampled["Close"].shift(1)
            
            # Add date tracking columns for non-daily frequencies
            if self.frequency != 'D':
                date_agg = df.resample(self.frequency).agg({
                    'Open': lambda x: x.index[0] if len(x) > 0 else pd.NaT,
                    'High': lambda x: x.index[x.argmax()] if len(x) > 0 else pd.NaT,
                    'Low': lambda x: x.index[x.argmin()] if len(x) > 0 else pd.NaT,
                    'Close': lambda x: x.index[-1] if len(x) > 0 else pd.NaT
                })
                
                resampled['OpenDate'] = date_agg['Open']
                resampled['HighDate'] = date_agg['High']
                resampled['LowDate'] = date_agg['Low']
                resampled['CloseDate'] = date_agg['Close']
            
            return resampled
            
        except Exception as e:
            logger.error(f"Error resampling data: {e}")
            return None

    def osc(self, on_effect=False):
        """
        Calculate price oscillation.
        
        Args:
            on_effect: Include overnight effect (gap between open and last close)
            
        Returns:
            Series containing oscillation data as percentage
        """
        if self._data is None or self._data.empty:
            return None
        
        try:
            if on_effect:
                # Include overnight gap effect
                high_adj = np.maximum(self._data["High"], self._data["LastClose"])
                low_adj = np.minimum(self._data["Low"], self._data["LastClose"])
                osc_data = (high_adj - low_adj) / self._data['LastClose'] * 100
            else:
                # Simple high-low oscillation
                osc_data = (self._data["High"] - self._data["Low"]) / self._data['LastClose'] * 100
            
            osc_data.name = 'Oscillation'
            return osc_data.dropna()
            
        except Exception as e:
            logger.error(f"Error calculating oscillation: {e}")
            return None

    def ret(self):
        """Calculate price returns as percentage"""
        if self._data is None or self._data.empty:
            return None
        
        try:
            ret_data = ((self._data["Close"] - self._data['LastClose']) / self._data['LastClose']) * 100
            ret_data.name = 'Returns'
            return ret_data.dropna()
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return None

    def dif(self):
        """Calculate price difference in absolute terms"""
        if self._data is None or self._data.empty:
            return None
        
        try:
            dif_data = self._data["Close"] - self._data['LastClose']
            dif_data.name = 'Difference'
            return dif_data.dropna()
        except Exception as e:
            logger.error(f"Error calculating difference: {e}")
            return None

    def is_valid(self):
        """Check if data is valid and available"""
        return self._data is not None and not self._data.empty

    def get_current_price(self):
        """Get the most recent closing price"""
        if self.is_valid():
            return self._data["Close"].iloc[-1]
        return None


class MarketAnalyzer:
    """
    High-level market analysis class that uses PriceDynamic for comprehensive analysis.
    """
    
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), end_date=None, frequency='W'):
        """Initialize MarketAnalyzer with PriceDynamic instance"""
        self.price_dynamic = PriceDynamic(ticker, start_date, end_date, frequency)
        self.ticker = ticker
        self.frequency = frequency
        
        # Calculate derived features if data is available
        if self.price_dynamic.is_valid():
            self._calculate_features()

    def _calculate_features(self):
        """Calculate all derived features"""
        try:
            self.oscillation = self.price_dynamic.osc(on_effect=True)
            self.returns = self.price_dynamic.ret()
            self.difference = self.price_dynamic.dif()
            
            # Create combined features DataFrame
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

    def get_period_segments(self, feature_name, periods=PERIODS):
        """Create period segments for analysis"""
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return {}
        
        feature_data = self.features_df[feature_name]
        return self._create_period_segments(feature_data, periods)

    def _create_period_segments(self, data, periods):
        """Create data segments for different time periods"""
        if data is None or data.empty:
            return {}

        last_date = data.index[-1]
        segments = {}
        
        for period in periods:
            try:
                if isinstance(period, int):
                    start_date = last_date - pd.DateOffset(months=period)
                    start_date = pd.Timestamp(start_date)
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    segments[col_name] = data.loc[data.index >= start_date]
                elif period == "ALL":
                    start_date = data.index[0]
                    col_name = f"{start_date.strftime('%y%b')}-{last_date.strftime('%y%b')}"
                    segments[col_name] = data
                else:
                    logger.warning(f"Invalid period value: {period}")
            except Exception as e:
                logger.error(f"Error creating segment for period {period}: {e}")
        
        return segments

    def generate_market_statistics(self):
        """Generate comprehensive market statistics"""
        if not self.is_data_valid():
            return None
        
        try:
            data = self.price_dynamic._data
            current_data = data.iloc[-1]
            
            # Last OHLC
            last_ohlc = {
                'Open': current_data['Open'],
                'High': current_data['High'],
                'Low': current_data['Low'],
                'Close': current_data['Close']
            }
            
            # Frequency-to-date statistics
            freq_stats = self._calculate_frequency_stats()
            
            # Feature percentile analysis
            feature_percentiles = self._calculate_feature_percentiles()
            
            # Combine all statistics
            stats_df = pd.DataFrame({
                'Last OHLC': pd.Series(last_ohlc),
                'Frequency Stats': freq_stats,
                'Feature Percentiles': feature_percentiles
            })
            
            return stats_df.round(4)
            
        except Exception as e:
            logger.error(f"Error generating market statistics: {e}")
            return None

    def _calculate_frequency_stats(self):
        """Calculate frequency-to-date statistics"""
        try:
            data = self.price_dynamic._data
            if len(data) < 2:
                return pd.Series()
            
            # Get current period data
            current_period_data = data.tail(min(len(data), 20))  # Last 20 periods or all available
            
            return pd.Series({
                'Period High': current_period_data['High'].max(),
                'Period Low': current_period_data['Low'].min(),
                'Period Range': (current_period_data['High'].max() - current_period_data['Low'].min()) / current_period_data['Close'].iloc[-1] * 100,
                'Avg Volume': current_period_data['Volume'].mean()
            })
            
        except Exception as e:
            logger.error(f"Error calculating frequency stats: {e}")
            return pd.Series()

    def _calculate_feature_percentiles(self):
        """Calculate feature percentile analysis"""
        try:
            if 'Oscillation' not in self.features_df.columns:
                return pd.Series()
            
            oscillation_data = self.features_df['Oscillation']
            current_osc = oscillation_data.iloc[-1]
            
            return pd.Series({
                'Current Oscillation': current_osc,
                'Oscillation Percentile': percentileofscore(oscillation_data, current_osc),
                'Mean Oscillation': oscillation_data.mean(),
                'Std Oscillation': oscillation_data.std()
            })
            
        except Exception as e:
            logger.error(f"Error calculating feature percentiles: {e}")
            return pd.Series()

    def generate_volatility_dynamics(self, frequency):
        """Generate volatility dynamics plot with frequency-matched rolling periods"""
        if not self.is_data_valid():
            return None
        
        try:
            oscillation_data = self.features_df['Oscillation']
            
            # Set rolling windows based on frequency
            if frequency == 'D':
                windows = [20, 60, 120]  # Daily: ~1 month, 3 months, 6 months
            elif frequency == 'W':
                windows = [4, 12, 26]    # Weekly: ~1 month, 3 months, 6 months
            elif frequency == 'ME':
                windows = [3, 6, 12]     # Monthly: 3, 6, 12 months
            else:  # QE
                windows = [2, 4, 8]      # Quarterly: 6 months, 1 year, 2 years
            
            fig, ax = plt.subplots(figsize=(14, 8))
            
            colors = ['blue', 'red', 'green']
            
            for i, window in enumerate(windows):
                if len(oscillation_data) > window:
                    rolling_vol = oscillation_data.rolling(window=window).std()
                    ax.plot(rolling_vol.index, rolling_vol, 
                           label=f'{window}-Period Rolling Volatility', 
                           color=colors[i], linewidth=2, alpha=0.8)
            
            # Add current volatility level
            current_vol = oscillation_data.std()
            ax.axhline(y=current_vol, color='orange', linestyle='--', 
                      label=f'Overall Volatility: {current_vol:.2f}%', linewidth=2)
            
            # Formatting
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Volatility (%)', fontsize=12)
            ax.set_title(f'{self.ticker} - Volatility Dynamics Over Time ({FREQUENCY_MAPPING.get(frequency, frequency)})', 
                        fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error generating volatility dynamics: {e}")
            return None

    def generate_enhanced_scatter_plot(self, feature_name):
        """Generate enhanced scatter plot with auxiliary lines and annotations"""
        if not self.is_data_valid() or feature_name not in self.features_df.columns:
            return None
        
        try:
            feature_data = self.features_df[feature_name]
            returns_data = self.features_df['Returns']
            
            fig = self._create_enhanced_scatter_plot(feature_data, returns_data)
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error generating enhanced scatter plot: {e}")
            return None

    def _create_enhanced_scatter_plot(self, x, y):
        """Create enhanced scatter plot with auxiliary lines and percentile divisions"""
        fig = plt.figure(figsize=(12, 10))
        gs = fig.add_gridspec(2, 2, width_ratios=(4, 1), height_ratios=(1, 4),
                              left=0.1, right=0.9, bottom=0.1, top=0.9,
                              wspace=0.05, hspace=0.05)
        
        # Main scatter plot
        ax = fig.add_subplot(gs[1, 0])
        ax_histx = fig.add_subplot(gs[0, 0], sharex=ax)
        ax_histy = fig.add_subplot(gs[1, 1], sharey=ax)
        
        # Hide tick labels for histograms
        ax_histx.tick_params(axis="x", labelbottom=False)
        ax_histy.tick_params(axis="y", labelleft=False)
        
        # Scatter plot
        ax.scatter(x, y, alpha=0.6, s=30, c='blue')
        
        # Add auxiliary lines y=x and y=-x for x in [0, x.max]
        x_max = x.max()
        if x_max > 0:
            x_line = np.linspace(0, x_max, 100)
            ax.plot(x_line, x_line, 'r--', alpha=0.7, linewidth=2, label='y = x')
            ax.plot(x_line, -x_line, 'g--', alpha=0.7, linewidth=2, label='y = -x')
        
        # Reference lines at zero
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.plot(xlim, [0, 0], 'k--', alpha=0.5, linewidth=1)
        ax.plot([0, 0], ylim, 'k--', alpha=0.5, linewidth=1)
        
        # Add percentile division lines
        x_percentiles = [np.percentile(x, p) for p in [20, 40, 60, 80]]
        y_percentiles = [np.percentile(y, p) for p in [20, 40, 60, 80]]
        
        for perc in x_percentiles:
            ax.axvline(x=perc, color='gray', linestyle=':', alpha=0.5)
        
        for perc in y_percentiles:
            ax.axhline(y=perc, color='gray', linestyle=':', alpha=0.5)
        
        # Display indices of first 10 x-values
        if len(x) >= 10:
            first_10_indices = x.head(10).index
            for i, idx in enumerate(first_10_indices):
                ax.annotate(f'{i+1}', (x.loc[idx], y.loc[idx]), 
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='red', fontweight='bold')
        
        # Highlight recent point
        if len(x) > 0 and len(y) > 0:
            ax.scatter(x.iloc[-1], y.iloc[-1], color='red', s=100, zorder=5, 
                      edgecolors='darkred', linewidth=2, label='Latest')
        
        # Grid and labels
        ax.grid(True, alpha=0.3)
        ax.set_xlabel(f'{x.name} (%)', fontsize=12)
        ax.set_ylabel(f'{y.name} (%)', fontsize=12)
        ax.legend(fontsize=10)
        
        # Marginal histograms
        ax_histx.hist(x, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax_histy.hist(y, bins=30, alpha=0.7, color='lightcoral', 
                     orientation='horizontal', edgecolor='black')
        
        # Title
        fig.suptitle(f'{x.name} vs {y.name} Analysis (Enhanced)', fontsize=14, fontweight='bold')
        
        return fig

    def generate_enhanced_tail_plot(self, feature_name):
        """Generate enhanced tail distribution plot with y-axis range 0.8-1"""
        segments = self.get_period_segments(feature_name)
        if not segments:
            return None
        
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            colors = plt.cm.Set1(np.linspace(0, 1, len(segments)))
            
            for (period_name, data), color in zip(segments.items(), colors):
                if len(data) > 0:
                    # Create ECDF
                    sorted_data = np.sort(data)
                    y_vals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
                    ax.plot(sorted_data, y_vals, label=period_name, linewidth=2, color=color)
            
            # Set y-axis range to 0.8-1
            ax.set_ylim(0.8, 1.0)
            
            # Reference lines for high percentiles
            for percentile in [0.9, 0.95, 0.99]:
                if percentile >= 0.8:  # Only show lines within our y-range
                    ax.axhline(y=percentile, color='gray', linestyle='--', alpha=0.7)
                    ax.text(ax.get_xlim()[1], percentile, f'{percentile*100:.0f}th', 
                           ha='left', va='center', color='gray', fontweight='bold')
            
            ax.set_xlabel(f'{feature_name} (%)', fontsize=12)
            ax.set_ylabel('Cumulative Probability', fontsize=12)
            ax.set_title(f'{feature_name} Tail Distribution (80th-100th Percentile)', fontsize=14, fontweight='bold')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error generating enhanced tail plot: {e}")
            return None

    def calculate_tail_statistics(self, feature_name):
        """Calculate tail statistics for different periods"""
        segments = self.get_period_segments(feature_name)
        if not segments:
            return None
        
        try:
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

    def calculate_gap_statistics(self, frequency):
        """Calculate gap statistics if applicable"""
        if not self.is_data_valid():
            return None
        
        try:
            data = self.price_dynamic._data.copy()
            
            # Calculate period gap if not exists
            if "PeriodGap" not in data.columns and "LastClose" in data.columns:
                data["PeriodGap"] = data["Open"] / data["LastClose"] - 1
            
            if "PeriodGap" not in data.columns:
                return None
            
            return self._calculate_period_gap_stats(data, frequency)
            
        except Exception as e:
            logger.error(f"Error calculating gap statistics: {e}")
            return None

    def _calculate_period_gap_stats(self, df, frequency):
        """Calculate detailed gap statistics"""
        try:
            periods = [12, 36, 60, "ALL"]
            data_sources = self._create_data_sources_for_gaps(df, periods, frequency)
            
            stats_index = ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th", 
                          "10th", "05th", "01st", "min", "p-value"]
            gap_stats_df = pd.DataFrame(index=stats_index)
            
            for period_name, data in data_sources.items():
                if len(data) > 0:
                    gap_return = data["PeriodGap"]
                    period_return = (data["Close"] / data["LastClose"] - 1)
                    
                    # Statistical test
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
        """Create data sources for gap analysis"""
        current_date = pd.Timestamp.now()
        
        # Adjust end date based on frequency
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

    def generate_enhanced_oscillation_projection(self, percentile=0.90, target_bias=None):
        """Generate enhanced oscillation projection with improved accuracy"""
        if not self.is_data_valid():
            return None
        
        try:
            data = self.price_dynamic._data.copy()
            
            # Add oscillation data
            data['Oscillation'] = self.oscillation
            
            # Ensure required columns exist
            required_cols = ['High', 'Low', 'LastClose', 'Close', 'Oscillation']
            if not all(col in data.columns for col in required_cols):
                logger.error("Missing required columns for oscillation projection")
                return None
            
            return self._create_enhanced_oscillation_projection_plot(data, percentile, target_bias)
            
        except Exception as e:
            logger.error(f"Error generating enhanced oscillation projection: {e}")
            return None

    def _create_enhanced_oscillation_projection_plot(self, data, percentile, target_bias):
        """Create enhanced oscillation projection with improved accuracy"""
        try:
            # Calculate projection volatility
            proj_volatility = data["Oscillation"].quantile(percentile)
            
            # Get current price with higher accuracy
            current_price = data["Close"].iloc[-1]
            accuracy = max(1, current_price / 1000)  # 1 or one-thousandth of latest price, whichever is higher
            
            # Optimize projection weights
            if target_bias is None:
                proj_high_weight = self._calculate_enhanced_natural_bias_weight(data, proj_volatility)
            else:
                proj_high_weight = self._optimize_enhanced_projection_weight(data, proj_volatility, target_bias)
            
            # Get price data
            px_last_close = data["LastClose"].iloc[-1]
            px_last = current_price
            
            # Calculate projections with enhanced accuracy
            proj_high_cur = px_last_close + px_last_close * proj_volatility / 100 * proj_high_weight
            proj_low_cur = px_last_close - px_last_close * proj_volatility / 100 * (1 - proj_high_weight)
            proj_high_next = px_last + px_last * proj_volatility / 100 * proj_high_weight
            proj_low_next = px_last - px_last * proj_volatility / 100 * (1 - proj_high_weight)
            
            # Round to accuracy
            proj_high_cur = round(proj_high_cur / accuracy) * accuracy
            proj_low_cur = round(proj_low_cur / accuracy) * accuracy
            proj_high_next = round(proj_high_next / accuracy) * accuracy
            proj_low_next = round(proj_low_next / accuracy) * accuracy
            
            # Create projection DataFrame
            proj_df = self._create_enhanced_projection_dataframe(data, proj_high_cur, proj_low_cur, 
                                                               proj_high_next, proj_low_next)
            
            # Create visualization
            fig = self._plot_enhanced_oscillation_projection(proj_df, percentile, proj_volatility, 
                                                           target_bias, accuracy)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating enhanced oscillation projection plot: {e}")
            return None

    def _calculate_enhanced_natural_bias_weight(self, data, proj_volatility):
        """Calculate enhanced natural bias weight with better accuracy"""
        try:
            df = data.iloc[:-1].copy()
            
            # Test multiple weight scenarios with finer granularity
            weights = np.linspace(0.3, 0.7, 41)  # More granular testing
            best_weight = 0.5
            best_score = -float('inf')
            
            for weight in weights:
                df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * weight
                df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - weight)
                
                # Calculate comprehensive scoring
                within_range = ((df["Close"] >= df["ProjLow"]) & (df["Close"] <= df["ProjHigh"])).sum()
                accuracy_score = within_range / len(df)
                
                # Bias consistency score
                df["Status"] = np.where(df["Close"] > df["ProjHigh"], 1,
                                       np.where(df["Close"] < df["ProjLow"], -1, 0))
                bias_consistency = abs(df["Status"].mean())
                
                # Combined score (accuracy weighted more heavily)
                combined_score = accuracy_score * 0.7 + (1 - bias_consistency) * 0.3
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_weight = weight
            
            return best_weight
            
        except Exception as e:
            logger.error(f"Error calculating enhanced natural bias weight: {e}")
            return 0.5

    def _optimize_enhanced_projection_weight(self, data, proj_volatility, target_bias):
        """Optimize projection weight with enhanced precision"""
        try:
            weights = np.linspace(0.35, 0.65, 31)  # Finer granularity around neutral
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
            logger.error(f"Error optimizing enhanced projection weight: {e}")
            return 0.5

    def _calculate_realized_bias(self, data, proj_volatility, weight):
        """Calculate realized bias for given parameters"""
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

    def _create_enhanced_projection_dataframe(self, data, proj_high_cur, proj_low_cur, 
                                            proj_high_next, proj_low_next):
        """Create enhanced DataFrame for projection visualization"""
        try:
            # Get relevant dates
            close_dates = data.get("CloseDate")
            if isinstance(close_dates, pd.Series) and len(close_dates) >= 2:
                date_last_close = close_dates.iloc[-2]
                date_last = close_dates.iloc[-1]
            else:
                date_last_close = data.index[-2] if len(data) >= 2 else data.index[-1]
                date_last = data.index[-1]

            # Create extended date range for projection
            end_date = date_last + pd.DateOffset(months=3)  # Extended projection period
            all_weekdays = pd.date_range(start=date_last_close, end=end_date, freq='B')
            
            # Initialize projection DataFrame
            proj_df = pd.DataFrame(index=all_weekdays, 
                                 columns=["Close", "High", "Low", "iHigh", "iLow", "iHigh1", "iLow1"])
            
            # Fill known data points
            proj_df.loc[date_last_close, "Close"] = data["LastClose"].iloc[-1]
            proj_df.loc[date_last, "Close"] = data["Close"].iloc[-1]
            
            if 'HighDate' in data.columns and 'LowDate' in data.columns:
                proj_df.loc[data["HighDate"].iloc[-1], "High"] = data["High"].iloc[-1]
                proj_df.loc[data["LowDate"].iloc[-1], "Low"] = data["Low"].iloc[-1]
            
            # Calculate projection periods
            current_month_end = self._get_current_month_end(date_last)
            next_month_end = current_month_end + pd.DateOffset(months=1)
            
            # Fill projection data with enhanced smoothing
            self._fill_enhanced_projection_data(proj_df, date_last_close, current_month_end, 
                                              proj_high_cur, proj_low_cur, "iHigh", "iLow")
            
            self._fill_enhanced_projection_data(proj_df, date_last, next_month_end, 
                                              proj_high_next, proj_low_next, "iHigh1", "iLow1")
            
            return proj_df
            
        except Exception as e:
            logger.error(f"Error creating enhanced projection DataFrame: {e}")
            return pd.DataFrame()

    def _get_current_month_end(self, date_last):
        """Get the end of current month"""
        if date_last.month < 12:
            return dt.datetime(date_last.year, date_last.month + 1, 1) - pd.Timedelta(days=1)
        else:
            return dt.datetime(date_last.year + 1, 1, 1) - pd.Timedelta(days=1)

    def _fill_enhanced_projection_data(self, proj_df, start_date, end_date, proj_high, proj_low, 
                                     high_col, low_col):
        """Fill projection data with enhanced smoothing"""
        try:
            weekdays = pd.date_range(start=start_date, end=end_date, freq='B')[1:]
            start_price = proj_df.loc[start_date, "Close"]
            
            for i, date in enumerate(weekdays):
                if date in proj_df.index:
                    # Enhanced progression with S-curve for more realistic projection
                    t = (i + 1) / len(weekdays)
                    progress = 3 * t**2 - 2 * t**3  # S-curve progression
                    
                    proj_df.loc[date, high_col] = start_price + (proj_high - start_price) * progress
                    proj_df.loc[date, low_col] = start_price + (proj_low - start_price) * progress
                    
        except Exception as e:
            logger.error(f"Error filling enhanced projection data: {e}")

    def _plot_enhanced_oscillation_projection(self, proj_df, percentile, proj_volatility, 
                                            target_bias, accuracy):
        """Create enhanced oscillation projection plot"""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        try:
            x_values = np.arange(len(proj_df.index))
            
            # Plot data points with enhanced styling
            self._plot_enhanced_projection_points(ax, x_values, proj_df)
            
            # Add enhanced annotations
            self._add_enhanced_projection_annotations(ax, x_values, proj_df, accuracy)
            
            # Format plot with enhanced information
            bias_text = "Natural" if target_bias is None else f"Neutral ({target_bias})"
            self._format_enhanced_projection_plot(ax, proj_df, percentile, proj_volatility, 
                                                bias_text, accuracy)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error plotting enhanced oscillation projection: {e}")
            return fig

    def _plot_enhanced_projection_points(self, ax, x_values, proj_df):
        """Plot enhanced data points with better styling"""
        # Historical data with enhanced markers
        for col, color, label, marker in [("Close", "black", "Close", "o"), 
                                         ("High", "purple", "High", "^"), 
                                         ("Low", "purple", "Low", "v")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], 
                          label=label, color=color, s=100, zorder=3, marker=marker)
        
        # Projected data with enhanced hollow markers
        for col, color, label, marker in [("iHigh", "red", "Proj High (Current)", "^"), 
                                         ("iLow", "red", "Proj Low (Current)", "v"),
                                         ("iHigh1", "orange", "Proj High (Next)", "^"), 
                                         ("iLow1", "orange", "Proj Low (Next)", "v")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], 
                          label=label, facecolors='none', edgecolors=color, 
                          s=100, linewidth=2, zorder=3, marker=marker)

    def _add_enhanced_projection_annotations(self, ax, x_values, proj_df, accuracy):
        """Add enhanced value annotations with accuracy formatting"""
        # Format values based on accuracy
        def format_value(val):
            if accuracy >= 1:
                return f"{val:.0f}"
            elif accuracy >= 0.1:
                return f"{val:.1f}"
            else:
                return f"{val:.2f}"
        
        # Annotate actual values
        for col, color in [("Close", "black"), ("High", "purple"), ("Low", "purple")]:
            for i, (idx, val) in enumerate(proj_df[col].dropna().items()):
                x_pos = list(proj_df.index).index(idx)
                ax.annotate(format_value(val), (x_pos, val), 
                           xytext=(0, -25), textcoords="offset points",
                           ha='center', va='top', fontsize=10, color=color, 
                           fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", 
                                                       facecolor='white', alpha=0.8))
        
        # Annotate key projections
        for col, color in [("iHigh", "red"), ("iLow", "red"), ("iHigh1", "orange"), ("iLow1", "orange")]:
            data_points = proj_df[col].dropna()
            if len(data_points) >= 5:  # Show fewer annotations to avoid clutter
                for idx, val in data_points.iloc[::len(data_points)//3].items():
                    x_pos = list(proj_df.index).index(idx)
                    ax.annotate(format_value(val), (x_pos, val), 
                               xytext=(0, -25), textcoords="offset points",
                               ha='center', va='top', fontsize=9, color=color, 
                               fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", 
                                                           facecolor='white', alpha=0.7))

    def _format_enhanced_projection_plot(self, ax, proj_df, percentile, proj_volatility, 
                                       bias_text, accuracy):
        """Format enhanced projection plot with comprehensive information"""
        # Set x-axis labels with better spacing
        step = max(1, len(proj_df.index)//15)
        ax.set_xticks(range(0, len(proj_df.index), step))
        ax.set_xticklabels([proj_df.index[i].strftime('%m/%d') 
                           for i in range(0, len(proj_df.index), step)], 
                          rotation=45)
        
        # Enhanced labels and title
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Price', fontsize=12, fontweight='bold')
        
        # Multi-line title with comprehensive information
        title_lines = [
            f'Enhanced Oscillation Projection - {self.ticker}',
            f'Threshold: {percentile:.0%} | Volatility: {proj_volatility:.1f}% | Bias: {bias_text}',
            f'Accuracy: ±{accuracy:.3f}' if accuracy < 1 else f'Accuracy: ±{accuracy:.0f}'
        ]
        ax.set_title('\n'.join(title_lines), fontsize=14, fontweight='bold', pad=20)
        
        # Enhanced grid and legend
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.legend(fontsize=10, loc='upper left', bbox_to_anchor=(0, 1), 
                 frameon=True, fancybox=True, shadow=True)
        
        # Add projection statistics box
        stats_text = self._generate_projection_stats_text(proj_df, proj_volatility, bias_text)
        ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=9,
               verticalalignment='bottom', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()

    def _generate_projection_stats_text(self, proj_df, proj_volatility, bias_text):
        """Generate statistics text for projection plot"""
        try:
            current_price = proj_df["Close"].dropna().iloc[-1]
            
            # Get projection ranges
            high_projections = proj_df[["iHigh", "iHigh1"]].dropna()
            low_projections = proj_df[["iLow", "iLow1"]].dropna()
            
            if not high_projections.empty and not low_projections.empty:
                max_upside = high_projections.max().max() - current_price
                max_downside = current_price - low_projections.min().min()
                
                upside_pct = (max_upside / current_price) * 100
                downside_pct = (max_downside / current_price) * 100
                
                return f"Projection Stats:\nMax Upside: +{upside_pct:.1f}%\nMax Downside: -{downside_pct:.1f}%\nVolatility: {proj_volatility:.1f}%\nBias: {bias_text}"
            
            return f"Volatility: {proj_volatility:.1f}%\nBias: {bias_text}"
            
        except Exception as e:
            logger.error(f"Error generating projection stats: {e}")
            return f"Volatility: {proj_volatility:.1f}%\nBias: {bias_text}"

    def analyze_strategy(self, option_data):
        """Comprehensive strategy analysis with P&L, probability, and Kelly criterion"""
        if not option_data:
            return None
        
        try:
            current_price = self.price_dynamic.get_current_price()
            if current_price is None:
                return None
            
            # Calculate option matrix
            option_matrix = self._calculate_enhanced_option_matrix(current_price, option_data)
            
            # Generate comprehensive analysis
            pnl_chart = self._create_enhanced_pnl_chart(option_matrix, current_price)
            probability_chart = self._create_price_probability_chart(current_price)
            kelly_analysis = self._calculate_kelly_criterion(option_matrix, current_price)
            
            return {
                'pnl_chart': pnl_chart,
                'probability_chart': probability_chart,
                'kelly_analysis': kelly_analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strategy: {e}")
            return None

    def _calculate_enhanced_option_matrix(self, current_price, option_data):
        """Calculate enhanced option P&L matrix with finer granularity"""
        try:
            # Enhanced price range with finer granularity
            price_range = np.linspace(current_price * 0.6, current_price * 1.4, 801)
            
            # Initialize matrix
            matrix_df = pd.DataFrame(index=price_range)
            matrix_df['PnL'] = 0.0
            
            # Calculate P&L for each option
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
            logger.error(f"Error calculating enhanced option matrix: {e}")
            return None

    def _calculate_single_option_pnl(self, prices, option_type, strike, quantity, premium):
        """Calculate P&L for a single option"""
        if option_type == 'SC':  # Short Call
            return np.where(prices > strike, 
                           (premium - (prices - strike)) * quantity,
                           premium * quantity)
        elif option_type == 'SP':  # Short Put
            return np.where(prices < strike,
                           (premium - (strike - prices)) * quantity,
                           premium * quantity)
        elif option_type == 'LC':  # Long Call
            return np.where(prices > strike,
                           (prices - strike - premium) * quantity,
                           -premium * quantity)
        elif option_type == 'LP':  # Long Put
            return np.where(prices < strike,
                           (strike - prices - premium) * quantity,
                           -premium * quantity)
        else:
            return np.zeros_like(prices)

    def _create_enhanced_pnl_chart(self, matrix_df, current_price):
        """Create enhanced P&L visualization with comprehensive analysis"""
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), height_ratios=[3, 1])
            
            # Main P&L plot
            ax1.plot(matrix_df.index, matrix_df['PnL'], linewidth=3, color='blue')
            
            # Enhanced reference lines
            ax1.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
            ax1.axvline(x=current_price, color='red', linestyle='--', alpha=0.8, linewidth=2,
                       label=f'Current Price: ${current_price:.2f}')
            
            # Enhanced profit/loss areas
            ax1.fill_between(matrix_df.index, matrix_df['PnL'], 0, 
                           where=(matrix_df['PnL'] > 0), color='green', alpha=0.3, label='Profit Zone')
            ax1.fill_between(matrix_df.index, matrix_df['PnL'], 0, 
                           where=(matrix_df['PnL'] < 0), color='red', alpha=0.3, label='Loss Zone')
            
            # Breakeven points
            breakeven_points = self._find_enhanced_breakeven_points(matrix_df)
            for bp in breakeven_points:
                ax1.axvline(x=bp, color='orange', linestyle=':', alpha=0.8, linewidth=2)
                ax1.text(bp, ax1.get_ylim()[1] * 0.9, f'BE: ${bp:.2f}', 
                        rotation=90, ha='right', va='top', fontweight='bold')
            
            # Enhanced formatting for main plot
            ax1.set_ylabel('P&L ($)', fontsize=12, fontweight='bold')
            ax1.set_title('Strategy P&L Analysis', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend(fontsize=11)
            
            # Risk metrics subplot
            self._add_risk_metrics_subplot(ax2, matrix_df, current_price, breakeven_points)
            
            # Enhanced statistics
            max_profit = matrix_df['PnL'].max()
            max_loss = matrix_df['PnL'].min()
            
            stats_text = f'Max Profit: ${max_profit:.0f}\nMax Loss: ${max_loss:.0f}'
            if breakeven_points:
                be_text = ', '.join([f'${bp:.0f}' for bp in breakeven_points[:3]])  # Show first 3
                stats_text += f'\nBreakeven: {be_text}'
            
            ax1.text(0.02, 0.98, stats_text, transform=ax1.transAxes, fontsize=12,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating enhanced P&L chart: {e}")
            return None

    def _add_risk_metrics_subplot(self, ax, matrix_df, current_price, breakeven_points):
        """Add risk metrics visualization subplot"""
        try:
            # Calculate risk metrics across price range
            price_range = matrix_df.index.values
            pnl_values = matrix_df['PnL'].values
            
            # Risk-reward ratio calculation
            risk_reward_ratios = []
            for i, price in enumerate(price_range):
                if abs(price - current_price) > 0.01:  # Avoid division by zero
                    potential_profit = max(0, pnl_values[i])
                    potential_loss = abs(min(0, pnl_values[i]))
                    if potential_loss > 0:
                        ratio = potential_profit / potential_loss
                    else:
                        ratio = float('inf') if potential_profit > 0 else 0
                    risk_reward_ratios.append(min(ratio, 10))  # Cap at 10 for visualization
                else:
                    risk_reward_ratios.append(0)
            
            ax.plot(price_range, risk_reward_ratios, color='purple', linewidth=2, alpha=0.7)
            ax.set_xlabel('Stock Price ($)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Risk/Reward Ratio', fontsize=10)
            ax.set_title('Risk-Reward Profile', fontsize=12)
            ax.grid(True, alpha=0.3)
            ax.axvline(x=current_price, color='red', linestyle='--', alpha=0.5)
            
        except Exception as e:
            logger.error(f"Error adding risk metrics subplot: {e}")

    def _find_enhanced_breakeven_points(self, matrix_df):
        """Find enhanced breakeven points with better precision"""
        try:
            pnl_values = matrix_df['PnL'].values
            prices = matrix_df.index.values
            
            breakeven_points = []
            tolerance = abs(pnl_values).max() * 0.001  # 0.1% tolerance
            
            for i in range(len(pnl_values) - 1):
                if (pnl_values[i] <= tolerance and pnl_values[i + 1] >= -tolerance) or \
                   (pnl_values[i] >= -tolerance and pnl_values[i + 1] <= tolerance):
                    # Linear interpolation for precise breakeven
                    if abs(pnl_values[i + 1] - pnl_values[i]) > 1e-10:
                        breakeven_price = prices[i] - pnl_values[i] * (prices[i + 1] - prices[i]) / (pnl_values[i + 1] - pnl_values[i])
                        breakeven_points.append(breakeven_price)
            
            return sorted(list(set([round(bp, 2) for bp in breakeven_points])))  # Remove duplicates and round
            
        except Exception as e:
            logger.error(f"Error finding enhanced breakeven points: {e}")
            return []

    def _create_price_probability_chart(self, current_price):
        """Create price probability distribution chart"""
        try:
            if not self.is_data_valid() or 'Returns' not in self.features_df.columns:
                return None
            
            returns_data = self.features_df['Returns']
            
            # Calculate probability distribution parameters
            mean_return = returns_data.mean()
            std_return = returns_data.std()
            
            # Create price range
            price_range = np.linspace(current_price * 0.6, current_price * 1.4, 200)
            
            # Convert to return space and calculate probabilities
            returns_range = (price_range / current_price - 1) * 100
            probabilities = norm.pdf(returns_range, mean_return, std_return)
            
            # Normalize probabilities
            probabilities = probabilities / probabilities.sum()
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot probability distribution
            ax.plot(price_range, probabilities, linewidth=3, color='blue', label='Price Probability')
            ax.fill_between(price_range, probabilities, alpha=0.3, color='lightblue')
            
            # Add current price line
            ax.axvline(x=current_price, color='red', linestyle='--', linewidth=2,
                      label=f'Current Price: ${current_price:.2f}')
            
            # Add confidence intervals
            for confidence in [0.68, 0.95]:  # 1 and 2 standard deviations
                lower_price = current_price * (1 + (mean_return - confidence * std_return) / 100)
                upper_price = current_price * (1 + (mean_return + confidence * std_return) / 100)
                
                ax.axvspan(lower_price, upper_price, alpha=0.1, color='green',
                          label=f'{confidence*100:.0f}% Confidence Interval')
            
            # Formatting
            ax.set_xlabel('Stock Price ($)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Probability Density', fontsize=12, fontweight='bold')
            ax.set_title(f'Price Probability Distribution - {self.ticker}', fontsize=14, fontweight='bold')
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3)
            
            # Add statistics
            stats_text = f'Expected Return: {mean_return:.2f}%\nVolatility: {std_return:.2f}%'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=12,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating price probability chart: {e}")
            return None

    def _calculate_kelly_criterion(self, matrix_df, current_price):
        """Calculate Kelly criterion for optimal betting size"""
        try:
            if not self.is_data_valid() or 'Returns' not in self.features_df.columns:
                return pd.DataFrame()
            
            returns_data = self.features_df['Returns']
            
            # Calculate win probability and average win/loss
            positive_returns = returns_data[returns_data > 0]
            negative_returns = returns_data[returns_data < 0]
            
            win_prob = len(positive_returns) / len(returns_data)
            avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0
            avg_loss = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0
            
            # Calculate Kelly criterion for the strategy
            pnl_at_current = matrix_df.loc[matrix_df.index.get_indexer([current_price], method='nearest')[0], 'PnL']
            
            # Estimate strategy performance
            upside_scenarios = matrix_df[matrix_df['PnL'] > 0]
            downside_scenarios = matrix_df[matrix_df['PnL'] < 0]
            
            strategy_win_prob = len(upside_scenarios) / len(matrix_df) if len(matrix_df) > 0 else 0
            avg_strategy_win = upside_scenarios['PnL'].mean() if len(upside_scenarios) > 0 else 0
            avg_strategy_loss = abs(downside_scenarios['PnL'].mean()) if len(downside_scenarios) > 0 else 0
            
            # Kelly formula: f = (bp - q) / b, where b = odds, p = win prob, q = loss prob
            if avg_strategy_loss > 0:
                kelly_fraction = (strategy_win_prob * avg_strategy_win - (1 - strategy_win_prob) * avg_strategy_loss) / avg_strategy_loss
            else:
                kelly_fraction = 0
            
            # Cap Kelly fraction for practical purposes
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
            
            # Create analysis DataFrame
            kelly_df = pd.DataFrame({
                'Metric': ['Win Probability', 'Average Win', 'Average Loss', 'Kelly Fraction', 'Recommended Position Size'],
                'Market': [f'{win_prob:.1%}', f'{avg_win:.2f}%', f'{avg_loss:.2f}%', 'N/A', 'N/A'],
                'Strategy': [f'{strategy_win_prob:.1%}', f'${avg_strategy_win:.0f}', f'${avg_strategy_loss:.0f}', 
                           f'{kelly_fraction:.1%}', f'{kelly_fraction*100:.1f}% of capital']
            })
            
            return kelly_df
            
        except Exception as e:
            logger.error(f"Error calculating Kelly criterion: {e}")
            return pd.DataFrame()

    def _fig_to_base64(self, fig):
        """Convert matplotlib figure to base64 string"""
        try:
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plot_url = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close(fig)
            return plot_url
        except Exception as e:
            logger.error(f"Error converting figure to base64: {e}")
            plt.close(fig)
            return None


# Legacy functions for backward compatibility
def period_segment(df, periods=PERIODS):
    """Legacy function - use MarketAnalyzer instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    return analyzer._create_period_segments(df, periods)

def oscillation(df):
    """Legacy function - use PriceDynamic.osc() instead"""
    data = df[['Open', 'High', 'Low', 'Close']].copy()
    data['LastClose'] = data["Close"].shift(1)
    data["Oscillation"] = (data["High"] - data["Low"]) / data['LastClose'] * 100
    return data.dropna()

def scatter_hist(x, y):
    """Legacy function - use MarketAnalyzer.generate_scatter_plot() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    return analyzer._create_scatter_hist_plot(x, y), None

def tail_stats(data_sources):
    """Legacy function - use MarketAnalyzer.calculate_tail_statistics() instead"""
    stats_index = ["mean", "std", "skew", "kurt", "max", "99th", "95th", "90th"]
    stats_df = pd.DataFrame(index=stats_index)
    
    for period_name, data in data_sources.items():
        if len(data) > 0:
            stats_df[period_name] = [
                data.mean(), data.std(), data.skew(), data.kurtosis(),
                data.max(), data.quantile(0.99), data.quantile(0.95), data.quantile(0.90)
            ]
    
    return stats_df

def tail_plot(data_sources):
    """Legacy function - use MarketAnalyzer.generate_tail_plot() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    for period_name, data in data_sources.items():
        if len(data) > 0:
            sorted_data = np.sort(data)
            y_vals = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
            ax.plot(sorted_data, y_vals, label=period_name, linewidth=2)
    
    for percentile in [0.9, 0.95, 0.99]:
        ax.axhline(y=percentile, color='gray', linestyle='--', alpha=0.7)
    
    ax.legend()
    ax.set_title("Cumulative Density")
    ax.grid(True, alpha=0.3)
    
    return analyzer._fig_to_base64(fig)

def osc_projection(data, target_bias=0):
    """Legacy function - use MarketAnalyzer.generate_oscillation_projection() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    analyzer.price_dynamic = type('MockPriceDynamic', (), {'_data': data, 'is_valid': lambda: True})()
    return analyzer.generate_oscillation_projection(target_bias=target_bias)

def period_gap_stats(df, feature, frequency):
    """Legacy function - use MarketAnalyzer.calculate_gap_statistics() instead"""
    analyzer = MarketAnalyzer.__new__(MarketAnalyzer)
    analyzer.price_dynamic = type('MockPriceDynamic', (), {'_data': df, 'is_valid': lambda: True})()
    return analyzer._calculate_period_gap_stats(df, frequency)

def option_matrix(ticker, option_position):
    """Legacy function - use MarketAnalyzer.analyze_options() instead"""
    try:
        analyzer = MarketAnalyzer(ticker)
        option_data = []
        for _, row in option_position.iterrows():
            option_data.append({
                'option_type': row['option_type'],
                'strike': row['strike'],
                'quantity': row['quantity'],
                'premium': row['premium']
            })
        return analyzer.analyze_strategy(option_data)
    except Exception as e:
        logger.error(f"Error in legacy option_matrix function: {e}")
        return None
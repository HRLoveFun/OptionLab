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
from matplotlib.ticker import PercentFormatter
from scipy.stats import ks_2samp, percentileofscore
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
    
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='D'):
        """
        Initialize the PriceDynamic class.

        Args:
            ticker: Stock ticker symbol
            start_date: The first date the record starts
            frequency: Sampling frequency ('D', 'W', 'ME', 'QE')
        """
        self._validate_inputs(ticker, start_date, frequency)
        
        self.ticker = ticker
        self.start_date = start_date
        self.frequency = frequency
        
        # Download and process data
        raw_data = self._download_data()
        self._data = self._refrequency(raw_data) if raw_data is not None else None

    def _validate_inputs(self, ticker, start_date, frequency):
        """Validate input parameters"""
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Ticker must be a non-empty string")
        
        if not isinstance(start_date, dt.date):
            raise ValueError("start_date must be a datetime.date object")
        
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


class MarketAnalyzer:
    """
    High-level market analysis class that uses PriceDynamic for comprehensive analysis.
    """
    
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='W'):
        """Initialize MarketAnalyzer with PriceDynamic instance"""
        self.price_dynamic = PriceDynamic(ticker, start_date, frequency)
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

    def _create_scatter_hist_plot(self, x, y):
        """Create scatter plot with marginal histograms"""
        fig = plt.figure(figsize=(10, 8))
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
        ax.scatter(x, y, alpha=0.6, s=30)
        
        # Reference lines
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.plot(xlim, [0, 0], 'k--', alpha=0.5, linewidth=1)
        ax.plot([0, 0], ylim, 'k--', alpha=0.5, linewidth=1)
        
        # Highlight recent point
        if len(x) > 0 and len(y) > 0:
            ax.scatter(x.iloc[-1], y.iloc[-1], color='red', s=100, zorder=5, 
                      edgecolors='darkred', linewidth=2)
        
        # Grid
        ax.grid(True, alpha=0.3)
        
        # Labels
        ax.set_xlabel(f'{x.name} (%)', fontsize=12)
        ax.set_ylabel(f'{y.name} (%)', fontsize=12)
        
        # Marginal histograms
        ax_histx.hist(x, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax_histy.hist(y, bins=30, alpha=0.7, color='lightcoral', 
                     orientation='horizontal', edgecolor='black')
        
        # Title
        fig.suptitle(f'{x.name} vs {y.name} Analysis', fontsize=14, fontweight='bold')
        
        return fig

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

    def generate_tail_plot(self, feature_name):
        """Generate cumulative distribution plot"""
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
            
            # Reference lines
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
        # Implementation similar to create_data_sources but adapted for gaps
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

    def generate_oscillation_projection(self, percentile=0.90, target_bias=0):
        """Generate oscillation projection plot"""
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
            
            return self._create_oscillation_projection_plot(data, percentile, target_bias)
            
        except Exception as e:
            logger.error(f"Error generating oscillation projection: {e}")
            return None

    def _create_oscillation_projection_plot(self, data, percentile, target_bias):
        """Create the oscillation projection visualization"""
        try:
            # Calculate projection volatility
            proj_volatility = data["Oscillation"].quantile(percentile)
            
            # Optimize projection weights if target bias specified
            proj_high_weight = self._optimize_projection_weight(data, proj_volatility, target_bias)
            
            # Get current price data
            px_last_close = data["LastClose"].iloc[-1]
            px_last = data["Close"].iloc[-1]
            
            # Calculate projections
            proj_high_cur = px_last_close + px_last_close * proj_volatility / 100 * proj_high_weight
            proj_low_cur = px_last_close - px_last_close * proj_volatility / 100 * (1 - proj_high_weight)
            proj_high_next = px_last + px_last * proj_volatility / 100 * proj_high_weight
            proj_low_next = px_last - px_last * proj_volatility / 100 * (1 - proj_high_weight)
            
            # Create projection DataFrame
            proj_df = self._create_projection_dataframe(data, proj_high_cur, proj_low_cur, 
                                                       proj_high_next, proj_low_next)
            
            # Create visualization
            fig = self._plot_oscillation_projection(proj_df, percentile, proj_volatility)
            
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating oscillation projection plot: {e}")
            return None

    def _optimize_projection_weight(self, data, proj_volatility, target_bias):
        """Optimize projection weight to achieve target bias"""
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
        """Calculate realized bias for given parameters"""
        try:
            df = data.iloc[:-1].copy()  # Exclude last row
            
            df["ProjHigh"] = df["LastClose"] + df["LastClose"] * proj_volatility / 100 * weight
            df["ProjLow"] = df["LastClose"] - df["LastClose"] * proj_volatility / 100 * (1 - weight)
            
            df["Status"] = np.where(df["Close"] > df["ProjHigh"], 1,
                                   np.where(df["Close"] < df["ProjLow"], -1, 0))
            
            return ((df["Status"] == 1).sum() - (df["Status"] == -1).sum()) / len(df)
            
        except Exception as e:
            logger.error(f"Error calculating realized bias: {e}")
            return 0

    def _create_projection_dataframe(self, data, proj_high_cur, proj_low_cur, 
                                   proj_high_next, proj_low_next):
        """Create DataFrame for projection visualization"""
        try:
            # Get relevant dates
            date_last_close = data.get("CloseDate", [])[-2] if isinstance(data.get("CloseDate"), (list, pd.Series)) and len(data.get("CloseDate", [])) >= 2 else None
            date_last = data.get("CloseDate", [])[-1]
            
            # Create date range for projection
            end_date = date_last + pd.DateOffset(months=2)
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
            next_twenty_days = date_last + pd.Timedelta(days=4*7)
            
            # Fill projection data
            self._fill_projection_data(proj_df, date_last_close, current_month_end, 
                                     proj_high_cur, proj_low_cur, "iHigh", "iLow")
            
            self._fill_projection_data(proj_df, date_last, next_twenty_days, 
                                     proj_high_next, proj_low_next, "iHigh1", "iLow1")
            
            return proj_df
            
        except Exception as e:
            logger.error(f"Error creating projection DataFrame: {e}")
            return pd.DataFrame()

    def _get_current_month_end(self, date_last):
        """Get the end of current month"""
        if date_last.month < 12:
            return dt.datetime(date_last.year, date_last.month + 1, 1) - pd.Timedelta(days=1)
        else:
            return dt.datetime(date_last.year + 1, 1, 1) - pd.Timedelta(days=1)

    def _fill_projection_data(self, proj_df, start_date, end_date, proj_high, proj_low, 
                            high_col, low_col):
        """Fill projection data for specified period"""
        try:
            weekdays = pd.date_range(start=start_date, end=end_date, freq='B')[1:]
            start_price = proj_df.loc[start_date, "Close"]
            
            for i, date in enumerate(weekdays):
                if date in proj_df.index:
                    progress = np.sqrt((i + 1) / len(weekdays))  # Non-linear progression
                    proj_df.loc[date, high_col] = start_price + (proj_high - start_price) * progress
                    proj_df.loc[date, low_col] = start_price + (proj_low - start_price) * progress
                    
        except Exception as e:
            logger.error(f"Error filling projection data: {e}")

    def _plot_oscillation_projection(self, proj_df, percentile, proj_volatility):
        """Create the oscillation projection plot"""
        fig, ax = plt.subplots(figsize=(16, 10))
        
        try:
            x_values = np.arange(len(proj_df.index))
            
            # Plot data points
            self._plot_projection_points(ax, x_values, proj_df)
            
            # Add annotations
            self._add_projection_annotations(ax, x_values, proj_df)
            
            # Format plot
            self._format_projection_plot(ax, proj_df, percentile, proj_volatility)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error plotting oscillation projection: {e}")
            return fig

    def _plot_projection_points(self, ax, x_values, proj_df):
        """Plot all data points on the projection chart"""
        # Historical data (filled circles)
        for col, color, label in [("Close", "black", "Close"), 
                                 ("High", "purple", "High"), 
                                 ("Low", "purple", "Low")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], 
                          label=label, color=color, s=80, zorder=3)
        
        # Projected data (hollow circles)
        for col, color, label in [("iHigh", "red", "Proj High (Current)"), 
                                 ("iLow", "red", "Proj Low (Current)"),
                                 ("iHigh1", "orange", "Proj High (Next)"), 
                                 ("iLow1", "orange", "Proj Low (Next)")]:
            mask = ~proj_df[col].isna()
            if mask.any():
                ax.scatter(x_values[mask], proj_df[col][mask], 
                          label=label, facecolors='none', edgecolors=color, 
                          s=80, linewidth=2, zorder=3)

    def _add_projection_annotations(self, ax, x_values, proj_df):
        """Add value annotations to projection points"""
        # Annotate actual values
        for col, color in [("Close", "black"), ("High", "purple"), ("Low", "purple")]:
            for i, (idx, val) in enumerate(proj_df[col].dropna().items()):
                x_pos = list(proj_df.index).index(idx)
                ax.annotate(f"{val:.0f}", (x_pos, val), 
                           xytext=(0, -20), textcoords="offset points",
                           ha='center', va='top', fontsize=10, color=color, fontweight='bold')
        
        # Annotate projections (last few points only)
        for col, color in [("iHigh", "red"), ("iLow", "red"), ("iHigh1", "orange"), ("iLow1", "orange")]:
            data_points = proj_df[col].dropna()
            if len(data_points) >= 3:
                for idx, val in data_points.tail(3).items():
                    x_pos = list(proj_df.index).index(idx)
                    ax.annotate(f"{val:.0f}", (x_pos, val), 
                               xytext=(0, -20), textcoords="offset points",
                               ha='center', va='top', fontsize=10, color=color, fontweight='bold')

    def _format_projection_plot(self, ax, proj_df, percentile, proj_volatility):
        """Format the projection plot"""
        # Set x-axis labels
        ax.set_xticks(range(0, len(proj_df.index), max(1, len(proj_df.index)//20)))
        ax.set_xticklabels([proj_df.index[i].strftime('%m/%d') 
                           for i in range(0, len(proj_df.index), max(1, len(proj_df.index)//20))], 
                          rotation=45)
        
        # Labels and title
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)
        ax.set_title(f'Oscillation Projection (Percentile: {percentile:.0%}, Volatility: {proj_volatility:.1f}%)', 
                    fontsize=14, fontweight='bold')
        
        # Grid and legend
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10, loc='best')
        
        plt.tight_layout()

    def analyze_options(self, option_data):
        """Analyze options portfolio and generate P&L chart"""
        if not option_data:
            return None
        
        try:
            # Get current price
            current_price = self._get_current_price()
            if current_price is None:
                return None
            
            # Calculate option matrix
            option_matrix = self._calculate_option_matrix(current_price, option_data)
            
            # Generate P&L chart
            return self._create_option_pnl_chart(option_matrix, current_price)
            
        except Exception as e:
            logger.error(f"Error analyzing options: {e}")
            return None

    def _get_current_price(self):
        """Get current stock price"""
        try:
            if self.is_data_valid():
                return self.price_dynamic._data["Close"].iloc[-1]
            return None
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None

    def _calculate_option_matrix(self, current_price, option_data):
        """Calculate option P&L matrix"""
        try:
            # Price range for analysis
            price_range = np.linspace(current_price * 0.7, current_price * 1.3, 301)
            
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
            logger.error(f"Error calculating option matrix: {e}")
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

    def _create_option_pnl_chart(self, matrix_df, current_price):
        """Create option P&L visualization"""
        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            # Plot P&L curve
            ax.plot(matrix_df.index, matrix_df['PnL'], linewidth=3, color='blue')
            
            # Add reference lines
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
            ax.axvline(x=current_price, color='red', linestyle='--', alpha=0.8, linewidth=2,
                      label=f'Current Price: ${current_price:.2f}')
            
            # Fill profit/loss areas
            ax.fill_between(matrix_df.index, matrix_df['PnL'], 0, 
                           where=(matrix_df['PnL'] > 0), color='green', alpha=0.3, label='Profit')
            ax.fill_between(matrix_df.index, matrix_df['PnL'], 0, 
                           where=(matrix_df['PnL'] < 0), color='red', alpha=0.3, label='Loss')
            
            # Formatting
            ax.set_xlabel('Stock Price ($)', fontsize=12)
            ax.set_ylabel('P&L ($)', fontsize=12)
            ax.set_title('Options Portfolio P&L Analysis', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11)
            
            # Add key statistics
            max_profit = matrix_df['PnL'].max()
            max_loss = matrix_df['PnL'].min()
            breakeven_points = self._find_breakeven_points(matrix_df)
            
            stats_text = f'Max Profit: ${max_profit:.2f}\nMax Loss: ${max_loss:.2f}'
            if breakeven_points:
                stats_text += f'\nBreakeven: ${breakeven_points[0]:.2f}'
                if len(breakeven_points) > 1:
                    stats_text += f', ${breakeven_points[1]:.2f}'
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error creating option P&L chart: {e}")
            return None

    def _find_breakeven_points(self, matrix_df):
        """Find breakeven points in option P&L"""
        try:
            # Find where P&L crosses zero
            pnl_values = matrix_df['PnL'].values
            prices = matrix_df.index.values
            
            breakeven_points = []
            for i in range(len(pnl_values) - 1):
                if (pnl_values[i] <= 0 <= pnl_values[i + 1]) or (pnl_values[i] >= 0 >= pnl_values[i + 1]):
                    # Linear interpolation to find exact breakeven point
                    if pnl_values[i + 1] != pnl_values[i]:
                        breakeven_price = prices[i] - pnl_values[i] * (prices[i + 1] - prices[i]) / (pnl_values[i + 1] - pnl_values[i])
                        breakeven_points.append(breakeven_price)
            
            return breakeven_points
            
        except Exception as e:
            logger.error(f"Error finding breakeven points: {e}")
            return []

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
        return analyzer.analyze_options(option_data)
    except Exception as e:
        logger.error(f"Error in legacy option_matrix function: {e}")
        return None

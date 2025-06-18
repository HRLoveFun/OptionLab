import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import datetime as dt
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class PriceDynamic:
    """Core class for handling price data and calculations"""
    
    def __init__(self, ticker, start_date, frequency='W'):
        self.ticker = ticker
        self.start_date = start_date
        self.frequency = frequency
        self.data = None
        self.daily_data = None
        self._download_data()
    
    def _download_data(self):
        """Download and process stock data"""
        try:
            # Download daily data first
            stock = yf.Ticker(self.ticker)
            daily_data = stock.history(start=self.start_date, auto_adjust=True)
            
            if daily_data.empty:
                raise ValueError(f"No data available for {self.ticker}")
            
            # Store daily data
            self.daily_data = daily_data.copy()
            
            # Resample to desired frequency
            if self.frequency == 'D':
                self.data = daily_data
            else:
                freq_map = {'W': 'W-FRI', 'ME': 'ME', 'QE': 'QE'}
                resampled = daily_data.resample(freq_map[self.frequency]).agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
                self.data = resampled
                
        except Exception as e:
            print(f"Error downloading data for {self.ticker}: {e}")
            self.data = pd.DataFrame()
            self.daily_data = pd.DataFrame()
    
    def is_valid(self):
        """Check if data was successfully loaded"""
        return not self.data.empty and not self.daily_data.empty
    
    def ret(self):
        """Calculate returns"""
        if self.data.empty:
            return pd.Series()
        return self.data['Close'].pct_change().dropna()
    
    def osc(self, on_effect=True):
        """Calculate oscillation with optional overnight effect"""
        if self.data.empty:
            return pd.Series()
        
        if on_effect and self.frequency == 'D':
            # Include overnight effect for daily data
            overnight = (self.data['Open'] / self.data['Close'].shift(1) - 1).dropna()
            intraday = (self.data['Close'] / self.data['Open'] - 1)
            return overnight + intraday
        else:
            # Standard oscillation calculation
            high_low = (self.data['High'] / self.data['Low'] - 1)
            return high_low.dropna()
    
    def diff(self):
        """Calculate price differences"""
        if self.data.empty:
            return pd.Series()
        return self.data['Close'].diff().dropna()
    
    def calculate_volatility(self, window=None):
        """Calculate rolling historical volatility"""
        if self.daily_data.empty:
            return pd.Series()
        
        # Default window based on frequency
        if window is None:
            window_map = {'D': 5, 'W': 5, 'ME': 21, 'QE': 63}
            window = window_map.get(self.frequency, 21)
        
        # Calculate daily returns
        daily_returns = self.daily_data['Close'].pct_change().dropna()
        
        # Calculate rolling volatility (annualized)
        volatility = daily_returns.rolling(window=window).std() * np.sqrt(252) * 100
        
        return volatility.dropna()
    
    def bull_bear_plot(self, window=None):
        """Determine bull/bear market periods"""
        if self.daily_data.empty:
            return pd.Series()
        
        # Default window based on frequency
        if window is None:
            window_map = {'D': 20, 'W': 50, 'ME': 100, 'QE': 200}
            window = window_map.get(self.frequency, 50)
        
        close_prices = self.daily_data['Close']
        moving_avg = close_prices.rolling(window=window).mean()
        
        # Bull market when price > moving average, Bear when price < moving average
        bull_bear = (close_prices > moving_avg).astype(int)
        bull_bear = bull_bear.replace({1: 'Bull', 0: 'Bear'})
        
        return bull_bear.dropna()
    
    def calculate_recent_extreme_change(self, series, periods=[21, 63, 252]):
        """Calculate recent extreme changes for different periods"""
        if series.empty:
            return {}
        
        results = {}
        current_value = series.iloc[-1]
        
        for period in periods:
            if len(series) >= period:
                period_data = series.tail(period)
                max_val = period_data.max()
                min_val = period_data.min()
                
                # Calculate extreme changes
                max_change = (max_val / current_value - 1) * 100
                min_change = (min_val / current_value - 1) * 100
                
                results[f'{period}d'] = {
                    'max_change': max_change,
                    'min_change': min_change,
                    'current': current_value,
                    'max_val': max_val,
                    'min_val': min_val
                }
        
        return results
    
    def market_review(self):
        """Generate comprehensive market review data"""
        if self.daily_data.empty:
            return {}
        
        close_prices = self.daily_data['Close']
        returns = close_prices.pct_change().dropna()
        
        # Current date and price
        current_date = close_prices.index[-1]
        current_price = close_prices.iloc[-1]
        
        # Calculate periods
        periods = {
            '1M': 21,
            '1Q': 63,
            'YTD': self._get_ytd_days(current_date),
            'ETD': len(close_prices)  # Entire Time Duration
        }
        
        review_data = {
            'last_close': current_price,
            'current_date': current_date,
            'volatility': {},
            'returns': {},
            'correlations': {}
        }
        
        # Calculate metrics for each period
        for period_name, days in periods.items():
            if days > 0 and len(close_prices) >= days:
                period_prices = close_prices.tail(days)
                period_returns = returns.tail(days)
                
                # Volatility (annualized)
                volatility = period_returns.std() * np.sqrt(252) * 100
                review_data['volatility'][period_name] = volatility
                
                # Returns
                total_return = (period_prices.iloc[-1] / period_prices.iloc[0] - 1) * 100
                review_data['returns'][period_name] = total_return
                
                # Correlation with market (using SPY as proxy)
                correlation = self._calculate_market_correlation(period_returns)
                review_data['correlations'][period_name] = correlation
        
        return review_data
    
    def _get_ytd_days(self, current_date):
        """Calculate days from year-to-date"""
        year_start = dt.datetime(current_date.year, 1, 1)
        if hasattr(current_date, 'tz_localize'):
            year_start = pd.Timestamp(year_start).tz_localize(current_date.tz)
        else:
            year_start = pd.Timestamp(year_start)
        
        # Count business days
        business_days = pd.bdate_range(start=year_start, end=current_date)
        return len(business_days)
    
    def _calculate_market_correlation(self, returns):
        """Calculate correlation with market (SPY)"""
        try:
            if self.ticker.upper() == 'SPY':
                return 1.0
            
            # Download SPY data for the same period
            spy_data = yf.download('SPY', start=returns.index[0], end=returns.index[-1], progress=False)
            if spy_data.empty:
                return np.nan
            
            spy_returns = spy_data['Close'].pct_change().dropna()
            
            # Align dates
            common_dates = returns.index.intersection(spy_returns.index)
            if len(common_dates) < 10:  # Need at least 10 observations
                return np.nan
            
            aligned_returns = returns.loc[common_dates]
            aligned_spy = spy_returns.loc[common_dates]
            
            correlation = aligned_returns.corr(aligned_spy)
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception:
            return np.nan


class MarketAnalyzer:
    """High-level market analysis class"""
    
    def __init__(self, ticker, start_date, frequency='W'):
        self.price_dynamic = PriceDynamic(ticker, start_date, frequency)
        self.ticker = ticker
        self.start_date = start_date
        self.frequency = frequency
    
    def is_data_valid(self):
        """Check if underlying data is valid"""
        return self.price_dynamic.is_valid()
    
    def generate_scatter_plot(self, feature_type='Oscillation'):
        """Generate scatter plot with marginal histograms"""
        try:
            if feature_type == 'Oscillation':
                feature_data = self.price_dynamic.osc()
            else:
                feature_data = self.price_dynamic.diff()
            
            returns_data = self.price_dynamic.ret()
            
            # Align data
            common_index = feature_data.index.intersection(returns_data.index)
            if len(common_index) < 10:
                return None
            
            x = feature_data.loc[common_index] * 100  # Convert to percentage
            y = returns_data.loc[common_index] * 100
            
            # Create figure with subplots
            fig = plt.figure(figsize=(12, 8))
            gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 3], 
                                hspace=0.05, wspace=0.05)
            
            # Main scatter plot
            ax_main = fig.add_subplot(gs[1, 0])
            ax_main.scatter(x, y, alpha=0.6, s=30, color='steelblue')
            ax_main.set_xlabel(f'{feature_type} (%)')
            ax_main.set_ylabel('Returns (%)')
            ax_main.grid(True, alpha=0.3)
            
            # Add correlation coefficient
            correlation = x.corr(y)
            ax_main.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
                        transform=ax_main.transAxes, fontsize=12, 
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Top histogram (feature)
            ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
            ax_top.hist(x, bins=30, alpha=0.7, color='steelblue', density=True)
            ax_top.set_ylabel('Density')
            ax_top.tick_params(labelbottom=False)
            
            # Right histogram (returns)
            ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)
            ax_right.hist(y, bins=30, alpha=0.7, color='steelblue', 
                         orientation='horizontal', density=True)
            ax_right.set_xlabel('Density')
            ax_right.tick_params(labelleft=False)
            
            plt.suptitle(f'{self.ticker} - {feature_type} vs Returns Analysis', 
                        fontsize=14, fontweight='bold')
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error generating scatter plot: {e}")
            return None
    
    def calculate_tail_statistics(self, feature_type='Oscillation'):
        """Calculate tail statistics for different periods"""
        try:
            if feature_type == 'Oscillation':
                data = self.price_dynamic.osc() * 100
            else:
                data = self.price_dynamic.ret() * 100
            
            if data.empty:
                return None
            
            periods = {'1Y': 252, '3Y': 756, '5Y': 1260, 'ALL': len(data)}
            results = []
            
            for period_name, period_length in periods.items():
                if len(data) >= period_length:
                    period_data = data.tail(period_length) if period_name != 'ALL' else data
                    
                    stats_dict = {
                        'Period': period_name,
                        'Count': len(period_data),
                        'Mean': period_data.mean(),
                        'Std': period_data.std(),
                        'Skew': period_data.skew(),
                        'Kurt': period_data.kurtosis(),
                        '1%': period_data.quantile(0.01),
                        '5%': period_data.quantile(0.05),
                        '95%': period_data.quantile(0.95),
                        '99%': period_data.quantile(0.99)
                    }
                    results.append(stats_dict)
            
            return pd.DataFrame(results).round(3)
            
        except Exception as e:
            print(f"Error calculating tail statistics: {e}")
            return None
    
    def generate_tail_plot(self, feature_type='Oscillation'):
        """Generate cumulative distribution plot"""
        try:
            if feature_type == 'Oscillation':
                data = self.price_dynamic.osc() * 100
            else:
                data = self.price_dynamic.ret() * 100
            
            if data.empty:
                return None
            
            periods = {'1Y': 252, '3Y': 756, '5Y': 1260, 'ALL': len(data)}
            
            plt.figure(figsize=(12, 8))
            colors = ['blue', 'green', 'red', 'purple']
            
            for i, (period_name, period_length) in enumerate(periods.items()):
                if len(data) >= period_length:
                    period_data = data.tail(period_length) if period_name != 'ALL' else data
                    sorted_data = np.sort(period_data)
                    cumulative_prob = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
                    
                    plt.plot(sorted_data, cumulative_prob, 
                            label=f'{period_name} (n={len(period_data)})', 
                            color=colors[i % len(colors)], linewidth=2)
            
            plt.xlabel(f'{feature_type} (%)')
            plt.ylabel('Cumulative Probability')
            plt.title(f'{self.ticker} - {feature_type} Cumulative Distribution')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error generating tail plot: {e}")
            return None
    
    def generate_volatility_dynamics(self):
        """Generate enhanced volatility dynamics with price and bull/bear analysis"""
        try:
            if not self.price_dynamic.is_valid():
                return None
            
            # Get daily data
            daily_data = self.price_dynamic.daily_data
            volatility = self.price_dynamic.calculate_volatility()
            bull_bear = self.price_dynamic.bull_bear_plot()
            
            if daily_data.empty or volatility.empty:
                return None
            
            # Align all data to common dates
            common_dates = daily_data.index.intersection(volatility.index).intersection(bull_bear.index)
            if len(common_dates) < 10:
                return None
            
            prices = daily_data.loc[common_dates, 'Close']
            vol_data = volatility.loc[common_dates]
            market_regime = bull_bear.loc[common_dates]
            
            # Create figure with dual y-axes
            fig, ax1 = plt.subplots(figsize=(14, 8))
            ax2 = ax1.twinx()
            
            # Plot price with bull/bear coloring
            bull_periods = market_regime == 'Bull'
            bear_periods = market_regime == 'Bear'
            
            # Plot bull periods in green
            if bull_periods.any():
                bull_prices = prices.where(bull_periods)
                ax1.plot(bull_prices.index, bull_prices.values, color='green', 
                        linewidth=2, label='Price (Bull Market)', alpha=0.8)
            
            # Plot bear periods in red
            if bear_periods.any():
                bear_prices = prices.where(bear_periods)
                ax1.plot(bear_prices.index, bear_prices.values, color='red', 
                        linewidth=2, label='Price (Bear Market)', alpha=0.8)
            
            # Plot volatility
            ax2.plot(vol_data.index, vol_data.values, color='blue', 
                    linewidth=2, label='Volatility', alpha=0.7)
            
            # Add current volatility level
            current_vol = vol_data.iloc[-1]
            ax2.axhline(y=current_vol, color='orange', linestyle='--', 
                       alpha=0.7, label=f'Current Vol: {current_vol:.1f}%')
            
            # Formatting
            ax1.set_xlabel('Date', fontsize=12)
            ax1.set_ylabel('Price ($)', fontsize=12, color='black')
            ax2.set_ylabel('Volatility (%)', fontsize=12, color='blue')
            
            # Get window size for title
            window_map = {'D': 5, 'W': 5, 'ME': 21, 'QE': 63}
            window = window_map.get(self.frequency, 21)
            
            plt.title(f'{self.ticker} - Volatility Dynamics & Price Movement\n'
                     f'({window}-day rolling volatility, {self.frequency} frequency)', 
                     fontsize=14, fontweight='bold', pad=20)
            
            # Legends
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # Grid
            ax1.grid(True, alpha=0.3)
            
            # Add statistics box
            vol_stats = f'Vol Stats: Mean={vol_data.mean():.1f}%, Std={vol_data.std():.1f}%, Max={vol_data.max():.1f}%, Min={vol_data.min():.1f}%'
            ax1.text(0.02, 0.98, vol_stats, transform=ax1.transAxes, fontsize=10,
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error generating volatility dynamics: {e}")
            return None
    
    def calculate_gap_statistics(self, frequency):
        """Calculate gap statistics for daily frequency"""
        try:
            if frequency != 'D' or not self.price_dynamic.is_valid():
                return None
            
            daily_data = self.price_dynamic.daily_data
            if daily_data.empty:
                return None
            
            # Calculate gaps (overnight returns)
            gaps = (daily_data['Open'] / daily_data['Close'].shift(1) - 1) * 100
            gaps = gaps.dropna()
            
            if gaps.empty:
                return None
            
            periods = {'1Y': 252, '3Y': 756, '5Y': 1260, 'ALL': len(gaps)}
            results = []
            
            for period_name, period_length in periods.items():
                if len(gaps) >= period_length:
                    period_gaps = gaps.tail(period_length) if period_name != 'ALL' else gaps
                    
                    # Kolmogorov-Smirnov test against normal distribution
                    ks_stat, p_value = stats.kstest(period_gaps, 'norm', 
                                                   args=(period_gaps.mean(), period_gaps.std()))
                    
                    stats_dict = {
                        'Period': period_name,
                        'Count': len(period_gaps),
                        'Mean': period_gaps.mean(),
                        'Std': period_gaps.std(),
                        'Skew': period_gaps.skew(),
                        'Kurt': period_gaps.kurtosis(),
                        'KS-stat': ks_stat,
                        'p-value': p_value
                    }
                    results.append(stats_dict)
            
            return pd.DataFrame(results).round(4)
            
        except Exception as e:
            print(f"Error calculating gap statistics: {e}")
            return None
    
    def generate_oscillation_projection(self, percentile=0.9, target_bias=None):
        """Generate oscillation projection with bias optimization"""
        try:
            oscillation_data = self.price_dynamic.osc()
            if oscillation_data.empty:
                return None
            
            # Use osc_projection function
            projection_data = self._osc_projection(oscillation_data, target_bias)
            if projection_data is None:
                return None
            
            # Create projection plot
            plt.figure(figsize=(14, 8))
            
            # Plot historical oscillation
            plt.plot(oscillation_data.index, oscillation_data * 100, 
                    color='blue', alpha=0.7, linewidth=1, label='Historical Oscillation')
            
            # Plot projection bands
            upper_band = np.percentile(oscillation_data * 100, percentile * 100)
            lower_band = np.percentile(oscillation_data * 100, (1 - percentile) * 100)
            
            plt.axhline(y=upper_band, color='red', linestyle='--', alpha=0.7, 
                       label=f'{percentile*100:.0f}% Upper Band: {upper_band:.2f}%')
            plt.axhline(y=lower_band, color='green', linestyle='--', alpha=0.7, 
                       label=f'{(1-percentile)*100:.0f}% Lower Band: {lower_band:.2f}%')
            
            # Add mean line
            mean_osc = oscillation_data.mean() * 100
            plt.axhline(y=mean_osc, color='orange', linestyle='-', alpha=0.7, 
                       label=f'Mean: {mean_osc:.2f}%')
            
            plt.xlabel('Date')
            plt.ylabel('Oscillation (%)')
            plt.title(f'{self.ticker} - Oscillation Projection Analysis\n'
                     f'Percentile: {percentile*100:.0f}%, Bias: {"Natural" if target_bias is None else "Neutral"}')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error generating oscillation projection: {e}")
            return None
    
    def _osc_projection(self, data, target_bias):
        """Internal oscillation projection calculation"""
        try:
            if data.empty:
                return None
            
            # Simple projection logic - can be enhanced
            if target_bias is None:
                # Natural bias - use historical mean
                bias = data.mean()
            else:
                # Neutral bias
                bias = target_bias
            
            # Return projection parameters
            return {
                'bias': bias,
                'std': data.std(),
                'mean': data.mean()
            }
            
        except Exception:
            return None
    
    def analyze_options(self, option_data):
        """Analyze options portfolio"""
        try:
            if not option_data or not self.price_dynamic.is_valid():
                return None
            
            # Get current price
            current_price = self.price_dynamic.daily_data['Close'].iloc[-1]
            
            # Create price range for P&L calculation
            price_range = np.linspace(current_price * 0.7, current_price * 1.3, 100)
            total_pnl = np.zeros_like(price_range)
            
            plt.figure(figsize=(14, 8))
            
            # Calculate P&L for each option
            for option in option_data:
                option_type = option['option_type']
                strike = float(option['strike'])
                quantity = int(option['quantity'])
                premium = float(option['premium'])
                
                # Calculate option P&L
                if option_type == 'LC':  # Long Call
                    pnl = quantity * (np.maximum(price_range - strike, 0) - premium)
                elif option_type == 'SC':  # Short Call
                    pnl = quantity * (premium - np.maximum(price_range - strike, 0))
                elif option_type == 'LP':  # Long Put
                    pnl = quantity * (np.maximum(strike - price_range, 0) - premium)
                elif option_type == 'SP':  # Short Put
                    pnl = quantity * (premium - np.maximum(strike - price_range, 0))
                else:
                    continue
                
                total_pnl += pnl
                
                # Plot individual option P&L
                plt.plot(price_range, pnl, '--', alpha=0.6, 
                        label=f'{option_type} {strike} x{quantity}')
            
            # Plot total P&L
            plt.plot(price_range, total_pnl, 'b-', linewidth=3, label='Total P&L')
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.axvline(x=current_price, color='red', linestyle='--', alpha=0.7, 
                       label=f'Current Price: ${current_price:.2f}')
            
            plt.xlabel('Stock Price ($)')
            plt.ylabel('Profit/Loss ($)')
            plt.title(f'{self.ticker} - Options Portfolio P&L Analysis')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error analyzing options: {e}")
            return None
    
    def generate_market_review_chart(self):
        """Generate market review correlation chart"""
        try:
            review_data = self.price_dynamic.market_review()
            if not review_data or 'correlations' not in review_data:
                return None
            
            correlations = review_data['correlations']
            periods = list(correlations.keys())
            corr_values = [correlations[p] for p in periods if not np.isnan(correlations[p])]
            valid_periods = [p for p in periods if not np.isnan(correlations[p])]
            
            if not corr_values:
                return None
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(valid_periods, corr_values, color='steelblue', alpha=0.7)
            
            # Add value labels on bars
            for bar, value in zip(bars, corr_values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{value:.3f}', ha='center', va='bottom', fontweight='bold')
            
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.ylabel('Correlation with Market (SPY)')
            plt.xlabel('Time Period')
            plt.title(f'{self.ticker} - Market Correlation Analysis')
            plt.ylim(-1.1, 1.1)
            plt.grid(True, alpha=0.3, axis='y')
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            plot_data = buffer.getvalue()
            buffer.close()
            plt.close()
            
            return base64.b64encode(plot_data).decode()
            
        except Exception as e:
            print(f"Error generating market review chart: {e}")
            return None
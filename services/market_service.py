import pandas as pd
import numpy as np
import datetime as dt
import logging
from marketobserve import MarketAnalyzer, calculate_recent_extreme_change
from utils.formatters import DataFormatter

logger = logging.getLogger(__name__)

class MarketService:
    """Service for market data operations and market review generation"""
    
    # Market tickers for review (updated list)
    MARKET_TICKERS = [
        'DX-Y.NYB',  # US Dollar Index
        '^TNX',      # 10-Year Treasury
        'GC=F',      # Gold
        '^GSPC',     # S&P 500
        '000300.SS', # CSI 300
        '^STOXX',    # STOXX Europe 600
        '^HSI',      # Hang Seng
        '^N225',     # Nikkei 225
        'BTC-USD'    # Bitcoin
    ]
    
    @staticmethod
    def validate_ticker(ticker):
        """Validate ticker symbol by attempting to fetch data"""
        try:
            analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=30), 'D')
            is_valid = analyzer.is_data_valid()
            message = 'Valid ticker' if is_valid else 'Invalid ticker or no data available'
            return is_valid, message
        except Exception as e:
            logger.error(f"Error validating ticker {ticker}: {e}")
            return False, f'Error validating ticker: {str(e)}'
    
    @staticmethod
    def generate_market_review(form_data):
        """Generate market review results with comprehensive table"""
        results = {}
        
        try:
            # Create ticker list with user's ticker first, then market tickers
            all_tickers = [form_data['ticker']] + MarketService.MARKET_TICKERS
            unique_tickers = MarketService._remove_duplicates(all_tickers)
            
            # Get user ticker's time range for ETD calculations
            user_time_range = MarketService._get_ticker_time_range(form_data['ticker'], form_data['start_date'])
            
            # Calculate comprehensive market data
            market_data = MarketService._calculate_comprehensive_market_data(unique_tickers, user_time_range)
            
            # Create market overview table
            if market_data:
                results['market_overview_table'] = MarketService._create_comprehensive_market_table(market_data)
            
        except Exception as e:
            logger.error(f"Error generating market review: {e}", exc_info=True)
        
        return results
    
    @staticmethod
    def _remove_duplicates(tickers):
        """Remove duplicates while preserving order"""
        seen = set()
        unique_tickers = []
        for ticker in tickers:
            if ticker not in seen:
                unique_tickers.append(ticker)
                seen.add(ticker)
        return unique_tickers
    
    @staticmethod
    def _get_ticker_time_range(ticker, start_date):
        """Get the time range for the user's ticker to use for ETD calculations"""
        try:
            analyzer = MarketAnalyzer(ticker, start_date, 'D')
            if analyzer.is_data_valid():
                data = analyzer.price_dynamic._data
                # 使用极值点作为起点
                _, _, extreme_date = calculate_recent_extreme_change(data['Close'])
                if pd.notna(extreme_date):
                    return extreme_date.date(), data.index[-1].date()
                else:
                    return data.index[0].date(), data.index[-1].date()
            return None, None
        except Exception as e:
            logger.error(f"Error getting time range for {ticker}: {e}")
            return None, None
    
    @staticmethod
    def _calculate_comprehensive_market_data(tickers, user_time_range):
        """Calculate comprehensive market data including correlations"""
        market_data = []
        
        # Get reference data for correlations (user's ticker)
        reference_ticker = tickers[0]
        reference_returns = MarketService._get_ticker_returns(reference_ticker, user_time_range)
        
        for ticker in tickers:
            try:
                ticker_data = MarketService._calculate_ticker_comprehensive_metrics(
                    ticker, user_time_range, reference_returns, reference_ticker
                )
                if ticker_data is not None:
                    market_data.append(ticker_data)
                
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker}: {e}")
                continue
        
        return market_data
    
    @staticmethod
    def _get_ticker_returns(ticker, time_range):
        """Get ticker returns for correlation calculations"""
        try:
            start_date, end_date = time_range
            if start_date is None:
                start_date = dt.date.today() - dt.timedelta(days=365)
            
            analyzer = MarketAnalyzer(ticker, start_date, 'D')
            if analyzer.is_data_valid():
                return analyzer.price_dynamic._data['Close'].pct_change().dropna()
            return None
        except Exception as e:
            logger.error(f"Error getting returns for {ticker}: {e}")
            return None
    
    @staticmethod
    def _calculate_ticker_comprehensive_metrics(ticker, user_time_range, reference_returns, reference_ticker):
        """Calculate comprehensive metrics including correlations for a ticker"""
        try:
            # Determine date range - use user's ticker time range for ETD
            start_date, end_date = user_time_range
            if start_date is None:
                start_date = dt.date.today() - dt.timedelta(days=365)
            
            # Create analyzer for the ticker
            analyzer = MarketAnalyzer(ticker, start_date, 'D')
            
            if not analyzer.is_data_valid():
                return None
            
            data = analyzer.price_dynamic._data
            current_price = data['Close'].iloc[-1]
            
            # Get ticker returns for correlation
            ticker_returns = data['Close'].pct_change().dropna()
            
            # Calculate metrics for different periods
            periods = {
                '1M': 22,    # ~1 month
                '1Q': 66,    # ~1 quarter
                'YTD': None, # Year to date
                'ETD': None  # Entire time period (user's range)
            }
            
            metrics = {'Ticker': ticker, 'Last_Close': current_price}
            
            for period_name, days in periods.items():
                # Calculate returns and volatility
                returns, volatility = MarketService._calculate_period_metrics(data, period_name, days, user_time_range)
                metrics[f'{period_name}_Return'] = returns
                metrics[f'{period_name}_Volatility'] = volatility
                
                # Calculate correlation with reference ticker
                if ticker != reference_ticker and reference_returns is not None:
                    correlation = MarketService._calculate_period_correlation(
                        ticker_returns, reference_returns, period_name, days
                    )
                    metrics[f'{period_name}_Correlation'] = correlation
                else:
                    # Self-correlation is always 1.0
                    metrics[f'{period_name}_Correlation'] = 1.0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive metrics for {ticker}: {e}")
            return None
    
    @staticmethod
    def _calculate_period_metrics(data, period_name, days, user_time_range):
        """Calculate return and volatility for a specific period"""
        try:
            if period_name == 'YTD':
                # Year to date calculation
                year_start = dt.date(dt.date.today().year, 1, 1)
                period_data = data[data.index.date >= year_start]
            elif period_name == 'ETD':
                # Use user's ticker time range
                start_date, end_date = user_time_range
                if start_date is not None:
                    period_data = data[data.index.date >= start_date]
                else:
                    period_data = data
            else:
                # Fixed period calculation
                period_data = data.iloc[-days:] if len(data) > days else data
            
            if len(period_data) > 1:
                period_return = (period_data['Close'].iloc[-1] / period_data['Close'].iloc[0]) - 1
                # period_volatility = period_data['Close'].pct_change().std() * np.sqrt(252)
                period_volatility = np.log(period_data['Close']).diff().std() * np.sqrt(252)

                return period_return, period_volatility
            else:
                return np.nan, np.nan
                
        except Exception as e:
            logger.warning(f"Error calculating {period_name} metrics: {e}")
            return np.nan, np.nan
    
    @staticmethod
    def _calculate_period_correlation(ticker_returns, reference_returns, period_name, days):
        """Calculate correlation for a specific period"""
        try:
            if period_name == 'YTD':
                # Year to date calculation
                year_start = dt.date(dt.date.today().year, 1, 1)
                ticker_period = ticker_returns[ticker_returns.index.date >= year_start]
                reference_period = reference_returns[reference_returns.index.date >= year_start]
            elif period_name == 'ETD':
                # Entire time period - use all available overlapping data
                ticker_period = ticker_returns
                reference_period = reference_returns
            else:
                # Fixed period calculation
                ticker_period = ticker_returns.iloc[-days:] if len(ticker_returns) > days else ticker_returns
                reference_period = reference_returns.iloc[-days:] if len(reference_returns) > days else reference_returns
            
            # Align the data by index (dates)
            aligned_data = pd.DataFrame({
                'ticker': ticker_period,
                'reference': reference_period
            }).dropna()
            
            if len(aligned_data) > 10:  # Minimum data points for meaningful correlation
                correlation = aligned_data['ticker'].corr(aligned_data['reference'])
                return correlation if not pd.isna(correlation) else np.nan
            else:
                return np.nan
                
        except Exception as e:
            logger.warning(f"Error calculating {period_name} correlation: {e}")
            return np.nan
    
    @staticmethod
    def _create_comprehensive_market_table(market_data):
        """Create formatted HTML table for comprehensive market overview"""
        try:
            market_df = pd.DataFrame(market_data)
            
            # Define column order
            column_order = ['Ticker', 'Last_Close']
            
            # Add return columns
            for period in ['1M', '1Q', 'YTD', 'ETD']:
                column_order.append(f'{period}_Return')
            
            # Add volatility columns
            for period in ['1M', '1Q', 'YTD', 'ETD']:
                column_order.append(f'{period}_Volatility')
            
            # Add correlation columns
            for period in ['1M', '1Q', 'YTD', 'ETD']:
                column_order.append(f'{period}_Correlation')
            
            # Reorder columns
            available_columns = [col for col in column_order if col in market_df.columns]
            market_df = market_df[available_columns]
            
            # Format the dataframe
            formatted_df = market_df.copy()
            
            # Format percentage columns (returns, volatility, correlations)
            percentage_cols = [col for col in formatted_df.columns if 'Return' in col or 'Volatility' in col]
            correlation_cols = [col for col in formatted_df.columns if 'Correlation' in col]
            
            for col in percentage_cols:
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
                )
            
            # Format correlation columns (as decimal with 3 places)
            for col in correlation_cols:
                formatted_df[col] = formatted_df[col].apply(
                    lambda x: f"{x:.3f}" if pd.notna(x) else "N/A"
                )
            
            # Format last close price
            if 'Last_Close' in formatted_df.columns:
                formatted_df['Last_Close'] = formatted_df['Last_Close'].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                )
            
            # Rename columns for better display
            column_renames = {
                'Last_Close': 'Last Close',
                '1M_Return': '1M Return',
                '1Q_Return': '1Q Return',
                'YTD_Return': 'YTD Return',
                'ETD_Return': 'ETD Return',
                '1M_Volatility': '1M Volatility',
                '1Q_Volatility': '1Q Volatility',
                'YTD_Volatility': 'YTD Volatility',
                'ETD_Volatility': 'ETD Volatility',
                '1M_Correlation': '1M Correlation',
                '1Q_Correlation': '1Q Correlation',
                'YTD_Correlation': 'YTD Correlation',
                'ETD_Correlation': 'ETD Correlation'
            }
            
            formatted_df = formatted_df.rename(columns=column_renames)
            
            return formatted_df.to_html(classes='table table-striped', index=False, escape=False)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive market table: {e}")
            return None
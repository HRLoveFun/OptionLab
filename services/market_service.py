import pandas as pd
import numpy as np
import datetime as dt
import logging
from marketobserve import MarketAnalyzer
from .chart_service import ChartService

logger = logging.getLogger(__name__)

class MarketService:
    """Service for market data operations and market review generation"""
    
    # Market tickers for review
    MARKET_TICKERS = [
        'DX-Y.NYB',  # US Dollar Index
        '^TNX',      # 10-Year Treasury
        '^GSPC',     # S&P 500
        'GC=F',      # Gold
        '000300.SS', # CSI 300
        '^STOXX',    # STOXX Europe 600
        '^HSI',      # Hang Seng
        '^N225'      # Nikkei 225
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
        """Generate market review results including market overview table and correlation matrix"""
        results = {}
        
        try:
            # Create unique ticker list including user's ticker
            market_tickers = [form_data['ticker']] + MarketService.MARKET_TICKERS
            unique_tickers = MarketService._remove_duplicates(market_tickers)
            
            # Calculate market review data
            market_data, correlation_data = MarketService._calculate_market_data(unique_tickers)
            
            # Create market overview table
            if market_data:
                results['market_overview_table'] = MarketService._create_market_table(market_data)
            
            # Generate correlation matrix chart
            if len(correlation_data) >= 2:
                correlation_chart = ChartService.generate_correlation_matrix(correlation_data)
                if correlation_chart:
                    results['correlation_matrix_url'] = correlation_chart
            
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
    def _calculate_market_data(tickers):
        """Calculate market data for all tickers"""
        market_data = []
        correlation_data = {}
        
        for ticker in tickers:
            try:
                # Get recent extreme change data
                extreme_data = MarketService._calculate_ticker_metrics(ticker)
                if extreme_data is not None:
                    market_data.append(extreme_data)
                    
                    # Store price data for correlation calculation
                    analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=365), 'D')
                    if analyzer.is_data_valid():
                        correlation_data[ticker] = analyzer.price_dynamic._data['Close'].pct_change().dropna()
                
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker}: {e}")
                continue
        
        return market_data, correlation_data
    
    @staticmethod
    def _calculate_ticker_metrics(ticker):
        """Calculate recent extreme changes for a ticker"""
        try:
            # Create analyzer for the ticker
            analyzer = MarketAnalyzer(ticker, dt.date.today() - dt.timedelta(days=365), 'D')
            
            if not analyzer.is_data_valid():
                return None
            
            data = analyzer.price_dynamic._data
            current_price = data['Close'].iloc[-1]
            
            # Calculate returns and volatility for different periods
            periods = {
                '1M': 22,    # ~1 month
                '1Q': 66,    # ~1 quarter
                'YTD': None, # Year to date
                'ETD': None  # Entire time period
            }
            
            metrics = {'Ticker': ticker, 'Last_Close': current_price}
            
            for period_name, days in periods.items():
                returns, volatility = MarketService._calculate_period_metrics(data, period_name, days)
                metrics[f'{period_name}_Return'] = returns
                metrics[f'{period_name}_Volatility'] = volatility
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics for {ticker}: {e}")
            return None
    
    @staticmethod
    def _calculate_period_metrics(data, period_name, days):
        """Calculate return and volatility for a specific period"""
        try:
            if period_name == 'YTD':
                # Year to date calculation
                year_start = dt.date(dt.date.today().year, 1, 1)
                period_data = data[data.index.date >= year_start]
            elif period_name == 'ETD':
                # Entire time period
                period_data = data
            else:
                # Fixed period calculation
                period_data = data.iloc[-days:] if len(data) > days else data
            
            if len(period_data) > 1:
                period_return = (period_data['Close'].iloc[-1] / period_data['Close'].iloc[0]) - 1
                period_volatility = period_data['Close'].pct_change().std() * np.sqrt(252)
                return period_return, period_volatility
            else:
                return np.nan, np.nan
                
        except Exception as e:
            logger.warning(f"Error calculating {period_name} metrics: {e}")
            return np.nan, np.nan
    
    @staticmethod
    def _create_market_table(market_data):
        """Create formatted HTML table for market overview"""
        try:
            market_df = pd.DataFrame(market_data)
            formatted_df = market_df.copy()
            
            # Format percentage columns
            percentage_cols = ['1M_Return', '1Q_Return', 'YTD_Return', 'ETD_Return', 
                             '1M_Volatility', '1Q_Volatility', 'YTD_Volatility', 'ETD_Volatility']
            
            for col in percentage_cols:
                if col in formatted_df.columns:
                    formatted_df[col] = formatted_df[col].apply(
                        lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
                    )
            
            # Format last close price
            if 'Last_Close' in formatted_df.columns:
                formatted_df['Last_Close'] = formatted_df['Last_Close'].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
                )
            
            return formatted_df.to_html(classes='table table-striped', index=False, escape=False)
            
        except Exception as e:
            logger.error(f"Error creating market table: {e}")
            return None
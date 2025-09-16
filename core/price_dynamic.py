import pandas as pd
import yfinance as yf
import numpy as np
import datetime as dt
import logging

logger = logging.getLogger(__name__)

PERIODS = [12, 36, 60, "ALL"]
FREQUENCY_MAPPING = {
    'D': 'Daily',
    'W': 'Weekly', 
    'ME': 'Monthly',
    'QE': 'Quarterly'
}

VOLATILITY_WINDOWS = {
    'D': 5,   # Daily equivalent to weekly
    'W': 5,   # Weekly
    'ME': 21, # Monthly
    'QE': 63  # Quarterly
}

class PriceDynamic:
    """
    Handles price data downloading, processing, and calculations.
    """
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='D'):
        self._validate_inputs(ticker, start_date, frequency)
        self.ticker = ticker
        self.start_date = start_date
        self.frequency = frequency
        raw_data = self._download_data()
        self._data = self._refrequency(raw_data) if raw_data is not None else None
        self._daily_data = raw_data

    def _validate_inputs(self, ticker, start_date, frequency):
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Ticker must be a non-empty string")
        if not isinstance(start_date, dt.date):
            raise ValueError("start_date must be a datetime.date object")
        if frequency not in ['D', 'W', 'ME', 'QE']:
            raise ValueError("frequency must be one of ['D', 'W', 'ME', 'QE']")

    def __getattr__(self, attr):
        if self._data is not None and hasattr(self._data, attr):
            return getattr(self._data, attr)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def __getitem__(self, item):
        if self._data is not None:
            return self._data[item]
        raise KeyError(f"No data available for key: {item}")

    def _download_data(self):
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
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.index = pd.DatetimeIndex(df.index)
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
        if df is None or df.empty:
            return None
        try:
            if self.frequency == 'D':
                df['LastClose'] = df["Close"].shift(1)
                return df
            resampled = df.resample(self.frequency).agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Adj Close': 'last',
                'Volume': 'sum'
            }).dropna()
            resampled['LastClose'] = resampled["Close"].shift(1)
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

    def calculate_volatility(self, window=None):
        if self._daily_data is None or self._daily_data.empty:
            return None
        try:
            if window is None:
                window = VOLATILITY_WINDOWS.get(self.frequency, 21)
            daily_returns = self._daily_data['Close'].pct_change().dropna()
            rolling_vol = daily_returns.rolling(window=window).std() * np.sqrt(252) * 100
            rolling_vol.name = 'Volatility'
            return rolling_vol.dropna()
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    def bull_bear_plot(self, price_series):
        if price_series is None or price_series.empty:
            return {'bull_segments': [], 'bear_segments': []}
        try:
            df = pd.DataFrame(price_series, columns=['Close'])
            df['CumMax'] = df['Close'].cummax()
            df['IsBull'] = df['Close'] >= 0.8 * df['CumMax']
            
            # Handle case where all values are the same
            if df['IsBull'].nunique() == 1:
                # If all bull or all bear, create one segment
                if df['IsBull'].iloc[0]:
                    return {'bull_segments': [price_series], 'bear_segments': []}
                else:
                    return {'bull_segments': [], 'bear_segments': [price_series]}
            
            trend_changes = df['IsBull'] != df['IsBull'].shift(1)
            trend_changes.iloc[0] = True
            segments = {'bull_segments': [], 'bear_segments': []}
            current_trend = None
            segment_start = None
            
            for i, (date, row) in enumerate(df.iterrows()):
                is_trend_change = trend_changes.loc[date]
                if is_trend_change or i == len(df) - 1:
                    if segment_start is not None and current_trend is not None:
                        segment_data = price_series.loc[segment_start:date]
                        if len(segment_data) > 1:
                            if current_trend:
                                segments['bull_segments'].append(segment_data)
                            else:
                                segments['bear_segments'].append(segment_data)
                    if i < len(df) - 1:
                        segment_start = date
                        current_trend = row['IsBull']
            
            # Ensure we have at least some segments for visualization
            if not segments['bull_segments'] and not segments['bear_segments']:
                # Fallback: treat entire series as one segment based on overall trend
                if len(price_series) > 1:
                    overall_trend = price_series.iloc[-1] > price_series.iloc[0]
                    if overall_trend:
                        segments['bull_segments'] = [price_series]
                    else:
                        segments['bear_segments'] = [price_series]
            
            return segments
        except Exception as e:
            logger.error(f"Error in bull_bear_plot: {e}")
            return {'bull_segments': [], 'bear_segments': []}

    def osc(self, on_effect=False):
        if self._data is None or self._data.empty:
            return None
        try:
            if on_effect:
                high_adj = np.maximum(self._data["High"], self._data["LastClose"])
                low_adj = np.minimum(self._data["Low"], self._data["LastClose"])
                osc_data = (high_adj - low_adj) / self._data['LastClose'] * 100
            else:
                osc_data = (self._data["High"] - self._data["Low"]) / self._data['LastClose'] * 100
            osc_data.name = 'Oscillation'
            return osc_data.dropna()
        except Exception as e:
            logger.error(f"Error calculating oscillation: {e}")
            return None

    def ret(self):
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
        return self._data is not None and not self._data.empty

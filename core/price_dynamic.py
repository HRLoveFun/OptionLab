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
    def __init__(self, ticker: str, start_date=dt.date(2016, 12, 1), frequency='D', end_date: dt.date | None = None):
        self._validate_inputs(ticker, start_date, frequency, end_date)
        self.ticker = ticker
        # Store user-requested horizon
        self.start_date = start_date
        self.user_start_date = start_date
        self.frequency = frequency
        # If end_date is blank (None), set internal end_date to today, but remember it was not user-provided
        self._user_provided_end = end_date is not None
        self.end_date = end_date or dt.date.today()  # internal exclusive end (may be adjusted for horizon filtering)
        self.user_end_date = self.end_date
        # Use an earlier download start to ensure the first in-horizon period has a valid LastClose
        self._download_start = self._compute_download_start(self.start_date, self.frequency)
        raw_data = self._download_data()
        self._data = self._refrequency(raw_data) if raw_data is not None else None
        self._daily_data = raw_data

    def _validate_inputs(self, ticker, start_date, frequency, end_date=None):
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Ticker must be a non-empty string")
        if not isinstance(start_date, dt.date):
            raise ValueError("start_date must be a datetime.date object")
        if frequency not in ['D', 'W', 'ME', 'QE']:
            raise ValueError("frequency must be one of ['D', 'W', 'ME', 'QE']")
        if end_date is not None and not isinstance(end_date, dt.date):
            raise ValueError("end_date must be a datetime.date object or None")
        if end_date is not None and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

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
                start=self._download_start,
                end=self.end_date,
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

    def _compute_download_start(self, start_date: dt.date, frequency: str) -> dt.date:
        # Provide a buffer before the requested start to compute LastClose, ret, etc.
        if frequency == 'D':
            delta = dt.timedelta(days=7)
        elif frequency == 'W':
            delta = dt.timedelta(days=35)
        elif frequency == 'ME':
            delta = dt.timedelta(days=90)
        elif frequency == 'QE':
            delta = dt.timedelta(days=200)
        else:
            delta = dt.timedelta(days=30)
        return start_date - delta

    def _apply_horizon(self, series: pd.Series | None) -> pd.Series | None:
        if series is None or series.empty:
            return series
        try:
            start_ts = pd.Timestamp(self.user_start_date)
            # Determine effective end timestamp: if user left horizon end blank, include current period by extending end
            if getattr(self, '_user_provided_end', True):
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
            return series[(idx >= start_ts) & (idx < end_ts)]
        except Exception:
            return series

    def _compute_effective_end_ts(self) -> pd.Timestamp:
        """Compute an effective exclusive end timestamp so the current period is included
        when the Horizon end date was left blank by the user.

        Rules:
        - D: today + 1 day
        - W: end of current week (Sunday by pandas default) + 1 day
        - ME: end of current month + 1 day
        - QE: end of current quarter + 1 day
        """
        today = pd.Timestamp(dt.date.today())
        if self.frequency == 'D':
            eff = today + pd.Timedelta(days=1)
        elif self.frequency == 'W':
            # pandas weekly default is anchored to Sunday ('W-SUN'), so compute upcoming Sunday
            weekday = today.weekday()  # Monday=0, Sunday=6
            days_to_sunday = (6 - weekday) % 7
            end_of_week = today + pd.Timedelta(days=days_to_sunday)
            eff = end_of_week + pd.Timedelta(days=1)
        elif self.frequency == 'ME':
            end_of_month = today + pd.offsets.MonthEnd(0)
            eff = end_of_month + pd.Timedelta(days=1)
        elif self.frequency == 'QE':
            end_of_quarter = today + pd.offsets.QuarterEnd(0)
            eff = end_of_quarter + pd.Timedelta(days=1)
        else:
            eff = today + pd.Timedelta(days=1)
        return pd.Timestamp(eff)

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
            return self._apply_horizon(rolling_vol.dropna())
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
            return self._apply_horizon(osc_data.dropna())
        except Exception as e:
            logger.error(f"Error calculating oscillation: {e}")
            return None

    def ret(self):
        if self._data is None or self._data.empty:
            return None
        try:
            ret_data = ((self._data["Close"] - self._data['LastClose']) / self._data['LastClose']) * 100
            ret_data.name = 'Returns'
            return self._apply_horizon(ret_data.dropna())
        except Exception as e:
            logger.error(f"Error calculating returns: {e}")
            return None

    def dif(self):
        if self._data is None or self._data.empty:
            return None
        try:
            dif_data = self._data["Close"] - self._data['LastClose']
            dif_data.name = 'Difference'
            return self._apply_horizon(dif_data.dropna())
        except Exception as e:
            logger.error(f"Error calculating difference: {e}")
            return None

    def is_valid(self):
        return self._data is not None and not self._data.empty

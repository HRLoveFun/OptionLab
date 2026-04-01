"""Tests for ticker format handling across the pipeline.

These tests verify that yahoo-format tickers are correctly converted to
futu-format before being passed to Futu API calls. This prevents the
production bug where 'NVDA' was sent to futu instead of 'US.NVDA'.
"""
import datetime as dt
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from utils.ticker_utils import is_futu_format, normalize_ticker

# ---------------------------------------------------------------------------
# 1. Ticker normalisation sanity checks
# ---------------------------------------------------------------------------

class TestTickerNormalisationForFutu:
    """Verify normalize_ticker always produces a usable futu ticker for
    common US/HK symbols — this is the contract the route relies on."""

    @pytest.mark.parametrize("raw, expected_futu", [
        ("NVDA", "US.NVDA"),
        ("nvda", "US.NVDA"),
        ("AAPL", "US.AAPL"),
        ("US.NVDA", "US.NVDA"),
        ("us.nvda", "US.NVDA"),
        ("0700.HK", "HK.00700"),
        ("HK.00700", "HK.00700"),
        ("BRK-B", "US.BRK.B"),
    ])
    def test_normalize_produces_futu_ticker(self, raw, expected_futu):
        yahoo, futu = normalize_ticker(raw)
        assert futu == expected_futu, (
            f"normalize_ticker({raw!r}) returned futu={futu!r}, "
            f"expected {expected_futu!r}"
        )

    @pytest.mark.parametrize("raw", ["NVDA", "US.NVDA", "AAPL"])
    def test_futu_ticker_is_futu_format(self, raw):
        """The futu ticker returned must pass is_futu_format()."""
        _, futu = normalize_ticker(raw)
        assert is_futu_format(futu), (
            f"normalize_ticker({raw!r}) returned futu={futu!r} "
            f"which is_futu_format() rejects"
        )


# ---------------------------------------------------------------------------
# 2. /api/option_chain route passes futu-format ticker to futu provider
# ---------------------------------------------------------------------------

class TestOptionChainRouteFutuFormat:
    """The /api/option_chain endpoint must convert any incoming ticker to
    futu-format before calling get_option_chain_futu()."""

    @pytest.fixture
    def client(self):
        from app import app
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c

    @patch('app._futu_available', True)
    @patch('app._refresh_futu_status')
    def test_yahoo_ticker_converted_to_futu(self, mock_refresh, client):
        """Sending ticker=NVDA must call get_option_chain_futu('US.NVDA', ...)."""
        fake_result = {
            'expirations': ['2026-04-17'],
            'chain': {'2026-04-17': {'calls': [], 'puts': []}},
            'spot': 100.0,
        }

        with patch(
            'data_pipeline.futu_provider.get_option_chain_futu',
            return_value=fake_result,
        ) as mock_futu:
            resp = client.get('/api/option_chain?ticker=NVDA')
            assert resp.status_code == 200
            # Verify the futu provider was called with futu-format ticker
            mock_futu.assert_called_once()
            call_ticker = mock_futu.call_args[0][0]
            assert call_ticker == 'US.NVDA', (
                f"get_option_chain_futu called with {call_ticker!r} "
                f"instead of 'US.NVDA'"
            )

    @patch('app._futu_available', True)
    @patch('app._refresh_futu_status')
    def test_futu_ticker_passed_through(self, mock_refresh, client):
        """Sending ticker=US.NVDA must still work (no double conversion)."""
        fake_result = {
            'expirations': [],
            'chain': {},
            'spot': 100.0,
        }

        with patch(
            'data_pipeline.futu_provider.get_option_chain_futu',
            return_value=fake_result,
        ) as mock_futu:
            resp = client.get('/api/option_chain?ticker=US.NVDA')
            assert resp.status_code == 200
            call_ticker = mock_futu.call_args[0][0]
            assert call_ticker == 'US.NVDA'

    @patch('app._futu_available', True)
    @patch('app._refresh_futu_status')
    def test_hk_ticker_converted(self, mock_refresh, client):
        """Sending ticker=0700.HK must call futu with HK.00700."""
        fake_result = {
            'expirations': [],
            'chain': {},
            'spot': 50.0,
        }

        with patch(
            'data_pipeline.futu_provider.get_option_chain_futu',
            return_value=fake_result,
        ) as mock_futu:
            resp = client.get('/api/option_chain?ticker=0700.HK')
            assert resp.status_code == 200
            call_ticker = mock_futu.call_args[0][0]
            assert call_ticker == 'HK.00700'

    @patch('app._futu_available', False)
    def test_futu_unavailable_returns_503(self, client):
        """When Futu is not connected, the route should return 503."""
        resp = client.get('/api/option_chain?ticker=NVDA')
        assert resp.status_code == 503
        data = resp.get_json()
        assert 'error' in data


# ---------------------------------------------------------------------------
# 3. OptionsChainAnalyzer._init_from_futu normalises ticker
# ---------------------------------------------------------------------------

class TestOptionsChainAnalyzerFutuInit:
    """OptionsChainAnalyzer must convert yahoo tickers to futu format."""

    def test_yahoo_ticker_converted_in_init(self):
        """Passing 'NVDA' (yahoo-format) must call futu provider with 'US.NVDA'."""
        from core.options_chain_analyzer import OptionsChainAnalyzer

        fake_result = {
            'expirations': ['2026-04-17'],
            'chain': {
                '2026-04-17': {
                    'calls': [{'strike': 100, 'lastPrice': 5, 'bid': 4.9,
                               'ask': 5.1, 'volume': 100, 'openInterest': 500,
                               'iv': 35.0, 'itm': True, 'liq_score': 'GOOD',
                               'liq_reason': ''}],
                    'puts': [],
                }
            },
            'spot': 100.0,
        }

        with patch(
            'data_pipeline.futu_provider.get_option_chain_futu',
            return_value=fake_result,
        ) as mock_futu:
            OptionsChainAnalyzer('NVDA', source='futu')
            mock_futu.assert_called_once()
            call_ticker = mock_futu.call_args[0][0]
            assert call_ticker == 'US.NVDA', (
                f"_init_from_futu called futu provider with {call_ticker!r}, "
                f"expected 'US.NVDA'"
            )


# ---------------------------------------------------------------------------
# 4. MarketAnalyzer features_df must not be empty when data is sufficient
# ---------------------------------------------------------------------------

def _make_daily_ohlcv(days: int = 60, start: str = '2026-01-02') -> pd.DataFrame:
    """Create a synthetic OHLCV DataFrame for testing."""
    dates = pd.bdate_range(start=start, periods=days, freq='B')
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(days) * 0.5)
    df = pd.DataFrame({
        'Open': close - np.random.rand(days) * 0.3,
        'High': close + np.abs(np.random.randn(days)) * 0.5,
        'Low': close - np.abs(np.random.randn(days)) * 0.5,
        'Close': close,
        'Adj Close': close,
        'Volume': np.random.randint(1_000_000, 10_000_000, days),
    }, index=dates)
    # Ensure High >= Close >= Low
    df['High'] = df[['High', 'Close', 'Open']].max(axis=1)
    df['Low'] = df[['Low', 'Close', 'Open']].min(axis=1)
    return df


class TestMarketAnalyzerFeaturesNotEmpty:
    """features_df must have rows when the horizon contains sufficient data."""

    def _build_analyzer_with_mock_data(self, start_date, end_date=None,
                                        frequency='D', data_days=60):
        """Create a MarketAnalyzer with mocked price data."""
        from core.market_analyzer import MarketAnalyzer

        fake_df = _make_daily_ohlcv(days=data_days, start='2025-12-01')

        with patch.object(
            MarketAnalyzer, '__init__', lambda self, *a, **kw: None,
        ):
            analyzer = MarketAnalyzer.__new__(MarketAnalyzer)

        # Manually replicate __init__ logic with mocked data
        from core.price_dynamic import PriceDynamic

        with patch.object(
            PriceDynamic, '__init__', lambda self, *a, **kw: None,
        ):
            pd_obj = PriceDynamic.__new__(PriceDynamic)

        pd_obj.ticker = 'TEST'
        pd_obj.user_start_date = start_date
        pd_obj.user_end_date = end_date or dt.date.today()
        pd_obj._user_provided_end = end_date is not None
        pd_obj.frequency = frequency
        pd_obj._daily_data = fake_df

        # Replicate _refrequency for D
        resampled = fake_df.copy()
        resampled['LastClose'] = resampled['Close'].shift(1)
        resampled['LastAdjClose'] = resampled['Adj Close'].shift(1)
        pd_obj._data = resampled

        analyzer.price_dynamic = pd_obj
        analyzer.ticker = 'TEST'
        analyzer.frequency = frequency
        analyzer.end_date = end_date
        analyzer._calculate_features()
        return analyzer

    def test_features_not_empty_two_month_daily(self):
        """2-month daily horizon should produce a non-empty features_df."""
        analyzer = self._build_analyzer_with_mock_data(
            start_date=dt.date(2026, 1, 1),
            frequency='D',
            data_days=80,
        )
        assert not analyzer.features_df.empty, (
            f"features_df should not be empty, shape={analyzer.features_df.shape}"
        )
        assert len(analyzer.features_df) >= 20, (
            f"Expected >=20 rows for 2-month daily, got {len(analyzer.features_df)}"
        )

    def test_features_not_empty_short_horizon(self):
        """Even a 1-month horizon should produce features if data exists."""
        analyzer = self._build_analyzer_with_mock_data(
            start_date=dt.date(2026, 1, 1),
            end_date=dt.date(2026, 2, 1),
            frequency='D',
            data_days=80,
        )
        assert not analyzer.features_df.empty, (
            "features_df should not be empty for 1-month horizon"
        )

    def test_features_empty_when_no_overlap(self):
        """features_df is empty when horizon is entirely outside data range."""
        analyzer = self._build_analyzer_with_mock_data(
            start_date=dt.date(2030, 1, 1),
            end_date=dt.date(2030, 6, 1),
            frequency='D',
            data_days=80,
        )
        assert analyzer.features_df.empty

    def test_all_feature_columns_present(self):
        """features_df must contain all 5 expected columns."""
        analyzer = self._build_analyzer_with_mock_data(
            start_date=dt.date(2026, 1, 1),
            frequency='D',
            data_days=80,
        )
        expected_cols = {'Oscillation', 'Osc_high', 'Osc_low', 'Returns', 'Difference'}
        assert set(analyzer.features_df.columns) == expected_cols


# ---------------------------------------------------------------------------
# 5. parse_tickers always returns yahoo-format tickers
# ---------------------------------------------------------------------------

class TestParseTickers:
    """parse_tickers must handle mixed-format comma-separated input."""

    def test_futu_format_normalised(self):
        from app import parse_tickers
        result = parse_tickers('US.NVDA, US.TLT')
        assert result == ['NVDA', 'TLT']

    def test_yahoo_format_passthrough(self):
        from app import parse_tickers
        result = parse_tickers('NVDA, TLT')
        assert result == ['NVDA', 'TLT']

    def test_mixed_format(self):
        from app import parse_tickers
        result = parse_tickers('us.nvda, TLT')
        assert result == ['NVDA', 'TLT']

    def test_dedup(self):
        from app import parse_tickers
        result = parse_tickers('NVDA,US.NVDA, nvda')
        assert result == ['NVDA']

    def test_hk_ticker(self):
        from app import parse_tickers
        result = parse_tickers('0700.HK')
        assert result == ['0700.HK']

    def test_max_six(self):
        from app import parse_tickers
        result = parse_tickers('A,B,C,D,E,F,G,H')
        assert len(result) <= 6

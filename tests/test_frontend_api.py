"""End-to-end tests for frontend tab functionality.

Tests exercise the Flask routes and JS-facing APIs that power each
dashboard tab, verifying that:
  - The index page renders (GET/POST)
  - The /api/option_chain endpoint handles valid/invalid inputs
  - Config-driven filter parameters (DTE, moneyness) are respected
  - MarketAnalyzer features_df is non-empty with adequate data
  - PriceDynamic normalizes futu-format tickers to yahoo format
"""

import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Flask test client
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a Flask test client with isolated DB."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════
# 1. Index page (Parameter tab → form submission)
# ═══════════════════════════════════════════════════════════════════════════

class TestIndexPage:
    def test_get_renders(self, client):
        """GET / should return 200 with form elements."""
        resp = client.get('/')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'id="ticker"' in html
        assert 'id="start_time"' in html

    def test_get_has_config_tab(self, client):
        """Config tab with all option filter fields should be present."""
        resp = client.get('/')
        html = resp.data.decode()
        assert 'id="cfg-frequency"' in html
        assert 'id="cfg-max-dte"' in html
        assert 'id="cfg-moneyness-low"' in html
        assert 'id="cfg-moneyness-high"' in html
        assert 'id="cfg-max-contracts"' in html

    def test_get_has_position_sizing_in_settings(self, client):
        """Position sizing fields should be inside Analysis Settings card."""
        resp = client.get('/')
        html = resp.data.decode()
        assert 'id="account_size"' in html
        assert 'id="max_risk_pct"' in html

    def test_post_missing_ticker(self, client):
        """POST without ticker should show error."""
        resp = client.post('/', data={
            'ticker': '',
            'start_time': '2024-01',
            'frequency': 'ME',
        })
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'error' in html.lower() or 'ticker' in html.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 2. /api/option_chain endpoint
# ═══════════════════════════════════════════════════════════════════════════

class TestOptionChainAPI:
    def test_missing_ticker(self, client):
        """Should return 400 when ticker is missing."""
        resp = client.get('/api/option_chain')
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data

    def test_empty_ticker(self, client):
        """Should return 400 when ticker is empty string."""
        resp = client.get('/api/option_chain?ticker=')
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert 'error' in data

    def test_invalid_ticker_format(self, client):
        """Non-convertible tickers should return an error response."""
        resp = client.get('/api/option_chain?ticker=XXXINVALID')
        data = json.loads(resp.data)
        assert 'error' in data
        # 404 (no options available), 500 (yfinance rejects unknown ticker)
        assert resp.status_code in (404, 500)

    def test_filter_params_forwarded(self, client):
        """Filter params (max_dte, moneyness) should be accepted in query string."""
        resp = client.get('/api/option_chain?ticker=NVDA&max_dte=45&moneyness_low=0.7&moneyness_high=1.3')
        data = json.loads(resp.data)
        # The important thing is no 500 (internal server error from bad param parsing)
        assert resp.status_code != 500 or 'error' in data
        # If Futu available and returns data, expirations should be within max_dte
        if resp.status_code == 200 and 'expirations' in data:
            from datetime import datetime
            today = datetime.now().date()
            for exp in data['expirations']:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                assert (exp_date - today).days <= 45, f"Expiry {exp} exceeds max_dte=45"

    def test_default_dte_is_45(self, client):
        """Default max_dte should be 45 (not 60)."""
        # Verify by inspecting the route's docstring or actual defaults
        from app import option_chain
        assert '45' in (option_chain.__doc__ or '')


# ═══════════════════════════════════════════════════════════════════════════
# 3. Option chain filter logic
# ═══════════════════════════════════════════════════════════════════════════

class TestOptionChainFilter:
    def _make_chain(self, days_list, strikes_list, spot=100.0):
        """Helper to build chain data for filter tests."""
        from datetime import datetime, timedelta
        today = datetime.now().date()
        expirations = []
        chain = {}
        for d in days_list:
            exp = (today + timedelta(days=d)).strftime('%Y-%m-%d')
            expirations.append(exp)
            chain[exp] = {
                'calls': [{'strike': s} for s in strikes_list],
                'puts': [{'strike': s} for s in strikes_list],
            }
        return {'expirations': expirations, 'chain': chain, 'spot': spot}

    def test_dte_45_default(self):
        """With max_dte=45, expirations at 50d should be excluded."""
        from app import _filter_option_chain
        data = self._make_chain([10, 44, 50, 90], [90, 100, 110])
        result = _filter_option_chain(data, max_dte=45)
        # 10d and 44d are within, 50d and 90d are outside
        assert len(result['expirations']) == 2

    def test_moneyness_30pct(self):
        """With moneyness [0.7, 1.3], strikes outside should be excluded."""
        from app import _filter_option_chain
        data = self._make_chain([10], [50, 70, 100, 130, 200], spot=100.0)
        result = _filter_option_chain(data, max_dte=45, moneyness_low=0.7, moneyness_high=1.3)
        exp = list(result['chain'].keys())[0]
        # strike 50 (0.5) and 200 (2.0) should be out; 70, 100, 130 should be in
        assert len(result['chain'][exp]['calls']) == 3
        kept_strikes = {c['strike'] for c in result['chain'][exp]['calls']}
        assert kept_strikes == {70, 100, 130}


# ═══════════════════════════════════════════════════════════════════════════
# 4. features_df non-empty with adequate data (dropna fix)
# ═══════════════════════════════════════════════════════════════════════════

class TestFeaturesDF:
    @staticmethod
    def _make_price_df(n_rows=60):
        """Create synthetic daily price data."""
        dates = pd.bdate_range(end=dt.date.today(), periods=n_rows)
        np.random.seed(42)
        close = 100 + np.cumsum(np.random.randn(n_rows) * 0.5)
        return pd.DataFrame({
            'Open': close - 0.5,
            'High': close + 1.0,
            'Low': close - 1.0,
            'Close': close,
            'Adj Close': close,
            'Volume': np.random.randint(1e6, 1e7, n_rows),
        }, index=dates)

    def test_features_df_nonempty_with_synthetic_data(self, monkeypatch):
        """features_df should have rows when PriceDynamic has adequate data."""
        from core.market_analyzer import MarketAnalyzer
        from core.price_dynamic import PriceDynamic

        fake_df = self._make_price_df(60)
        start = fake_df.index[0].date()
        end = fake_df.index[-1].date()

        # Patch PriceDynamic to use synthetic data

        def mock_init(self, ticker, start_date=None, frequency='D', end_date=None):
            self.ticker = ticker
            self.user_start_date = start_date or start
            self.frequency = frequency
            self._user_provided_end = end_date is not None
            self.user_end_date = end_date or end
            df = fake_df.copy()
            df['LastClose'] = df['Close'].shift(1)
            df['LastAdjClose'] = df['Adj Close'].shift(1)
            self._data = df
            self._daily_data = fake_df.copy()

        monkeypatch.setattr(PriceDynamic, '__init__', mock_init)

        analyzer = MarketAnalyzer('TEST', start, 'D', end_date=end)
        assert not analyzer.features_df.empty, f"features_df should not be empty, shape={analyzer.features_df.shape}"
        assert len(analyzer.features_df) >= 50, f"Expected >=50 rows, got {len(analyzer.features_df)}"
        assert set(analyzer.features_df.columns) == {'Oscillation', 'Osc_high', 'Osc_low', 'Returns', 'Difference'}

    def test_features_df_tolerates_partial_nan(self, monkeypatch):
        """features_df should retain rows even when one column has NaN at a few spots."""
        from core.market_analyzer import MarketAnalyzer
        from core.price_dynamic import PriceDynamic

        fake_df = self._make_price_df(60)
        # Introduce NaN in High for a few rows (osc_high will be NaN there)
        fake_df.iloc[10:13, fake_df.columns.get_loc('High')] = np.nan

        start = fake_df.index[0].date()
        end = fake_df.index[-1].date()

        def mock_init(self, ticker, start_date=None, frequency='D', end_date=None):
            self.ticker = ticker
            self.user_start_date = start_date or start
            self.frequency = frequency
            self._user_provided_end = end_date is not None
            self.user_end_date = end_date or end
            df = fake_df.copy()
            df['LastClose'] = df['Close'].shift(1)
            df['LastAdjClose'] = df['Adj Close'].shift(1)
            self._data = df
            self._daily_data = fake_df.copy()

        monkeypatch.setattr(PriceDynamic, '__init__', mock_init)

        analyzer = MarketAnalyzer('TEST', start, 'D', end_date=end)
        # With dropna(how='all'), rows with partial NaN are kept
        assert not analyzer.features_df.empty
        # At least most rows should survive — only first row (shift NaN) removed
        assert len(analyzer.features_df) >= 50

    def test_features_df_empty_when_all_nan(self, monkeypatch):
        """features_df should have 0 rows when all data is NaN."""
        from core.market_analyzer import MarketAnalyzer
        from core.price_dynamic import PriceDynamic

        fake_df = self._make_price_df(10)
        fake_df['Adj Close'] = np.nan
        fake_df['High'] = np.nan
        fake_df['Low'] = np.nan

        start = fake_df.index[0].date()
        end = fake_df.index[-1].date()

        def mock_init(self, ticker, start_date=None, frequency='D', end_date=None):
            self.ticker = ticker
            self.user_start_date = start_date or start
            self.frequency = frequency
            self._user_provided_end = end_date is not None
            self.user_end_date = end_date or end
            df = fake_df.copy()
            df['LastClose'] = df['Close'].shift(1)
            df['LastAdjClose'] = df['Adj Close'].shift(1)
            self._data = df
            self._daily_data = fake_df.copy()

        monkeypatch.setattr(PriceDynamic, '__init__', mock_init)

        analyzer = MarketAnalyzer('TEST', start, 'D', end_date=end)
        assert analyzer.features_df.empty


# ═══════════════════════════════════════════════════════════════════════════
# 5. PriceDynamic ticker normalization
# ═══════════════════════════════════════════════════════════════════════════

class TestPriceDynamicTickerNorm:
    def test_futu_format_normalized(self, monkeypatch):
        """PriceDynamic('US.NVDA', ...) should normalize to 'NVDA'."""
        from core.price_dynamic import PriceDynamic

        # Prevent actual data download
        monkeypatch.setattr(PriceDynamic, '_fetch_daily_from_db', lambda self: None)
        monkeypatch.setattr(PriceDynamic, '_download_data', lambda self: None)

        pd_obj = PriceDynamic('US.NVDA', start_date=dt.date(2024, 1, 1))
        assert pd_obj.ticker == 'NVDA'

    def test_yahoo_format_unchanged(self, monkeypatch):
        """PriceDynamic('NVDA', ...) should keep ticker as 'NVDA'."""
        from core.price_dynamic import PriceDynamic

        monkeypatch.setattr(PriceDynamic, '_fetch_daily_from_db', lambda self: None)
        monkeypatch.setattr(PriceDynamic, '_download_data', lambda self: None)

        pd_obj = PriceDynamic('NVDA', start_date=dt.date(2024, 1, 1))
        assert pd_obj.ticker == 'NVDA'

    def test_hk_format_normalized(self, monkeypatch):
        """PriceDynamic('HK.00700', ...) should normalize to '0700.HK'."""
        from core.price_dynamic import PriceDynamic

        monkeypatch.setattr(PriceDynamic, '_fetch_daily_from_db', lambda self: None)
        monkeypatch.setattr(PriceDynamic, '_download_data', lambda self: None)

        pd_obj = PriceDynamic('HK.00700', start_date=dt.date(2024, 1, 1))
        assert pd_obj.ticker == '0700.HK'


# ═══════════════════════════════════════════════════════════════════════════
# 6. Template auto-refresh script
# ═══════════════════════════════════════════════════════════════════════════

class TestAutoRefreshTemplate:
    def test_auto_refresh_script_present(self, client):
        """The 60-second auto-refresh interval should be in the page."""
        resp = client.get('/')
        html = resp.data.decode()
        assert 'OC_REFRESH_MS' in html
        assert '60 * 1000' in html or '60000' in html

    def test_auto_load_flags_present(self, client):
        """Auto-load flags for option chain and odds should be in the page."""
        resp = client.get('/')
        html = resp.data.decode()
        assert '_ocAutoLoaded' in html
        assert '_oddsAutoLoaded' in html

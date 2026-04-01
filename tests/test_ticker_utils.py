"""Tests for utils/ticker_utils.py — futu ticker format conversion."""

import pytest

from utils.ticker_utils import (
    from_futu_ticker,
    futu_to_yahoo,
    is_futu_format,
    normalize_ticker,
    to_futu_ticker,
    yahoo_to_futu,
)

# ── to_futu_ticker ──────────────────────────────────────────────

class TestToFutuTicker:
    """Tests for to_futu_ticker()."""

    def test_us_stock(self):
        assert to_futu_ticker("AAPL", "US") == "US.AAPL"

    def test_us_default_market(self):
        """market defaults to 'US'."""
        assert to_futu_ticker("SPY") == "US.SPY"

    def test_hk_stock(self):
        assert to_futu_ticker("00700", "HK") == "HK.00700"

    def test_hk_etf(self):
        assert to_futu_ticker("02800", "HK") == "HK.02800"

    def test_sh_stock(self):
        assert to_futu_ticker("600519", "SH") == "SH.600519"

    def test_sz_stock(self):
        assert to_futu_ticker("000001", "SZ") == "SZ.000001"

    def test_market_case_insensitive(self):
        assert to_futu_ticker("AAPL", "us") == "US.AAPL"
        assert to_futu_ticker("00700", "hk") == "HK.00700"

    # ── edge / error cases ──

    def test_unknown_market_raises(self):
        with pytest.raises(ValueError, match="Unknown market"):
            to_futu_ticker("AAPL", "XX")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError, match="Invalid symbol"):
            to_futu_ticker("", "US")

    def test_whitespace_symbol_raises(self):
        with pytest.raises(ValueError, match="Invalid symbol"):
            to_futu_ticker("  ", "US")

    def test_empty_market_raises(self):
        with pytest.raises(ValueError, match="Unknown market"):
            to_futu_ticker("AAPL", "")


# ── from_futu_ticker ────────────────────────────────────────────

class TestFromFutuTicker:
    """Tests for from_futu_ticker()."""

    def test_us_stock(self):
        assert from_futu_ticker("US.AAPL") == ("AAPL", "US")

    def test_hk_stock(self):
        assert from_futu_ticker("HK.00700") == ("00700", "HK")

    def test_us_option_ticker(self):
        """Option tickers contain extra info after the dot — all kept as symbol."""
        sym, mkt = from_futu_ticker("US.AAPL250618P550000")
        assert mkt == "US"
        assert sym == "AAPL250618P550000"

    def test_hk_option_ticker(self):
        sym, mkt = from_futu_ticker("HK.TCH210429C350000")
        assert mkt == "HK"
        assert sym == "TCH210429C350000"

    def test_market_prefix_normalised_to_upper(self):
        """Lowercase market prefix should still parse."""
        assert from_futu_ticker("us.AAPL") == ("AAPL", "US")

    # ── edge / error cases ──

    def test_no_dot_raises(self):
        with pytest.raises(ValueError, match="missing '.'"):
            from_futu_ticker("USAAPL")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid futu ticker"):
            from_futu_ticker("")

    def test_none_raises(self):
        with pytest.raises(ValueError, match="Invalid futu ticker"):
            from_futu_ticker(None)  # type: ignore[arg-type]

    def test_unknown_market_prefix_raises(self):
        with pytest.raises(ValueError, match="Unknown market"):
            from_futu_ticker("XX.AAPL")

    def test_dot_only_raises(self):
        with pytest.raises(ValueError, match="empty symbol"):
            from_futu_ticker("US.")


# ── round-trip ──────────────────────────────────────────────────

class TestRoundTrip:
    """Verify bidirectional conversion is consistent."""

    @pytest.mark.parametrize("symbol,market", [
        ("AAPL", "US"),
        ("SPY", "US"),
        ("00700", "HK"),
        ("02800", "HK"),
        ("600519", "SH"),
        ("000001", "SZ"),
    ])
    def test_round_trip(self, symbol: str, market: str):
        futu = to_futu_ticker(symbol, market)
        got_symbol, got_market = from_futu_ticker(futu)
        assert got_symbol == symbol
        assert got_market == market


# ── is_futu_format ──────────────────────────────────────────────

class TestIsFutuFormat:
    """Tests for is_futu_format()."""

    def test_us_stock(self):
        assert is_futu_format("US.AAPL") is True

    def test_hk_stock(self):
        assert is_futu_format("HK.00700") is True

    def test_yahoo_us(self):
        assert is_futu_format("AAPL") is False

    def test_yahoo_hk(self):
        assert is_futu_format("0700.HK") is False

    def test_yahoo_index(self):
        assert is_futu_format("^SPX") is False

    def test_empty(self):
        assert is_futu_format("") is False

    def test_none(self):
        assert is_futu_format(None) is False

    def test_case_insensitive(self):
        assert is_futu_format("us.nvda") is True


# ── futu_to_yahoo ───────────────────────────────────────────────

class TestFutuToYahoo:
    """Tests for futu_to_yahoo()."""

    def test_us_stock(self):
        assert futu_to_yahoo("US.AAPL") == "AAPL"

    def test_us_stock_with_dot(self):
        assert futu_to_yahoo("US.BRK.B") == "BRK-B"

    def test_us_index(self):
        assert futu_to_yahoo("US..SPX") == "^SPX"

    def test_hk_stock(self):
        assert futu_to_yahoo("HK.00700") == "0700.HK"

    def test_hk_stock_5digit(self):
        assert futu_to_yahoo("HK.09988") == "9988.HK"

    def test_unsupported_market_raises(self):
        with pytest.raises(ValueError, match="Unsupported market"):
            futu_to_yahoo("SH.600519")

    def test_case_insensitive_input(self):
        assert futu_to_yahoo("us.nvda") == "NVDA"


# ── yahoo_to_futu ───────────────────────────────────────────────

class TestYahooToFutu:
    """Tests for yahoo_to_futu()."""

    def test_us_stock(self):
        assert yahoo_to_futu("AAPL") == "US.AAPL"

    def test_us_stock_with_hyphen(self):
        assert yahoo_to_futu("BRK-B") == "US.BRK.B"

    def test_us_index(self):
        assert yahoo_to_futu("^SPX") == "US..SPX"

    def test_hk_stock_4digit(self):
        assert yahoo_to_futu("0700.HK") == "HK.00700"

    def test_hk_stock_5digit(self):
        assert yahoo_to_futu("89988.HK") == "HK.89988"

    def test_futures_raises(self):
        with pytest.raises(ValueError, match="Futures"):
            yahoo_to_futu("GC=F")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Invalid yahoo ticker"):
            yahoo_to_futu("")


# ── normalize_ticker ────────────────────────────────────────────

class TestNormalizeTicker:
    """Tests for normalize_ticker()."""

    def test_futu_us_stock(self):
        yahoo, futu = normalize_ticker("US.NVDA")
        assert yahoo == "NVDA"
        assert futu == "US.NVDA"

    def test_futu_hk_stock(self):
        yahoo, futu = normalize_ticker("HK.00700")
        assert yahoo == "0700.HK"
        assert futu == "HK.00700"

    def test_yahoo_us_stock(self):
        yahoo, futu = normalize_ticker("AAPL")
        assert yahoo == "AAPL"
        assert futu == "US.AAPL"

    def test_yahoo_hk_stock(self):
        yahoo, futu = normalize_ticker("0700.HK")
        assert yahoo == "0700.HK"
        assert futu == "HK.00700"

    def test_yahoo_index(self):
        yahoo, futu = normalize_ticker("^SPX")
        assert yahoo == "^SPX"
        assert futu == "US..SPX"

    def test_case_insensitive(self):
        yahoo, futu = normalize_ticker("us.nvda")
        assert yahoo == "NVDA"
        assert futu == "US.NVDA"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            normalize_ticker("")

    def test_futu_us_index(self):
        yahoo, futu = normalize_ticker("US..SPX")
        assert yahoo == "^SPX"
        assert futu == "US..SPX"

    def test_tlt(self):
        """Verify us.tlt normalizes correctly."""
        yahoo, futu = normalize_ticker("us.tlt")
        assert yahoo == "TLT"
        assert futu == "US.TLT"

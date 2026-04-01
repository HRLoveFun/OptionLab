"""Futu ticker format conversion utilities.

Converts between plain symbols (e.g. "AAPL") and futu-format tickers
(e.g. "US.AAPL"). Covers US and HK markets primarily.

Also provides detection and cross-format conversion:
  - is_futu_format(): detect "US.AAPL" style
  - futu_to_yahoo(): "US.AAPL" → "AAPL", "HK.00700" → "0700.HK"
  - yahoo_to_futu(): "AAPL" → "US.AAPL", "0700.HK" → "HK.00700"
  - normalize_ticker(): accept either format, return (yahoo, futu) pair
"""

import re

FUTU_MARKETS = {"US", "HK", "SH", "SZ", "SG", "JP", "AU", "MY", "CA", "FX"}

# --- Regex patterns per WORKFLOW spec §6.1 ---
# Futu format
_RE_FUTU_US_STOCK = re.compile(r"^US\.[A-Z.\-]+$")
_RE_FUTU_US_INDEX = re.compile(r"^US\.\.[A-Z.\-]+$")
_RE_FUTU_HK_STOCK = re.compile(r"^HK\.\d{5}$")

# Yahoo format
_RE_YAHOO_US_STOCK = re.compile(r"^[A-Z\-]+$")
_RE_YAHOO_US_INDEX = re.compile(r"^\^[A-Z]+$")
_RE_YAHOO_HK_STOCK = re.compile(r"^\d{4,5}\.HK$")
_RE_YAHOO_FUTURES = re.compile(r"^[A-Z]+=F$")


def is_futu_format(ticker: str) -> bool:
    """Detect whether a ticker string is in futu format (MARKET.SYMBOL)."""
    if not ticker or not isinstance(ticker, str):
        return False
    ticker = ticker.strip().upper()
    parts = ticker.split(".", 1)
    if len(parts) != 2:
        return False
    market = parts[0]
    return market in FUTU_MARKETS


def futu_to_yahoo(futu_ticker: str) -> str:
    """Convert futu-format ticker to Yahoo Finance format.

    Supported conversions:
        US.AAPL   → AAPL
        US.BRK.B  → BRK-B
        US..SPX   → ^SPX
        HK.00700  → 0700.HK

    Raises:
        ValueError: If market is not US or HK (unsupported conversion).
    """
    symbol, market = from_futu_ticker(futu_ticker)
    symbol = symbol.upper()

    if market == "US":
        if symbol.startswith("."):
            # Index: US..SPX → ^SPX
            return f"^{symbol[1:]}"
        # Replace dots in symbols with hyphens for Yahoo (BRK.B → BRK-B)
        return symbol.replace(".", "-")

    if market == "HK":
        # HK.00700 → strip leading zeros to 4-digit min, add .HK
        # e.g. 00700 → 0700.HK, 09988 → 9988.HK
        numeric = symbol.lstrip("0") or "0"
        # Yahoo HK tickers are 4-5 digits: pad to at least 4
        if len(numeric) < 4:
            numeric = numeric.zfill(4)
        return f"{numeric}.HK"

    raise ValueError(f"Unsupported market for yahoo conversion: {market}")


def yahoo_to_futu(yahoo_ticker: str) -> str:
    """Convert Yahoo Finance ticker to futu format.

    Supported conversions:
        AAPL    → US.AAPL
        BRK-B   → US.BRK.B
        ^SPX    → US..SPX
        0700.HK → HK.00700

    Raises:
        ValueError: If ticker format is not recognized as US or HK.
    """
    if not yahoo_ticker or not isinstance(yahoo_ticker, str):
        raise ValueError(f"Invalid yahoo ticker: {yahoo_ticker!r}")
    ticker = yahoo_ticker.strip().upper()

    # HK stock: 0700.HK → HK.00700
    if _RE_YAHOO_HK_STOCK.match(ticker):
        code = ticker.split(".")[0]
        return f"HK.{code.zfill(5)}"

    # US index: ^SPX → US..SPX
    if _RE_YAHOO_US_INDEX.match(ticker):
        return f"US..{ticker[1:]}"

    # US futures: GC=F — not supported for futu
    if _RE_YAHOO_FUTURES.match(ticker):
        raise ValueError(f"Futures ticker not supported for futu conversion: {ticker}")

    # US stock: AAPL → US.AAPL, BRK-B → US.BRK.B
    if _RE_YAHOO_US_STOCK.match(ticker):
        return f"US.{ticker.replace('-', '.')}"

    raise ValueError(f"Cannot determine market for yahoo ticker: {ticker}")


def normalize_ticker(raw: str) -> tuple[str, str]:
    """Accept a ticker in either futu or yahoo format, return (yahoo_ticker, futu_ticker).

    For unsupported markets (not US/HK), futu_ticker may be empty string.
    For unrecognized formats, assumes yahoo format and futu_ticker is empty.

    Returns:
        (yahoo_ticker, futu_ticker) tuple
    """
    if not raw or not isinstance(raw, str):
        raise ValueError(f"Invalid ticker: {raw!r}")
    raw = raw.strip().upper()

    if is_futu_format(raw):
        try:
            yahoo = futu_to_yahoo(raw)
            return yahoo, raw
        except ValueError:
            # Unsupported market — use raw as-is for yahoo, no futu equivalent
            _, market = from_futu_ticker(raw)
            symbol, _ = from_futu_ticker(raw)
            return symbol, raw

    # Assume yahoo format
    try:
        futu = yahoo_to_futu(raw)
        return raw, futu
    except ValueError:
        # Unrecognized format — pass through as yahoo, no futu
        return raw, ""


def to_futu_ticker(symbol: str, market: str = "US") -> str:
    """Convert a plain symbol + market to futu ticker format.

    Args:
        symbol: Pure code, e.g. "AAPL", "00700", "600519"
        market: Market prefix, e.g. "US", "HK", "SH"

    Returns:
        Futu-format ticker, e.g. "US.AAPL"

    Raises:
        ValueError: If symbol is empty or market is unknown.
    """
    if not symbol or not symbol.strip():
        raise ValueError(f"Invalid symbol: {symbol!r}")
    market = market.upper().strip()
    if market not in FUTU_MARKETS:
        raise ValueError(f"Unknown market: {market}")
    return f"{market}.{symbol.strip()}"


def from_futu_ticker(futu_ticker: str) -> tuple[str, str]:
    """Split a futu-format ticker into (symbol, market).

    Args:
        futu_ticker: e.g. "US.AAPL", "HK.TCH210429C350000"

    Returns:
        (symbol, market) tuple, e.g. ("AAPL", "US")

    Raises:
        ValueError: If format is invalid or market is unknown.
    """
    if not futu_ticker or not isinstance(futu_ticker, str):
        raise ValueError(f"Invalid futu ticker: {futu_ticker!r}")
    if "." not in futu_ticker:
        raise ValueError(f"Invalid futu ticker format (missing '.'): {futu_ticker!r}")
    market, symbol = futu_ticker.split(".", 1)
    market = market.upper().strip()
    if not symbol or not symbol.strip():
        raise ValueError(f"Invalid futu ticker (empty symbol): {futu_ticker!r}")
    if market not in FUTU_MARKETS:
        raise ValueError(f"Unknown market: {market}")
    return symbol.strip(), market

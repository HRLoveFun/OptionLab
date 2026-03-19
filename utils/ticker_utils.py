"""Futu ticker format conversion utilities.

Converts between plain symbols (e.g. "AAPL") and futu-format tickers
(e.g. "US.AAPL"). Covers US and HK markets primarily.
"""

FUTU_MARKETS = {"US", "HK", "SH", "SZ", "SG", "JP", "AU", "MY", "CA", "FX"}


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

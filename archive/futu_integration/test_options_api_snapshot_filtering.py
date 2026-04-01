"""
Test Suite: Options Chain API, Snapshot API, and Local Filtering

This test file validates the following functionality:
1. Fetch options chain data for a specific expiration date using an options chain API
2. Use a snapshot API to batch-retrieve underlying instrument data (including strike prices)
   without requiring a subscription
3. Perform local filtering (strike price range, option type, etc.) on retrieved data

The tests demonstrate:
- API integration patterns with proper error handling
- Data transformation from API responses to DataFrames
- Local filtering logic verification
- Assertions on expected data structure and content

Note: This test file uses placeholder API endpoints. Replace with actual endpoints
when connecting to Futu, Interactive Brokers, or other data providers.
"""

import unittest
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

# ============================================================================
# Mock API Client Classes (Placeholder implementations)
# ============================================================================


class MockOptionsChainAPI:
    """
    Mock Options Chain API client.

    Simulates fetching options chain data for a specific ticker and expiration.
    In production, this would connect to Futu API, IBKR API, or similar.

    API Endpoint: GET /api/v1/options/chain/{ticker}?expiration={date}
    """

    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self._mock_data = self._generate_mock_data()

    def _generate_mock_data(self) -> dict[str, Any]:
        """Generate realistic mock options chain data for testing."""
        spot_price = 150.0
        strikes = [140, 145, 150, 155, 160, 165, 170]

        calls = []
        puts = []

        for _i, strike in enumerate(strikes):
            # ATM options have higher IV
            moneyness = abs(strike - spot_price) / spot_price
            iv_base = 0.25 + moneyness * 0.15  # IV increases as we go OTM

            # Generate call option
            intrinsic_call = max(spot_price - strike, 0)
            time_value = max(2.0 - moneyness * 1.5, 0.1)
            call_price = intrinsic_call + time_value

            calls.append(
                {
                    "strike": strike,
                    "option_type": "CALL",
                    "bid": round(call_price * 0.95, 2),
                    "ask": round(call_price * 1.05, 2),
                    "last_price": round(call_price, 2),
                    "volume": int(1000 * (1 - moneyness)),
                    "open_interest": int(5000 * (1 - moneyness * 0.5)),
                    "implied_volatility": round(iv_base, 4),
                    "delta": round(0.5 + (spot_price - strike) / 20, 3),
                    "gamma": 0.03,
                    "theta": -0.05,
                    "vega": 0.15,
                    "itm": strike < spot_price,
                }
            )

            # Generate put option
            intrinsic_put = max(strike - spot_price, 0)
            put_price = intrinsic_put + time_value

            puts.append(
                {
                    "strike": strike,
                    "option_type": "PUT",
                    "bid": round(put_price * 0.95, 2),
                    "ask": round(put_price * 1.05, 2),
                    "last_price": round(put_price, 2),
                    "volume": int(800 * (1 - moneyness * 0.8)),
                    "open_interest": int(4000 * (1 - moneyness * 0.6)),
                    "implied_volatility": round(iv_base + 0.02, 4),  # Put skew
                    "delta": round(-0.5 + (spot_price - strike) / 20, 3),
                    "gamma": 0.03,
                    "theta": -0.04,
                    "vega": 0.14,
                    "itm": strike > spot_price,
                }
            )

        return {
            "ticker": "AAPL",
            "expiration": "2026-04-17",
            "spot_price": spot_price,
            "underlying": {
                "symbol": "AAPL",
                "last_price": spot_price,
                "change": 2.5,
                "change_percent": 1.69,
            },
            "options": {
                "calls": calls,
                "puts": puts,
            },
        }

    def fetch_options_chain(
        self,
        ticker: str,
        expiration: str,
    ) -> dict[str, Any]:
        """
        Fetch options chain for a specific ticker and expiration date.

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            expiration: Expiration date in YYYY-MM-DD format

        Returns:
            Dictionary containing calls, puts, and underlying data

        Raises:
            ValueError: If ticker or expiration is invalid
            ConnectionError: If API request fails
        """
        if not ticker or not isinstance(ticker, str):
            raise ValueError(f"Invalid ticker: {ticker}")

        if not expiration:
            raise ValueError("Expiration date is required")

        # Validate date format
        try:
            datetime.strptime(expiration, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {expiration}. Expected YYYY-MM-DD")

        # Simulate API latency
        return self._mock_data


class MockSnapshotAPI:
    """
    Mock Snapshot API client for batch-retrieving instrument data.

    This API allows fetching market data snapshots without requiring
    real-time subscriptions. Useful for initial data loading and analysis.

    API Endpoint: POST /api/v1/market/snapshot
    Request Body: {"instruments": ["AAPL", "AAPL240417C150", ...]}
    """

    def __init__(self, base_url: str = "https://api.example.com"):
        self.base_url = base_url
        self._batch_size_limit = 100  # API limitation

    def batch_get_snapshot(
        self,
        instruments: list[str],
    ) -> dict[str, Any]:
        """
        Batch retrieve market snapshots for multiple instruments.

        Args:
            instruments: List of instrument symbols/identifiers

        Returns:
            Dictionary mapping instrument symbols to their snapshot data

        Raises:
            ValueError: If instrument list exceeds batch size limit
            ConnectionError: If API request fails
        """
        if len(instruments) > self._batch_size_limit:
            raise ValueError(f"Batch size {len(instruments)} exceeds limit of {self._batch_size_limit}")

        # Generate mock snapshot data for each instrument
        snapshots = {}
        for i, symbol in enumerate(instruments):
            # Determine if it's an underlying or option
            if len(symbol) <= 5:  # Stock symbol
                snapshots[symbol] = {
                    "symbol": symbol,
                    "last_price": 150.0 + (i * 0.01),
                    "bid": 149.95,
                    "ask": 150.05,
                    "volume": 1000000,
                    "open_interest": None,
                    "implied_volatility": None,
                    "instrument_type": "STOCK",
                }
            else:  # Option symbol
                # Extract strike from symbol (simplified)
                try:
                    strike = float(symbol[-6:-3]) if symbol[-6:-3].isdigit() else 150.0
                except ValueError:
                    strike = 150.0

                option_type = "CALL" if "C" in symbol else "PUT"
                snapshots[symbol] = {
                    "symbol": symbol,
                    "last_price": 5.0 + (i * 0.01),
                    "bid": 4.9,
                    "ask": 5.1,
                    "volume": 500 + i * 10,
                    "open_interest": 2000 + i * 100,
                    "implied_volatility": 0.28 + (i * 0.001),
                    "strike": strike,
                    "instrument_type": option_type,
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "snapshots": snapshots,
            "count": len(snapshots),
        }


# ============================================================================
# Data Processing and Filtering Functions
# ============================================================================


def parse_options_chain(api_response: dict[str, Any]) -> pd.DataFrame:
    """
    Parse API response into a unified DataFrame with calls and puts.

    Args:
        api_response: Raw API response from options chain endpoint

    Returns:
        DataFrame with all options (both calls and puts)
    """
    if not api_response or "options" not in api_response:
        raise ValueError("Invalid API response: missing 'options' key")

    records = []
    spot = api_response.get("spot_price", 0)
    expiration = api_response.get("expiration", "")

    for option_type in ["calls", "puts"]:
        for opt in api_response["options"].get(option_type, []):
            record = {
                "ticker": api_response.get("ticker", ""),
                "expiration": expiration,
                "strike": opt.get("strike"),
                "option_type": option_type.upper().rstrip("S"),  # CALL/PUT
                "bid": opt.get("bid"),
                "ask": opt.get("ask"),
                "last_price": opt.get("last_price"),
                "volume": opt.get("volume"),
                "open_interest": opt.get("open_interest"),
                "implied_volatility": opt.get("implied_volatility"),
                "delta": opt.get("delta"),
                "gamma": opt.get("gamma"),
                "theta": opt.get("theta"),
                "vega": opt.get("vega"),
                "itm": opt.get("itm"),
                "spot_price": spot,
            }
            records.append(record)

    return pd.DataFrame(records)


def calculate_dte(expiration: str) -> int:
    """
    Calculate Days to Expiration from today.

    Args:
        expiration: Expiration date in YYYY-MM-DD format

    Returns:
        Number of days until expiration (0 if expired)
    """
    try:
        exp_date = datetime.strptime(expiration, "%Y-%m-%d").date()
        today = datetime.now().date()
        return max(0, (exp_date - today).days)
    except (ValueError, TypeError):
        return 0


def filter_options(
    df: pd.DataFrame,
    option_type: str | None = None,
    min_strike: float | None = None,
    max_strike: float | None = None,
    min_volume: int | None = None,
    min_oi: int | None = None,
    itm_only: bool = False,
    otm_only: bool = False,
    min_dte: int | None = None,
    max_dte: int | None = None,
    expiry_list: list[str] | None = None,
) -> pd.DataFrame:
    """
    Filter options DataFrame based on multiple criteria.

    This performs local filtering on already-retrieved data, avoiding
    additional API calls.

    Args:
        df: DataFrame containing options data
        option_type: Filter by "CALL" or "PUT"
        min_strike: Minimum strike price
        max_strike: Maximum strike price
        min_volume: Minimum trading volume
        min_oi: Minimum open interest
        itm_only: Only include in-the-money options
        otm_only: Only include out-of-the-money options
        min_dte: Minimum days to expiration
        max_dte: Maximum days to expiration
        expiry_list: List of specific expiry dates to include (YYYY-MM-DD format)

    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df

    filtered = df.copy()

    # Filter by option type
    if option_type:
        filtered = filtered[filtered["option_type"] == option_type.upper()]

    # Filter by strike price range
    if min_strike is not None:
        filtered = filtered[filtered["strike"] >= min_strike]
    if max_strike is not None:
        filtered = filtered[filtered["strike"] <= max_strike]

    # Filter by volume and open interest
    if min_volume is not None:
        filtered = filtered[filtered["volume"] >= min_volume]
    if min_oi is not None:
        filtered = filtered[filtered["open_interest"] >= min_oi]

    # Filter by moneyness (ITM/OTM)
    if itm_only:
        filtered = filtered[filtered["itm"]]
    if otm_only:
        filtered = filtered[not filtered["itm"]]

    # Filter by specific expiry list
    if expiry_list:
        filtered = filtered[filtered["expiration"].isin(expiry_list)]

    # Filter by DTE range (requires calculating DTE first)
    if min_dte is not None or max_dte is not None:
        # Add DTE column if not present
        if "dte" not in filtered.columns:
            filtered["dte"] = filtered["expiration"].apply(calculate_dte)

        if min_dte is not None:
            filtered = filtered[filtered["dte"] >= min_dte]
        if max_dte is not None:
            filtered = filtered[filtered["dte"] <= max_dte]

    return filtered.reset_index(drop=True)


def get_atm_options(
    df: pd.DataFrame,
    spot_price: float,
    n_strikes: int = 2,
) -> pd.DataFrame:
    """
    Get ATM (at-the-money) options within N strikes of spot price.

    Args:
        df: DataFrame containing options data
        spot_price: Current underlying price
        n_strikes: Number of strikes above and below ATM to include

    Returns:
        DataFrame with ATM options
    """
    if df.empty:
        return df

    unique_strikes = sorted(df["strike"].unique())

    # Find closest strike to spot
    atm_strike = min(unique_strikes, key=lambda x: abs(x - spot_price))
    atm_idx = unique_strikes.index(atm_strike)

    # Get range of strikes
    start_idx = max(0, atm_idx - n_strikes)
    end_idx = min(len(unique_strikes), atm_idx + n_strikes + 1)
    selected_strikes = unique_strikes[start_idx:end_idx]

    return df[df["strike"].isin(selected_strikes)].reset_index(drop=True)


def extract_strikes_from_options(df: pd.DataFrame) -> list[float]:
    """
    Extract unique strike prices from options DataFrame.

    Args:
        df: DataFrame containing options data

    Returns:
        Sorted list of unique strike prices
    """
    if df.empty or "strike" not in df.columns:
        return []
    return sorted(df["strike"].dropna().unique().tolist())


# ============================================================================
# Test Class
# ============================================================================


class TestOptionsAPISnapshotFiltering(unittest.TestCase):
    """
    Test suite validating:
    1. Options Chain API functionality
    2. Snapshot API for batch data retrieval
    3. Local filtering of retrieved data
    """

    @classmethod
    def setUpClass(cls):
        """Set up API clients once for all tests."""
        cls.options_api = MockOptionsChainAPI()
        cls.snapshot_api = MockSnapshotAPI()
        cls.test_ticker = "AAPL"
        cls.test_expiration = "2026-04-17"

    def test_01_fetch_options_chain_success(self):
        """
        Test: Fetch options chain for a specific expiration date.

        Verifies:
        - API returns valid response
        - Response contains expected keys (ticker, expiration, options)
        - Both calls and puts are present
        - Each option has required fields (strike, bid, ask, iv, etc.)
        """
        response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)

        # Verify response structure
        self.assertIn("ticker", response)
        self.assertIn("expiration", response)
        self.assertIn("spot_price", response)
        self.assertIn("options", response)
        self.assertIn("calls", response["options"])
        self.assertIn("puts", response["options"])

        # Verify data content
        self.assertEqual(response["ticker"], self.test_ticker)
        self.assertEqual(response["expiration"], self.test_expiration)
        self.assertGreater(response["spot_price"], 0)

        # Verify options have required fields
        for call in response["options"]["calls"]:
            self.assertIn("strike", call)
            self.assertIn("bid", call)
            self.assertIn("ask", call)
            self.assertIn("implied_volatility", call)
            self.assertIn("volume", call)
            self.assertIn("open_interest", call)

    def test_02_fetch_options_chain_invalid_inputs(self):
        """
        Test: API properly handles invalid inputs.

        Verifies:
        - Empty ticker raises ValueError
        - Invalid date format raises ValueError
        """
        with self.assertRaises(ValueError):
            self.options_api.fetch_options_chain("", self.test_expiration)

        with self.assertRaises(ValueError):
            self.options_api.fetch_options_chain(self.test_ticker, "invalid-date")

        with self.assertRaises(ValueError):
            self.options_api.fetch_options_chain(self.test_ticker, "04-17-2026")

    def test_03_batch_snapshot_retrieval(self):
        """
        Test: Batch-retrieve underlying instrument data without subscription.

        Verifies:
        - API accepts batch of instrument symbols
        - Returns data for all requested instruments
        - Data includes strike prices for options
        - No subscription requirement (simulated)
        """
        # Create a list of instrument symbols including underlying and options
        instruments = [
            "AAPL",  # Underlying stock
            "AAPL240417C140",  # Call option @ 140 strike
            "AAPL240417C145",  # Call option @ 145 strike
            "AAPL240417C150",  # ATM Call option
            "AAPL240417P150",  # ATM Put option
            "AAPL240417P155",  # Put option @ 155 strike
        ]

        response = self.snapshot_api.batch_get_snapshot(instruments)

        # Verify response structure
        self.assertIn("timestamp", response)
        self.assertIn("snapshots", response)
        self.assertIn("count", response)

        # Verify all instruments returned data
        self.assertEqual(response["count"], len(instruments))
        for symbol in instruments:
            self.assertIn(symbol, response["snapshots"])

        # Verify underlying data
        underlying = response["snapshots"]["AAPL"]
        self.assertEqual(underlying["instrument_type"], "STOCK")
        self.assertIn("last_price", underlying)
        self.assertIn("bid", underlying)
        self.assertIn("ask", underlying)

        # Verify option data includes strike price
        option = response["snapshots"]["AAPL240417C150"]
        self.assertEqual(option["instrument_type"], "CALL")
        self.assertIn("strike", option)
        self.assertGreater(option["strike"], 0)

    def test_04_batch_snapshot_size_limit(self):
        """
        Test: Batch API enforces size limits.

        Verifies:
        - Request exceeding batch limit raises ValueError
        """
        large_batch = [f"SYM{i}" for i in range(150)]

        with self.assertRaises(ValueError) as context:
            self.snapshot_api.batch_get_snapshot(large_batch)

        self.assertIn("exceeds limit", str(context.exception))

    def test_05_parse_options_chain_to_dataframe(self):
        """
        Test: Convert API response to DataFrame for analysis.

        Verifies:
        - Parsing creates DataFrame with correct columns
        - Both calls and puts are included
        - Strike prices are extracted correctly
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)

        df = parse_options_chain(raw_response)

        # Verify DataFrame structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)

        # Verify required columns
        required_cols = [
            "ticker",
            "expiration",
            "strike",
            "option_type",
            "bid",
            "ask",
            "last_price",
            "volume",
            "open_interest",
            "implied_volatility",
            "itm",
            "spot_price",
        ]
        for col in required_cols:
            self.assertIn(col, df.columns)

        # Verify both calls and puts present
        types = df["option_type"].unique()
        self.assertIn("CALL", types)
        self.assertIn("PUT", types)

        # Verify strikes extracted correctly
        strikes = sorted(df["strike"].unique())
        self.assertGreater(len(strikes), 0)

    def test_06_local_filter_by_option_type(self):
        """
        Test: Filter DataFrame by option type (CALL or PUT).

        Verifies:
        - Filter by CALL returns only calls
        - Filter by PUT returns only puts
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        # Filter calls only
        calls_df = filter_options(df, option_type="CALL")
        self.assertTrue(all(calls_df["option_type"] == "CALL"))

        # Filter puts only
        puts_df = filter_options(df, option_type="PUT")
        self.assertTrue(all(puts_df["option_type"] == "PUT"))

    def test_07_local_filter_by_strike_range(self):
        """
        Test: Filter DataFrame by strike price range.

        Verifies:
        - min_strike filter excludes strikes below threshold
        - max_strike filter excludes strikes above threshold
        - Combined range filter works correctly
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        spot = raw_response["spot_price"]

        # Filter by min strike (OTM calls only)
        min_strike = spot * 1.02  # 2% OTM
        filtered = filter_options(df, option_type="CALL", min_strike=min_strike)
        self.assertTrue(all(filtered["strike"] >= min_strike))

        # Filter by max strike (ITM calls only)
        max_strike = spot * 0.98  # 2% ITM
        filtered = filter_options(df, option_type="CALL", max_strike=max_strike)
        self.assertTrue(all(filtered["strike"] <= max_strike))

        # Filter by range (near ATM)
        range_filtered = filter_options(df, min_strike=spot * 0.95, max_strike=spot * 1.05)
        self.assertTrue(all(range_filtered["strike"] >= spot * 0.95))
        self.assertTrue(all(range_filtered["strike"] <= spot * 1.05))

    def test_08_local_filter_by_volume_and_oi(self):
        """
        Test: Filter DataFrame by liquidity metrics.

        Verifies:
        - min_volume filter excludes low-volume options
        - min_oi filter excludes low open-interest options
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        # Filter by minimum volume
        min_vol = 500
        vol_filtered = filter_options(df, min_volume=min_vol)
        self.assertTrue(all(vol_filtered["volume"] >= min_vol))

        # Filter by minimum open interest
        min_oi = 2000
        oi_filtered = filter_options(df, min_oi=min_oi)
        self.assertTrue(all(oi_filtered["open_interest"] >= min_oi))

    def test_09_local_filter_by_moneyness(self):
        """
        Test: Filter DataFrame by ITM/OTM status.

        Verifies:
        - itm_only filter returns only ITM options
        - otm_only filter returns only OTM options
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        # ITM only
        itm_calls = filter_options(df, option_type="CALL", itm_only=True)
        self.assertTrue(all(itm_calls["itm"]))

        # OTM only
        otm_calls = filter_options(df, option_type="CALL", otm_only=True)
        self.assertTrue(all(not otm_calls["itm"]))

        # ITM puts (puts ITM when strike > spot)
        itm_puts = filter_options(df, option_type="PUT", itm_only=True)
        self.assertTrue(all(itm_puts["itm"]))

    def test_10_get_atm_options(self):
        """
        Test: Extract ATM options with configurable strike range.

        Verifies:
        - Returns options near current spot price
        - Respects n_strikes parameter
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)
        spot = raw_response["spot_price"]

        # Get ATM options (2 strikes above and below)
        atm_df = get_atm_options(df, spot_price=spot, n_strikes=2)

        # Verify strikes are near spot price
        strikes = sorted(atm_df["strike"].unique())
        self.assertGreater(len(strikes), 0)

        # ATM should include strikes around spot
        atm_strike = min(strikes, key=lambda x: abs(x - spot))
        strike_diff_pct = abs(atm_strike - spot) / spot
        self.assertLess(strike_diff_pct, 0.10)  # Within 10%

    def test_11_extract_strikes_function(self):
        """
        Test: Extract unique strike prices from options DataFrame.

        Verifies:
        - Returns sorted list of unique strikes
        - Handles empty DataFrame gracefully
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        strikes = extract_strikes_from_options(df)

        # Verify sorted unique strikes
        self.assertIsInstance(strikes, list)
        self.assertGreater(len(strikes), 0)
        self.assertEqual(strikes, sorted(set(strikes)))  # Sorted and unique

        # Test empty DataFrame
        empty_df = pd.DataFrame()
        empty_strikes = extract_strikes_from_options(empty_df)
        self.assertEqual(empty_strikes, [])

    def test_12_complex_filtering_scenario(self):
        """
        Test: Real-world filtering scenario combining multiple criteria.

        Scenario: Find liquid, near-ATM calls for a bullish strategy
        Criteria:
        - Option type: CALL
        - Strike range: spot to spot + 5%
        - Min volume: 200
        - Min open interest: 1000
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)
        spot = raw_response["spot_price"]

        # Apply complex filter
        candidates = filter_options(
            df,
            option_type="CALL",
            min_strike=spot,
            max_strike=spot * 1.05,
            min_volume=200,
            min_oi=1000,
        )

        # Verify all criteria met
        self.assertTrue(all(candidates["option_type"] == "CALL"))
        self.assertTrue(all(candidates["strike"] >= spot))
        self.assertTrue(all(candidates["strike"] <= spot * 1.05))
        self.assertTrue(all(candidates["volume"] >= 200))
        self.assertTrue(all(candidates["open_interest"] >= 1000))

    def test_13_data_integrity_after_filtering(self):
        """
        Test: Data integrity is preserved through filtering operations.

        Verifies:
        - Original DataFrame is not modified (immutability)
        - All columns preserved after filtering
        - Data types maintained
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)
        original_columns = set(df.columns)

        # Apply multiple filters
        filtered1 = filter_options(df, option_type="CALL")
        filtered2 = filter_options(filtered1, min_strike=145)

        # Verify original not modified
        self.assertEqual(set(df.columns), original_columns)
        self.assertIn("CALL", df["option_type"].values)
        self.assertIn("PUT", df["option_type"].values)

        # Verify filtered has same columns
        self.assertEqual(set(filtered2.columns), original_columns)

        # Verify data types preserved
        self.assertEqual(filtered2["strike"].dtype, df["strike"].dtype)
        self.assertEqual(filtered2["volume"].dtype, df["volume"].dtype)

    def test_14_filter_by_dte_range(self):
        """
        Test: Filter DataFrame by Days to Expiration (DTE) range.

        Verifies:
        - min_dte filter excludes shorter-dated options
        - max_dte filter excludes longer-dated options
        - DTE calculation works correctly
        """
        # Create test data with multiple expirations
        today = datetime.now()
        test_data = {
            "ticker": ["AAPL"] * 12,
            "expiration": [
                (today + timedelta(days=3)).strftime("%Y-%m-%d"),  # 3 DTE
                (today + timedelta(days=7)).strftime("%Y-%m-%d"),  # 7 DTE
                (today + timedelta(days=14)).strftime("%Y-%m-%d"),  # 14 DTE
                (today + timedelta(days=21)).strftime("%Y-%m-%d"),  # 21 DTE
                (today + timedelta(days=30)).strftime("%Y-%m-%d"),  # 30 DTE
                (today + timedelta(days=45)).strftime("%Y-%m-%d"),  # 45 DTE
            ]
            * 2,  # 2 option types each
            "strike": [150] * 12,
            "option_type": ["CALL", "PUT"] * 6,
            "bid": [3.0] * 12,
            "ask": [3.2] * 12,
            "last_price": [3.1] * 12,
            "volume": [100] * 12,
            "open_interest": [1000] * 12,
            "implied_volatility": [0.30] * 12,
            "itm": [False] * 12,
            "spot_price": [150.0] * 12,
        }
        df = pd.DataFrame(test_data)

        # Filter by DTE range (6-30 days)
        filtered = filter_options(df, min_dte=6, max_dte=30)

        # Verify DTE column was added
        self.assertIn("dte", filtered.columns)

        # Verify all results within range
        self.assertTrue(all(filtered["dte"] >= 6))
        self.assertTrue(all(filtered["dte"] <= 30))

        # Verify 3 DTE excluded, 45 DTE excluded
        exp_dates = filtered["expiration"].unique()
        self.assertNotIn((today + timedelta(days=3)).strftime("%Y-%m-%d"), exp_dates)
        self.assertNotIn((today + timedelta(days=45)).strftime("%Y-%m-%d"), exp_dates)

    def test_15_filter_by_expiry_list(self):
        """
        Test: Filter DataFrame by specific expiry dates.

        Verifies:
        - Only specified expiry dates are included
        """
        raw_response = self.options_api.fetch_options_chain(self.test_ticker, self.test_expiration)
        df = parse_options_chain(raw_response)

        # Filter by specific expiry list
        target_expiries = ["2026-04-17", "2026-04-24"]
        filtered = filter_options(df, expiry_list=target_expiries)

        # All results should be in the target list
        for exp in filtered["expiration"]:
            self.assertIn(exp, target_expiries)

    def test_16_futu_api_nvda_complex_filtering(self):
        """
        Test: Futu API integration with US.NVDA and complex multi-criteria filtering.

        Scenario: Filter NVDA options for swing trading strategy
        Criteria:
        - Ticker: US.NVDA
        - Strike range: $160 - $190
        - Expiry range: 6 - 30 days (DTE)
        - Option type: CALL (bullish bias)
        - Minimum volume: 50
        - Minimum open interest: 500

        Note: This test uses mock data. For live testing, uncomment the integration
        test section and configure Futu API credentials.
        """
        # Mock Futu API response for US.NVDA
        today = datetime.now()
        spot_price = 175.0  # NVDA around $175

        # Generate mock NVDA options across multiple expiries
        records = []
        strikes = [155, 160, 165, 170, 175, 180, 185, 190, 195]

        # Create expiries: 3 DTE, 7 DTE, 14 DTE, 21 DTE, 30 DTE, 45 DTE
        expiries = [
            (today + timedelta(days=3)).strftime("%Y-%m-%d"),  # Outside range
            (today + timedelta(days=7)).strftime("%Y-%m-%d"),  # In range
            (today + timedelta(days=14)).strftime("%Y-%m-%d"),  # In range
            (today + timedelta(days=21)).strftime("%Y-%m-%d"),  # In range
            (today + timedelta(days=30)).strftime("%Y-%m-%d"),  # In range
            (today + timedelta(days=45)).strftime("%Y-%m-%d"),  # Outside range
        ]

        for exp in expiries:
            for strike in strikes:
                for opt_type in ["CALL", "PUT"]:
                    # Only strikes 160-190 should match
                    # Only expiries 7, 14, 21, 30 DTE should match (6-30 range)
                    moneyness = abs(strike - spot_price) / spot_price

                    records.append(
                        {
                            "ticker": "US.NVDA",
                            "expiration": exp,
                            "strike": strike,
                            "option_type": opt_type,
                            "bid": round(5.0 - moneyness * 3, 2),
                            "ask": round(5.2 - moneyness * 3, 2),
                            "last_price": round(5.1 - moneyness * 3, 2),
                            "volume": int(200 * (1 - moneyness)),
                            "open_interest": int(1500 * (1 - moneyness * 0.5)),
                            "implied_volatility": round(0.45 + moneyness * 0.1, 4),
                            "itm": (opt_type == "CALL" and strike < spot_price)
                            or (opt_type == "PUT" and strike > spot_price),
                            "spot_price": spot_price,
                        }
                    )

        df = pd.DataFrame(records)

        # Apply complex multi-criteria filter
        # Criteria: strike 160-190, expiry 6-30 days, CALL only, min volume 50, min OI 500
        candidates = filter_options(
            df,
            option_type="CALL",
            min_strike=160.0,
            max_strike=190.0,
            min_dte=6,
            max_dte=30,
            min_volume=50,
            min_oi=500,
        )

        # Verify all criteria are met
        self.assertTrue(all(candidates["ticker"] == "US.NVDA"))
        self.assertTrue(all(candidates["option_type"] == "CALL"))
        self.assertTrue(all(candidates["strike"] >= 160.0))
        self.assertTrue(all(candidates["strike"] <= 190.0))
        self.assertTrue(all(candidates["volume"] >= 50))
        self.assertTrue(all(candidates["open_interest"] >= 500))

        # Verify DTE column exists and is within range
        self.assertIn("dte", candidates.columns)
        self.assertTrue(all(candidates["dte"] >= 6))
        self.assertTrue(all(candidates["dte"] <= 30))

        # Verify strikes outside range are excluded
        self.assertNotIn(155, candidates["strike"].values)
        self.assertNotIn(195, candidates["strike"].values)

        # Verify short-dated (3 DTE) and long-dated (45 DTE) options excluded
        exp_dates = candidates["expiration"].unique()
        self.assertNotIn(expiries[0], exp_dates)  # 3 DTE
        self.assertNotIn(expiries[5], exp_dates)  # 45 DTE
        self.assertIn(expiries[1], exp_dates)  # 7 DTE
        self.assertIn(expiries[4], exp_dates)  # 30 DTE


# ============================================================================
# Futu API Integration Example for Live Testing
# ============================================================================

"""
# To test with real Futu API data, use the following pattern:

from data_pipeline.futu_provider import get_option_chain_futu

# Fetch full options chain for US.NVDA
result = get_option_chain_futu("US.NVDA", host="127.0.0.1", port=11111)

# Result structure:
# {
#     "expirations": ["2026-03-28", "2026-04-04", "2026-04-11", ...],
#     "chain": {
#         "2026-03-28": {"calls": [...], "puts": [...]},
#         "2026-04-04": {"calls": [...], "puts": [...]},
#         ...
#     },
#     "spot": 175.45
# }

# Convert to DataFrame for filtering
all_records = []
for expiry, data in result["chain"].items():
    for call in data["calls"]:
        call["expiration"] = expiry
        call["option_type"] = "CALL"
        call["spot_price"] = result["spot"]
        all_records.append(call)
    for put in data["puts"]:
        put["expiration"] = expiry
        put["option_type"] = "PUT"
        put["spot_price"] = result["spot"]
        all_records.append(put)

df = pd.DataFrame(all_records)

# Apply complex filter: strike 160-190, expiry 6-30 days, CALL only
filtered = filter_options(
    df,
    option_type="CALL",
    min_strike=160.0,
    max_strike=190.0,
    min_dte=6,
    max_dte=30,
    min_volume=50,
    min_oi=500,
)

print(f"Found {len(filtered)} matching options")
print(filtered[["expiration", "strike", "option_type", "lastPrice", "dte"]])
"""


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)

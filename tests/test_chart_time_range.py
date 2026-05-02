#!/usr/bin/env python3
"""
Test script to verify that charts use the full time range defined by the Horizon parameter.
"""

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from core.market_analyzer import MarketAnalyzer


# WHY: these tests hit live yfinance and are therefore subject to rate-limiting.
# They provide valuable end-to-end validation but should not block CI.
pytestmark = pytest.mark.network


_TEST_CASES = [
    {
        "ticker": "AAPL",
        "start": dt.date(2020, 1, 1),
        "end": dt.date(2024, 1, 1),
        "frequency": "W",
        "expected_min_points": 200,
        "description": "4-year Weekly data for AAPL",
    },
    {
        "ticker": "SPY",
        "start": dt.date(2019, 1, 1),
        "end": dt.date(2024, 1, 1),
        "frequency": "W",
        "expected_min_points": 250,
        "description": "5-year Weekly data for SPY",
    },
    {
        "ticker": "MSFT",
        "start": dt.date(2021, 1, 1),
        "end": dt.date(2023, 12, 31),
        "frequency": "ME",
        "expected_min_points": 30,
        "description": "3-year Monthly data for MSFT",
    },
]


def _run_single_case(test_case: dict) -> None:
    """Assert that a single test case produces sufficient data points and charts."""
    analyzer = MarketAnalyzer(
        ticker=test_case["ticker"],
        start_date=test_case["start"],
        frequency=test_case["frequency"],
        end_date=test_case["end"],
    )

    assert analyzer.is_data_valid(), (
        f"{test_case['description']}: No valid data returned"
    )

    df = analyzer.features_df
    num_points = len(df)
    expected_min = test_case["expected_min_points"]

    assert num_points >= expected_min, (
        f"{test_case['description']}: Only {num_points} points "
        f"(expected at least {expected_min})"
    )

    osc_std = df["Oscillation"].std()
    assert osc_std >= 0.1, (
        f"{test_case['description']}: Oscillation std={osc_std:.4f} too low"
    )

    assert analyzer.generate_scatter_plots("Oscillation"), "Scatter plot failed"
    assert analyzer.generate_high_low_scatter(), "HL scatter failed"
    assert analyzer.generate_return_osc_high_low_chart(), "Return-osc chart failed"
    assert analyzer.generate_volatility_dynamics(), "Volatility chart failed"
    proj, proj_table = analyzer.generate_oscillation_projection()
    assert proj and proj_table, "Projection chart/table failed"


@pytest.mark.parametrize("case", _TEST_CASES, ids=lambda c: c["description"])
def test_full_time_range(case):
    """Test that charts use full time range, not just last data point."""
    _run_single_case(case)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

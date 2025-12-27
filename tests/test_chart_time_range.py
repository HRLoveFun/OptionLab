#!/usr/bin/env python3
"""
Test script to verify that charts use the full time range defined by the Horizon parameter.

This test ensures that the fix for the issue where all output charts only used 
a single (last) data point is working correctly.
"""

import sys
import os
import datetime as dt

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.market_analyzer import MarketAnalyzer

def test_full_time_range():
    """Test that charts use full time range, not just last data point"""
    
    test_cases = [
        {
            'ticker': 'AAPL',
            'start': dt.date(2020, 1, 1),
            'end': dt.date(2024, 1, 1),
            'frequency': 'W',
            'expected_min_points': 200,  # ~4 years of weekly data
            'description': '4-year Weekly data for AAPL'
        },
        {
            'ticker': 'SPY',
            'start': dt.date(2019, 1, 1),
            'end': dt.date(2024, 1, 1),
            'frequency': 'W',
            'expected_min_points': 250,  # ~5 years of weekly data
            'description': '5-year Weekly data for SPY'
        },
        {
            'ticker': 'MSFT',
            'start': dt.date(2021, 1, 1),
            'end': dt.date(2023, 12, 31),
            'frequency': 'ME',
            'expected_min_points': 30,  # ~3 years of monthly data
            'description': '3-year Monthly data for MSFT'
        },
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test_case['description']}")
        print(f"{'='*70}")
        
        try:
            analyzer = MarketAnalyzer(
                ticker=test_case['ticker'],
                start_date=test_case['start'],
                frequency=test_case['frequency'],
                end_date=test_case['end']
            )
            
            if not analyzer.is_data_valid():
                print(f"❌ FAILED: No valid data returned")
                all_passed = False
                continue
            
            # Check number of data points
            df = analyzer.features_df
            num_points = len(df)
            expected_min = test_case['expected_min_points']
            
            print(f"\nData Points: {num_points}")
            print(f"Expected Minimum: {expected_min}")
            print(f"Date Range: {df.index[0].date()} to {df.index[-1].date()}")
            
            if num_points < expected_min:
                print(f"❌ FAILED: Only {num_points} points (expected at least {expected_min})")
                all_passed = False
                continue
            
            # Check data variation (not just single point)
            osc_std = df['Oscillation'].std()
            if osc_std < 0.1:
                print(f"❌ FAILED: Oscillation std={osc_std:.4f} too low (data might be single point)")
                all_passed = False
                continue
            
            # Test chart generation
            charts_ok = True
            
            scatter = analyzer.generate_scatter_plots('Oscillation')
            if not scatter:
                print("❌ Scatter plot failed")
                charts_ok = False
            
            hl_scatter = analyzer.generate_high_low_scatter()
            if not hl_scatter:
                print("❌ HL scatter failed")
                charts_ok = False
            
            ret_osc = analyzer.generate_return_osc_high_low_chart()
            if not ret_osc:
                print("❌ Return-osc chart failed")
                charts_ok = False
            
            vol = analyzer.generate_volatility_dynamics()
            if not vol:
                print("❌ Volatility chart failed")
                charts_ok = False
            
            proj, proj_table = analyzer.generate_oscillation_projection()
            if not proj or not proj_table:
                print("❌ Projection chart/table failed")
                charts_ok = False
            
            if charts_ok:
                print("\n✅ PASSED: All charts generated successfully")
                print(f"   - {num_points} data points covering full time range")
                print(f"   - Oscillation std: {osc_std:.2f}% (shows variation)")
            else:
                print("\n❌ FAILED: Some charts failed to generate")
                all_passed = False
                
        except Exception as e:
            print(f"❌ FAILED: Exception occurred: {e}")
            all_passed = False
    
    print(f"\n{'='*70}")
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("Charts correctly use full time range defined by Horizon parameter")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please review the failures above")
    print(f"{'='*70}\n")
    
    return all_passed

if __name__ == "__main__":
    import sys
    success = test_full_time_range()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""Small CLI to seed historical data for a ticker into the pipeline DB.

Usage: python scripts/seed_history.py AAPL 5
"""
import sys
import logging
import datetime as dt

from data_pipeline.data_service import DataService

logging.basicConfig(level=logging.INFO)

def main():
    if len(sys.argv) < 2:
        print("Usage: seed_history.py <TICKER> [YEARS]")
        sys.exit(2)
    ticker = sys.argv[1]
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(f"Seeding {years} years for {ticker}...")
    DataService.seed_history(ticker, years=years)
    print("Done")

if __name__ == '__main__':
    main()

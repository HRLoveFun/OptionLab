"""
Data pipeline package for downloading, cleaning, processing, and serving
market data via a local SQLite database.

Modules:
- db: DB initialization and CRUD helpers
- downloader: Fetch from providers (yfinance) and upsert into DB
- cleaning: Time-series alignment, missing handling, anomaly flags
- processing: Derived features across frequencies (daily/weekly/monthly)
- data_service: Facade used by app code to fetch data with manual/auto updates
- scheduler: Optional daily auto-update scheduler (16:15 local time)
"""

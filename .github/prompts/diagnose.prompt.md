---
description: "Quick diagnosis of data pipeline issues: why is a ticker showing empty data, stale charts, or errors?"
agent: "agent"
tools: [read, search, execute]
argument-hint: "Ticker symbol or symptom (e.g., 'NVDA empty charts', 'stale TLT data')"
---

Diagnose why a specific ticker's data is missing, stale, or showing errors in the OptionView dashboard.

Steps:
1. Check the DB for the ticker: query `raw_prices`, `clean_prices`, `processed_prices` for recent rows
2. Look for NaN-only filler rows (root cause of empty charts)
3. Check yfinance download logs for errors (429, timeout)
4. Trace data flow through the 5-stage pipeline to find the failure point
5. Report: which stage failed, why, and how to fix it

Use `sqlite3 market_data.sqlite` to query the database directly.

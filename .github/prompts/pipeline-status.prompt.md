---
description: "Check data pipeline health: DB row counts, recent download timestamps, NaN-only rows, and data freshness for all or specific tickers."
agent: "agent"
tools: [read, execute]
argument-hint: "Optional: specific ticker to check (default: all tickers)"
---

Check the current health of the OptionView data pipeline:

1. Query the SQLite database (`market_data.sqlite`) for:
   ```sql
   -- Row counts per table
   SELECT 'raw_bars' as tbl, count(*) as rows FROM raw_bars
   UNION SELECT 'clean_bars', count(*) FROM clean_bars
   UNION SELECT 'feature_bars', count(*) FROM feature_bars;

   -- Latest data per ticker
   SELECT ticker, MAX(date) as latest, COUNT(*) as rows FROM raw_bars GROUP BY ticker;

   -- NaN-only filler rows (problematic)
   SELECT ticker, count(*) as nan_rows FROM raw_bars
   WHERE open IS NULL AND high IS NULL AND low IS NULL AND close IS NULL
   GROUP BY ticker HAVING nan_rows > 0;

   -- Data freshness (days since last update)
   SELECT ticker, MAX(date) as latest,
          julianday('now') - julianday(MAX(date)) as days_stale
   FROM raw_bars GROUP BY ticker ORDER BY days_stale DESC;
   ```

2. Report:
   - Total rows per table
   - Per-ticker data freshness
   - Any NaN-only filler rows that need cleanup
   - Any tickers with suspiciously stale data (>3 trading days)

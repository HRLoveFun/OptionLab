import datetime as dt
import logging
import os

import pandas as pd
import yfinance as yf

from utils.utils import yf_throttle

from . import PipelineResult
from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)

# Maximum window the gap-aware downloader will auto-expand to. Larger ranges
# require explicit `DataService.seed_history` to avoid runaway yfinance load
# after a long outage.
MAX_AUTO_BACKFILL_DAYS = int(os.environ.get("MAX_AUTO_BACKFILL_DAYS", "90"))


def find_missing_business_days(ticker: str, start: dt.date, end: dt.date) -> list[dt.date]:
    """Return business days in [start, end] (inclusive) that have no row in raw_prices.

    Uses the same Mon-Fri business-day calendar as `cleaning._get_business_days`
    so gaps map 1:1 with cleaning's expected index. Holidays are intentionally
    NOT excluded — they will appear as harmless empty download attempts.
    """
    expected = pd.bdate_range(start, end)
    if len(expected) == 0:
        return []
    df = fetch_df(
        "SELECT date FROM raw_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    have: set[dt.date] = set()
    # NOTE: `df.empty` is True for a (N rows, 0 cols) frame, which is exactly
    # what `fetch_df` returns for a SELECT-only-date query (the date column is
    # promoted to the index). Check `len(df.index)` instead.
    if len(df.index) > 0:
        for ts in df.index:
            try:
                have.add(pd.Timestamp(ts).date())
            except (ValueError, TypeError):
                continue
    return [ts.date() for ts in expected if ts.date() not in have]


def _download_yf(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    # yfinance 'end' is exclusive, so pass end + 1 day to include the requested end date
    yf_end = end + dt.timedelta(days=1)
    yf_throttle()
    df = yf.download(ticker, start=start, end=yf_end, interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    cols = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    for c in cols:
        if c not in df.columns:
            df[c] = pd.NA
    return df[cols].rename(columns={"Adj Close": "Adj_Close"})


def upsert_raw_prices(
    ticker: str, start: dt.date | None = None, end: dt.date | None = None, days: int = 7
) -> PipelineResult:
    """
    Download OHLCV for [start, end) and upsert into raw_prices.
    If df for a day is entirely NA, skip and keep existing row.
    Returns a PipelineResult with row count and any warnings.
    """
    result = PipelineResult()
    # Interpret end as inclusive date
    end = end or dt.date.today()
    # If start is None, include the past `days` calendar days ending at `end` inclusive
    if start is None:
        start = end - dt.timedelta(days=days - 1)

    # ── Gap-aware coverage check ──
    # Skip the network only when every business day in [start, end] is already
    # present in raw_prices. Otherwise expand the download range to cover the
    # earliest gap so back-fills happen automatically after an outage.
    missing = find_missing_business_days(ticker, start, end)
    if not missing:
        logger.debug(f"DB data for {ticker} fully covers {start}..{end}; skipping download")
        result.warnings.append(f"Skipped download: full coverage in {start}..{end}")
        return result

    # Expand start to the earliest missing business day. Cap the auto-expansion
    # so a multi-year outage does not silently trigger a giant download — those
    # cases must use `DataService.seed_history` explicitly.
    gap_start = min(missing)
    effective_start = min(start, gap_start)
    if (end - effective_start).days > MAX_AUTO_BACKFILL_DAYS:
        capped_start = end - dt.timedelta(days=MAX_AUTO_BACKFILL_DAYS)
        logger.warning(
            f"Gap for {ticker} spans {(end - effective_start).days}d (>{MAX_AUTO_BACKFILL_DAYS}); "
            f"capping backfill at {capped_start}. Use seed_history for older data."
        )
        result.warnings.append(
            f"Backfill capped at {MAX_AUTO_BACKFILL_DAYS} days; oldest gaps require seed_history"
        )
        effective_start = capped_start
    if effective_start != start:
        logger.info(f"Expanding download range for {ticker}: {start}..{end} → {effective_start}..{end}")
        start = effective_start

    try:
        df_new = _download_yf(ticker, start, end)
    except Exception as e:
        logger.error(f"Download failed for {ticker}: {e}", exc_info=True)
        return PipelineResult(ok=False, error=f"download_failed: {e}")
    if df_new.empty:
        logger.info(f"No new data for {ticker} between {start} and {end}")
        result.warnings.append(f"No new data for {ticker} between {start} and {end}")
        return result

    df_new = df_new.copy()
    df_new.index = pd.DatetimeIndex(df_new.index).tz_localize(None)
    df_new["date"] = df_new.index.date

    # Load existing for comparison (inclusive end)
    df_old = fetch_df(
        "SELECT * FROM raw_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    if not df_old.empty:
        df_old = df_old.rename(columns={"adj_close": "Adj_Close"})

    rows = []
    for _d, row in df_new.iterrows():
        date_str = row["date"].isoformat()
        # If all new values are NA, retain old data (skip insert) and log
        if row[["Open", "High", "Low", "Close", "Adj_Close", "Volume"]].isna().all():
            msg = f"Blank data for {ticker} on {date_str}; retaining old data if exists"
            logger.warning(msg)
            result.warnings.append(msg)
            continue
        tup = (
            ticker,
            date_str,
            float(row.get("Open", pd.NA)) if pd.notna(row.get("Open")) else None,
            float(row.get("High", pd.NA)) if pd.notna(row.get("High")) else None,
            float(row.get("Low", pd.NA)) if pd.notna(row.get("Low")) else None,
            float(row.get("Close", pd.NA)) if pd.notna(row.get("Close")) else None,
            float(row.get("Adj_Close", pd.NA)) if pd.notna(row.get("Adj_Close")) else None,
            float(row.get("Volume", pd.NA)) if pd.notna(row.get("Volume")) else None,
            "yfinance",
        )
        rows.append(tup)

    if rows:
        upsert_many(
            "raw_prices",
            [
                "ticker",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "provider",
            ],
            rows,
        )
    result.rows = len(rows)
    return result

import datetime as dt
import logging

import pandas as pd
import yfinance as yf

from utils.utils import yf_throttle

from . import PipelineResult
from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)


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

    # ── Staleness check: skip download if DB already has recent data ──
    existing = fetch_df(
        "SELECT MAX(date) as max_date FROM raw_prices WHERE ticker=?",
        (ticker,),
    )
    if not existing.empty and existing.iloc[0]["max_date"] is not None:
        max_date_str = existing.iloc[0]["max_date"]
        try:
            max_date = dt.date.fromisoformat(max_date_str)
            # Consider data fresh if latest row is within 1 calendar day of requested end
            if max_date >= end - dt.timedelta(days=1):
                logger.debug(f"DB data for {ticker} is fresh (max_date={max_date}), skipping download")
                result.warnings.append(f"Skipped download: DB data fresh (max_date={max_date})")
                return result
        except (ValueError, TypeError):
            pass  # Can't parse date, proceed with download

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

"""Market data downloader: business-day gap detection + raw OHLCV upsert.

Domain:    Data Pipeline — Ingest Glue
Context:
  - Acquisition itself lives in ``data_pipeline/providers/``. This module keeps
    only the DB-aware parts: business-day gap detection, the auto-backfill cap,
    and the ``raw_bars`` upsert. Batch B1 (see
    docs/plans/business_line_reorg.md §6) moved the ``yf.download`` call behind
    ``providers.yfinance_provider.download_daily_frame``, so this module no
    longer imports yfinance.
Contracts:
  - ``upsert_raw_prices(ticker, start, end, days) -> PipelineResult`` — never
    raises; degraded outcomes are reported through the ``PipelineResult``.
  - ``find_missing_business_days(ticker, start, end) -> list[date]``
Dependencies UPWARD:
  - providers.yfinance_provider (download), .db (fetch_df / upsert_many)
Dependencies DOWNWARD:
  - data_pipeline/data_ops (_update / _range), services/regime/ops/_bootstrap.py
"""

import datetime as dt
import logging
import os
from pathlib import Path

import pandas as pd

from data_pipeline.providers import get_provider
from data_pipeline.providers.base import CANONICAL_BAR_COLUMNS
from data_pipeline.providers.yfinance_provider import to_canonical_bars

from . import PipelineResult
from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)

# DOMAIN / CONSTRAINT: cap on how far back the gap-aware downloader will
# auto-expand. Larger ranges require explicit ``DataService.seed_history``
# to avoid runaway yfinance load (and 429s) after a long outage.
# See docs/constraints.md §2 / ADR 0005.
MAX_AUTO_BACKFILL_DAYS = int(os.environ.get("MAX_AUTO_BACKFILL_DAYS", "90"))

# WHY: Local fixture directory for ``TEST_*`` tickers. Tests should never
# hit the network — routing TEST_* through this fixture also keeps the
# global yfinance throttle uncontended for real tickers during test runs.
_FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "yf"


def _last_business_day_on_or_before(d: dt.date) -> dt.date:
    """Snap ``d`` back to the most recent Mon–Fri (inclusive)."""
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= dt.timedelta(days=1)
    return d


def _load_test_fixture(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Synthesise OHLCV for ``TEST_*`` tickers without touching the network.

    Matches the yfinance column shape (Title Case + ``Adj_Close``) so the
    canonical mapping is exercised identically for fixtures and real downloads.
    If a CSV exists at ``tests/fixtures/yf/<TICKER>.csv`` it is used verbatim;
    otherwise a deterministic synthetic series is generated.
    """
    csv_path = _FIXTURE_DIR / f"{ticker}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["Date"]).set_index("Date")
        df = df.loc[(df.index >= pd.Timestamp(start)) & (df.index <= pd.Timestamp(end))]
        return df

    idx = pd.bdate_range(start, end)
    if len(idx) == 0:
        return pd.DataFrame()
    base = 100.0 + (sum(ord(c) for c in ticker) % 50)
    closes = [base + i * 0.1 for i in range(len(idx))]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 0.5 for c in closes],
            "Low": [c - 0.5 for c in closes],
            "Close": closes,
            "Adj_Close": closes,
            "Volume": [1_000_000] * len(idx),
        },
        index=idx,
    )
    return df


def find_missing_business_days(ticker: str, start: dt.date, end: dt.date) -> list[dt.date]:
    """Return business days in [start, end] (inclusive) that have no row in raw_bars.

    Uses the same Mon-Fri business-day calendar as `cleaning._get_business_days`
    so gaps map 1:1 with cleaning's expected index. Holidays are intentionally
    NOT excluded — they will appear as harmless empty download attempts.
    """
    expected = pd.bdate_range(start, end)
    if len(expected) == 0:
        return []
    df = fetch_df(
        "SELECT date FROM raw_bars WHERE ticker=? AND date>=? AND date<=?",
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


def download_bars(ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    """Acquire daily bars for ``[start, end]`` (inclusive) in the canonical schema.

    ``TEST_*`` tickers never hit the network (useful for unit tests + ad-hoc
    smoke tests under rate-limit conditions; see ``_load_test_fixture``).
    Everything else goes through the provider registry, which returns canonical
    bars already (ADR 0011).
    """
    if ticker.startswith("TEST_"):
        logger.info("Loading fixture data for test ticker %s (%s..%s)", ticker, start, end)
        # WHY the yfinance mapper for fixtures: the fixture frames deliberately
        # mimic `yf.download`'s Title-Case shape, so they need the same mapping
        # the provider applies to a real download.
        return to_canonical_bars(_load_test_fixture(ticker, start, end))
    return get_provider().history(ticker, start, end)


def upsert_raw_prices(
    ticker: str, start: dt.date | None = None, end: dt.date | None = None, days: int = 7
) -> PipelineResult:
    """
    Download OHLCV for [start, end) and upsert into raw_bars (canonical store).
    If df for a day is entirely NA, skip and keep existing row.
    Returns a PipelineResult with row count and any warnings.
    """
    result = PipelineResult()
    # Interpret end as inclusive date
    end = end or dt.date.today()
    # Weekend short-circuit: Yahoo only publishes data for trading days, so
    # snap a Sat/Sun `end` back to the most recent Friday before computing
    # gaps. Avoids spurious "no new data" downloads on weekend page loads.
    end = _last_business_day_on_or_before(end)
    # If start is None, include the past `days` calendar days ending at `end` inclusive
    if start is None:
        start = end - dt.timedelta(days=days - 1)

    # ── Gap-aware coverage check ──
    # Skip the network only when every business day in [start, end] is already
    # present in raw_bars. Otherwise expand the download range to cover the
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
        result.warnings.append(f"Backfill capped at {MAX_AUTO_BACKFILL_DAYS} days; oldest gaps require seed_history")
        effective_start = capped_start
    if effective_start != start:
        logger.info(f"Expanding download range for {ticker}: {start}..{end} → {effective_start}..{end}")
        start = effective_start

    try:
        df_new = download_bars(ticker, start, end)
    except Exception as e:
        logger.error(f"Download failed for {ticker}: {e}", exc_info=True)
        return PipelineResult(ok=False, error=f"download_failed: {e}")
    if df_new.empty:
        logger.info(f"No new data for {ticker} between {start} and {end}")
        result.warnings.append(f"No new data for {ticker} between {start} and {end}")
        return result

    df_new = df_new.copy()
    idx = pd.DatetimeIndex(df_new.index)
    # yfinance's daily index is normally tz-naive, but some versions/paths
    # return tz-aware stamps — tz_localize(None) would raise on those, so
    # convert instead of localize when a tz is present.
    df_new.index = idx.tz_localize(None) if idx.tz is None else idx.tz_convert(None)
    df_new["date"] = df_new.index.date

    # INVARIANT: bars arrive canonical (ADR 0011), so the ingest stage never
    # touches vendor column names — the mapping lives in the provider.
    bar_cols = list(CANONICAL_BAR_COLUMNS)
    provider_name = get_provider().name

    rows = []
    for _d, row in df_new.iterrows():
        date_str = row["date"].isoformat()
        # If all new values are NA, retain old data (skip insert) and log
        if row[bar_cols].isna().all():
            msg = f"Blank data for {ticker} on {date_str}; retaining old data if exists"
            logger.warning(msg)
            result.warnings.append(msg)
            continue
        rows.append(
            (
                ticker,
                date_str,
                *[float(row[col]) if pd.notna(row.get(col)) else None for col in bar_cols],
                provider_name,
            )
        )

    if rows:
        upsert_many(
            "raw_bars",
            ["ticker", "date", *bar_cols, "provider"],
            rows,
        )
    result.rows = len(rows)
    return result

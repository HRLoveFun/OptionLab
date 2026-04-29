"""Data cleaning utilities for raw market price data."""
import datetime as dt
import logging

import numpy as np
import pandas as pd

from . import PipelineResult
from .db import fetch_df, upsert_many

logger = logging.getLogger(__name__)


def _get_business_days(start: dt.date, end: dt.date) -> pd.DatetimeIndex:
    """Return business days (Mon-Fri) index for [start, end)."""
    # Use pandas 'B' frequency which excludes weekends. Holidays are not removed here.
    # pd.date_range with start and end includes the end if it matches the frequency.
    return pd.date_range(start, end, freq="B")


def _flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # CONSTRAINT: SQLite returns Python float objects → columns have ``object``
    # dtype. ``np.log()`` on object dtype fails with a cryptic error.
    # Always coerce numerics first. See docs/constraints.md §2.
    for col in ("open", "high", "low", "close", "adj_close", "volume"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    # DOMAIN: 5σ threshold for price-jump and volume-anomaly flags. Empirically
    # tuned for US equities; lower values produce excessive false positives on
    # earnings days, higher values miss real corporate-action artefacts.
    # Do NOT “extract to config” — changing this changes the meaning of
    # downstream ``price_jump_flag`` consumers.
    # Price jumps: difference in Close vs previous Close
    ret = np.log(out["close"]).diff()
    thr = 5 * ret.std(skipna=True)
    out["price_jump_flag"] = ((ret.abs() > thr).astype(int)).values
    # Vol anomaly: log delta volume
    lv = np.log(out["volume"]).replace([-np.inf, np.inf], np.nan)
    d_lv = lv.diff()
    thr_v = 5 * d_lv.std(skipna=True)
    out["vol_anom_flag"] = ((d_lv.abs() > thr_v).astype(int)).values
    # OHLC consistency: low must not exceed open and close must not exceed high.
    # Violations indicate a data error from yfinance, not a market event.
    out["ohlc_inconsistent"] = (
        ~((out["low"] <= out["open"]).fillna(True) & (out["close"] <= out["high"]).fillna(True))
    ).astype(int)
    return out


def clean_range(ticker: str, start: dt.date | None = None, end: dt.date | None = None) -> PipelineResult:
    """
    Clean data for [start, end). Align to business days, mark missing days as NA
    (no interpolation for full missing days), flag anomalies, and upsert to clean_prices.
    Returns a PipelineResult with row count and any warnings.

    INVARIANT: missing trading days remain NA. We do NOT interpolate prices
    that didn’t trade — inventing them would corrupt every downstream
    indicator (HV, MA, regime). See docs/constraints.md §4.
    """
    # Treat end as inclusive date
    end = end or dt.date.today()
    start = start or (end - dt.timedelta(days=30))

    # Inclusive end date query
    df = fetch_df(
        "SELECT * FROM raw_prices WHERE ticker=? AND date>=? AND date<=?",
        (ticker, start.isoformat(), end.isoformat()),
    )
    # WHY: If raw_prices has zero rows for this ticker (e.g. the ticker was
    # invalid and yfinance returned nothing), do NOT generate a business-day
    # aligned all-NaN frame and upsert it. Doing so pollutes clean_prices
    # with phantom rows for arbitrary user input — including XSS payloads —
    # and turns a read-only "validate_ticker" call into a DB writer.
    if df.empty:
        # Sanity check: only short-circuit when the ticker has no clean_prices
        # history at all. Established tickers might legitimately have a quiet
        # period (e.g. exchange holiday week) where the requested raw range
        # is empty; in that case fall through and align as before so existing
        # downstream guarantees about business-day alignment are preserved.
        existing = fetch_df(
            "SELECT 1 FROM clean_prices WHERE ticker=? LIMIT 1",
            (ticker,),
        )
        if existing.empty:
            logger.info(
                "clean_range: skipping upsert for %s — no raw rows and no existing clean_prices",
                ticker,
            )
            return PipelineResult(ok=True, rows=0, warnings=["no_data_for_ticker"])
    # Align to business days
    idx = _get_business_days(start, end)
    if df.empty:
        # Create an empty aligned frame with expected columns so subsequent
        # column-based operations work without KeyError.
        aligned = pd.DataFrame(
            index=idx, columns=["ticker", "open", "high", "low", "close", "adj_close", "volume", "provider"]
        )
    else:
        df = df.rename(
            columns={
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "adj_close": "adj_close",
                "volume": "volume",
            }
        )
        df.index = pd.to_datetime(df.index).tz_localize(None)
        aligned = df.reindex(idx)

    aligned["is_trading_day"] = (
        aligned[["open", "high", "low", "close", "adj_close", "volume"]].notna().any(axis=1).astype(int)
    )
    aligned["missing_any"] = (
        aligned[["open", "high", "low", "close", "adj_close", "volume"]].isna().any(axis=1).astype(int)
    )

    # Interpolate missing field values within trading days: forward fill for volume only (policy)
    aligned["volume"] = aligned["volume"].ffill()

    # Anomalies
    aligned = _flag_anomalies(aligned)

    # WHY: Yahoo occasionally returns bad far-future / split-glitch rows where
    # close is 100x+ the surrounding median (e.g. NVDA showing $53k–$59k for
    # several Apr-2026 dates with no split). These poison every downstream
    # signal (HV, regime, returns). Drop the OHLC of any row whose close is
    # more than 10x or less than 1/10th the 30-row trailing median while
    # keeping the row in place (so business-day alignment is preserved).
    try:
        close_num = pd.to_numeric(aligned["close"], errors="coerce")
        med = close_num.rolling(30, min_periods=5).median()
        ratio = close_num / med
        bad_mask = (ratio > 10) | (ratio < 0.1)
        if bad_mask.any():
            n_bad = int(bad_mask.sum())
            logger.warning(
                "clean_range: dropping %d implausible OHLC row(s) for %s (close vs 30d median > 10x)",
                n_bad,
                ticker,
            )
            for col in ("open", "high", "low", "close", "adj_close"):
                if col in aligned.columns:
                    aligned.loc[bad_mask, col] = np.nan
            aligned.loc[bad_mask, "price_jump_flag"] = 1
            aligned.loc[bad_mask, "missing_any"] = 1
            aligned.loc[bad_mask, "is_trading_day"] = 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("outlier guard skipped for %s: %s", ticker, exc)

    rows = []
    for d, r in aligned.iterrows():
        date_str = d.date().isoformat()
        rows.append(
            (
                ticker,
                date_str,
                None if pd.isna(r.get("open")) else float(r["open"]),
                None if pd.isna(r.get("high")) else float(r["high"]),
                None if pd.isna(r.get("low")) else float(r["low"]),
                None if pd.isna(r.get("close")) else float(r["close"]),
                None if pd.isna(r.get("adj_close")) else float(r["adj_close"]),
                None if pd.isna(r.get("volume")) else float(r["volume"]),
                int(r.get("is_trading_day", 0)),
                int(r.get("missing_any", 0)),
                int(r.get("price_jump_flag", 0)),
                int(r.get("vol_anom_flag", 0)),
                int(r.get("ohlc_inconsistent", 0)),
            )
        )
    if rows:
        upsert_many(
            "clean_prices",
            [
                "ticker",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "is_trading_day",
                "missing_any",
                "price_jump_flag",
                "vol_anom_flag",
                "ohlc_inconsistent",
            ],
            rows,
        )
    return PipelineResult(rows=len(rows))

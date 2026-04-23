"""Market regime orchestration service.

Responsibilities:
  - Pull VIX/SPY daily closes via the existing DataService (DB-cached, throttled).
  - Invoke core.regime to compute labels.
  - Persist labels in the ``regime_log`` SQLite table (idempotent per date).
  - Produce window coverage reports for the frontend.

This service never imports from ``app`` or Flask. All I/O errors are caught
and surfaced as ``data_complete=False`` / UNKNOWN labels — never raised.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import pandas as pd

from core.regime import (
    SLOPE_LOOKBACK,
    SMA_WINDOW,
    coverage_report,
    label_regime,
    label_series,
    regime_transitions,
)
from data_pipeline.cleaning import clean_range
from data_pipeline.data_service import DataService, _cache_invalidate
from data_pipeline.db import fetch_df, init_db, upsert_many
from data_pipeline.downloader import upsert_raw_prices
from data_pipeline.processing import process_frequencies

logger = logging.getLogger(__name__)

VIX_TICKER = "^VIX"
SPY_TICKER = "SPY"
MIN_LOOKBACK_DAYS = 90  # calendar days; covers 20-day SMA + 5-day slope + weekends
BOOTSTRAP_DAYS = 400  # ≈ 280 trading days — enough for 3Y charts once accumulated
MIN_TRADING_ROWS = SMA_WINDOW + SLOPE_LOOKBACK + 5  # need this many rows to label direction


def _count_clean_rows(ticker: str) -> int:
    """Return how many *priced* rows the DB holds for ``ticker``.

    Counts only rows with a non-null ``close`` — ``clean_prices`` is
    calendar-padded, so row count alone overstates real history when
    an earlier download was rate-limited and produced NaN prices.
    """
    init_db()
    df = fetch_df(
        "SELECT COUNT(*) AS n FROM clean_prices WHERE ticker=? AND close IS NOT NULL",
        (ticker,),
    )
    if df.empty:
        return 0
    try:
        return int(df.iloc[0]["n"])
    except (KeyError, TypeError, ValueError):
        return 0


def _bootstrap_history(ticker: str, days: int = BOOTSTRAP_DAYS) -> None:
    """Run the full data pipeline over a wide date range for ``ticker``.

    ``DataService.get_cleaned_daily`` only seeds ~7 days per call (and has a
    60 s cooldown), which is insufficient for 20-day SMA computation. This
    helper bypasses that limitation by invoking the pipeline directly when the
    DB is thin. Safe to call repeatedly: all three stages are upserts.
    """
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    logger.info("Regime: bootstrapping %d days of history for %s", days, ticker)
    try:
        dl = upsert_raw_prices(ticker, start, end)
        if not dl.ok:
            logger.warning("Regime bootstrap (download) failed for %s: %s", ticker, dl.error)
            return
        cl = clean_range(ticker, start, end)
        if not cl.ok:
            logger.warning("Regime bootstrap (clean) failed for %s: %s", ticker, cl.error)
            return
        pr = process_frequencies(ticker, start, end)
        if not pr.ok:
            logger.warning("Regime bootstrap (process) failed for %s: %s", ticker, pr.error)
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Regime bootstrap for %s crashed: %s", ticker, e, exc_info=True)
    finally:
        # Invalidate DataService's TTL cache; otherwise a previously cached
        # empty result would mask the freshly downloaded rows.
        _cache_invalidate(ticker)


def _ensure_history(ticker: str) -> None:
    """Guarantee enough rows for 20-day SMA + 5-day slope. No-op when already present."""
    if _count_clean_rows(ticker) < MIN_TRADING_ROWS:
        _bootstrap_history(ticker)


# ── Data access ───────────────────────────────────────────────────
def _fetch_close_series(ticker: str, start: dt.date, end: dt.date) -> pd.Series:
    """Return a date-indexed close series, or empty on failure.

    Ensures the DB has enough history for SMA/slope computation on first access.
    """
    try:
        _ensure_history(ticker)
        df = DataService.get_cleaned_daily(ticker, start=start, end=end)
    except Exception as e:
        logger.warning("Regime: fetch failed for %s: %s", ticker, e)
        return pd.Series(dtype=float)

    if df is None or df.empty or "close" not in df.columns:
        logger.info("Regime: no data for %s in [%s, %s]", ticker, start, end)
        return pd.Series(dtype=float)

    s = pd.to_numeric(df["close"], errors="coerce").dropna()
    s.index = pd.to_datetime(s.index)
    s.name = ticker
    return s.sort_index()


# ── Persistence ───────────────────────────────────────────────────
_REGIME_COLS = (
    "date",
    "vol_regime",
    "dir_regime",
    "vix_value",
    "sma_20",
    "sma_slope_5d",
    "close_vs_sma_pct",
    "regime_changed_from_previous",
    "fetch_timestamp",
    "notes",
)


def _load_log_df() -> pd.DataFrame:
    init_db()
    return fetch_df("SELECT * FROM regime_log ORDER BY date ASC")


def _previous_log_row(date: dt.date) -> dict | None:
    init_db()
    df = fetch_df(
        "SELECT * FROM regime_log WHERE date < ? ORDER BY date DESC LIMIT 1",
        (date.isoformat(),),
    )
    if df.empty:
        return None
    row = df.iloc[0].to_dict()
    return row


def _upsert_log_rows(rows: list[dict]) -> None:
    if not rows:
        return
    init_db()
    ordered = [tuple(r.get(c) for c in _REGIME_COLS) for r in rows]
    upsert_many("regime_log", _REGIME_COLS, ordered)


# ── Public API ────────────────────────────────────────────────────
class RegimeService:
    """Facade for all market-regime operations exposed to Flask routes."""

    @staticmethod
    def compute_current(as_of: dt.date | None = None) -> dict[str, Any]:
        """Compute regime for ``as_of`` (default today). Does NOT persist."""
        as_of = as_of or dt.date.today()
        start = as_of - dt.timedelta(days=MIN_LOOKBACK_DAYS)

        vix = _fetch_close_series(VIX_TICKER, start, as_of)
        spy = _fetch_close_series(SPY_TICKER, start, as_of)

        data_complete = not vix.empty and len(spy) >= SMA_WINDOW + SLOPE_LOOKBACK
        label = label_regime(as_of, vix, spy)

        return {
            "label": label.to_dict(),
            "data_complete": bool(data_complete),
            "spy_history_days": int(len(spy)),
            "vix_history_days": int(len(vix)),
        }

    @staticmethod
    def append_today(as_of: dt.date | None = None) -> dict[str, Any]:
        """Compute regime for ``as_of`` and upsert into ``regime_log``.

        Idempotent: re-running on the same date updates rather than duplicates.
        """
        result = RegimeService.compute_current(as_of)
        label = result["label"]
        date_str = label["date"]

        prev = _previous_log_row(dt.date.fromisoformat(date_str))
        regime_changed = 0
        if prev is not None:
            if (prev.get("vol_regime") != label["vol_regime"]) or (
                prev.get("dir_regime") != label["dir_regime"]
            ):
                regime_changed = 1

        row = {
            **label,
            "regime_changed_from_previous": regime_changed,
            "fetch_timestamp": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        _upsert_log_rows([row])
        result["persisted"] = True
        result["regime_changed_from_previous"] = bool(regime_changed)
        return result

    @staticmethod
    def backfill(days: int = 30, end_date: dt.date | None = None) -> dict[str, Any]:
        """Backfill regime labels for the last ``days`` trading days up to ``end_date``.

        Uses a single historical fetch for efficiency (no per-day yfinance calls).
        """
        days = max(1, min(int(days), 365 * 3))
        end = end_date or dt.date.today()
        # Pad lookback so the earliest backfilled date has 20-day SMA + 5-day slope
        start = end - dt.timedelta(days=days + MIN_LOOKBACK_DAYS)

        vix = _fetch_close_series(VIX_TICKER, start, end)
        spy = _fetch_close_series(SPY_TICKER, start, end)

        if spy.empty:
            return {"persisted_rows": 0, "reason": "spy_data_unavailable"}

        df = label_series(vix, spy)
        if df.empty or "sma_20" not in df.columns:
            return {"persisted_rows": 0, "reason": "label_series_empty"}

        # Keep only trading days where SMA is defined
        df = df.dropna(subset=["sma_20"])
        # Restrict to the requested window
        cutoff = pd.Timestamp(end - dt.timedelta(days=days))
        df = df[df.index >= cutoff]
        if df.empty:
            return {"persisted_rows": 0, "reason": "no_rows_in_window"}

        transitions = regime_transitions(df)
        change_dates = {t["date"] for t in transitions}

        now_iso = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        rows: list[dict] = []
        for ts, r in df.iterrows():
            d = pd.Timestamp(ts).date().isoformat()
            rows.append(
                {
                    "date": d,
                    "vol_regime": r["vol_regime"],
                    "dir_regime": r["dir_regime"],
                    "vix_value": None if pd.isna(r["vix_value"]) else float(r["vix_value"]),
                    "sma_20": None if pd.isna(r["sma_20"]) else float(r["sma_20"]),
                    "sma_slope_5d": None
                    if pd.isna(r["sma_slope_5d"])
                    else float(r["sma_slope_5d"]),
                    "close_vs_sma_pct": None
                    if pd.isna(r["close_vs_sma_pct"])
                    else float(r["close_vs_sma_pct"]),
                    "regime_changed_from_previous": 1 if d in change_dates else 0,
                    "fetch_timestamp": now_iso,
                    "notes": "",
                }
            )
        _upsert_log_rows(rows)
        return {"persisted_rows": len(rows), "first_date": rows[0]["date"], "last_date": rows[-1]["date"]}

    @staticmethod
    def history(days: int = 180) -> dict[str, Any]:
        """Return the persisted regime log for the last ``days`` days.

        If the log is empty/sparse, computes an on-the-fly series from market
        data without persisting — so the tab renders useful content on first visit.
        """
        days = max(5, min(int(days), 365 * 3))
        end = dt.date.today()
        start = end - dt.timedelta(days=days)

        df = _load_log_df()
        used_live = False
        if df.empty or len(df) < 5:
            # Fallback: compute live for display only.
            # Fetch a wider lookback so SMA is defined at the start of the window.
            vix = _fetch_close_series(VIX_TICKER, start - dt.timedelta(days=MIN_LOOKBACK_DAYS), end)
            spy = _fetch_close_series(SPY_TICKER, start - dt.timedelta(days=MIN_LOOKBACK_DAYS), end)
            df = label_series(vix, spy)
            if "sma_20" in df.columns:
                df = df.dropna(subset=["sma_20"])
            # Crop to the requested visible window (after SMA is computed)
            if not df.empty:
                df = df[df.index >= pd.Timestamp(start)]
            used_live = True
        else:
            df = df[df.index >= pd.Timestamp(start)]

        if df is None or df.empty:
            return {
                "rows": [],
                "coverage": coverage_report(df if df is not None else pd.DataFrame()),
                "source": "live" if used_live else "log",
            }

        rows = []
        for ts, r in df.iterrows():
            rows.append(
                {
                    "date": pd.Timestamp(ts).date().isoformat(),
                    "vol_regime": r.get("vol_regime"),
                    "dir_regime": r.get("dir_regime"),
                    "vix_value": None if pd.isna(r.get("vix_value")) else float(r.get("vix_value")),
                    "sma_20": None if pd.isna(r.get("sma_20")) else float(r.get("sma_20")),
                    "sma_slope_5d": None
                    if pd.isna(r.get("sma_slope_5d"))
                    else float(r.get("sma_slope_5d")),
                    "close_vs_sma_pct": None
                    if pd.isna(r.get("close_vs_sma_pct"))
                    else float(r.get("close_vs_sma_pct")),
                }
            )
        return {
            "rows": rows,
            "coverage": coverage_report(df),
            "source": "live" if used_live else "log",
        }

    @staticmethod
    def coverage_window(start_date: dt.date, end_date: dt.date) -> dict[str, Any]:
        """Charter §6 support: coverage report between two dates from the persisted log."""
        init_db()
        df = fetch_df(
            "SELECT * FROM regime_log WHERE date>=? AND date<=? ORDER BY date ASC",
            (start_date.isoformat(), end_date.isoformat()),
        )
        return {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "rows": int(len(df)),
            "coverage": coverage_report(df),
        }


__all__ = ["RegimeService"]

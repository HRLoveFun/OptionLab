"""DataService facade — the DB-first read entry point (ADR 0011).

Domain:    Data Pipeline — Read
Context:
  - This is the only ``data_pipeline`` surface above the package: services/,
    routes/ and app.py talk to ``DataService`` and never to store/ingest/
    transform directly. Reads come from ``read/_query.py``; anything that has to
    *make data ready* is delegated to ``orchestrate``.
Contracts:
  - ``DataService`` staticmethods — initialize, manual_update, seed_history,
    has_data_for_date, ensure_range, get_cleaned_daily, get_processed,
    get_processed_data, get_latest_spot.
Dependencies UPWARD:
  - store (db), orchestrate (backfill / update)
Dependencies DOWNWARD:
  - services/, routes/, app.py
"""

from data_pipeline.orchestrate import backfill as _bf
from data_pipeline.orchestrate import update as _u
from data_pipeline.store.db import init_db

from . import _query as _q


class DataService:
    """Facade for data operations."""

    # Re-export class-level attributes for backward compat
    _ENSURE_RANGE_TTL = _bf._ENSURE_RANGE_TTL
    _ensure_range_memo = _bf._ensure_range_memo
    _ensure_range_lock = _bf._ensure_range_lock
    _ensure_range_inflight = _bf._ensure_range_inflight
    _ensure_range_inflight_lock = _bf._ensure_range_inflight_lock
    _BACKFILL_MIN_DATE = _bf._BACKFILL_MIN_DATE
    _SENTINEL_GAP_THRESHOLD_DAYS = _bf._SENTINEL_GAP_THRESHOLD_DAYS
    _SENTINEL_MIN_DB_SPAN_DAYS = _bf._SENTINEL_MIN_DB_SPAN_DAYS

    @staticmethod
    def initialize():
        init_db()

    @staticmethod
    def manual_update(ticker: str, days: int = 7):
        return _u.manual_update(ticker, days)

    @staticmethod
    def seed_history(ticker: str, years: int = 5):
        return _u.seed_history(ticker, years)

    @staticmethod
    def has_data_for_date(ticker: str, date) -> bool:
        init_db()
        from data_pipeline.store.db import fetch_df

        df = fetch_df(
            "SELECT * FROM clean_bars WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        if not df.empty:
            return True
        df2 = fetch_df(
            "SELECT * FROM raw_bars WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        return not df2.empty

    @staticmethod
    def ensure_range(ticker: str, start, end) -> bool:
        return _bf.ensure_range(ticker, start, end)

    @staticmethod
    def get_cleaned_daily(ticker: str, start=None, end=None):
        return _q.get_cleaned_daily(ticker, start, end)

    @staticmethod
    def get_processed(ticker: str, frequency: str = "D", start=None, end=None):
        return _q.get_processed(ticker, frequency, start, end)

    @staticmethod
    def get_processed_data(ticker: str, start, end, frequency: str = "W"):
        return _q.get_processed_data(ticker, start, end, frequency)

    @staticmethod
    def get_latest_spot(ticker: str) -> float | None:
        return _q.get_latest_spot(ticker)

    @staticmethod
    def clear_ensure_range_memo(ticker: str) -> None:
        """Clear the cached ensure_range memo for *ticker*.

        Call this before ``seed_history`` when you want to bypass a
        previously cached failure and force a fresh backfill.
        """
        with _bf._ensure_range_lock:
            _bf._ensure_range_memo.pop(ticker, None)

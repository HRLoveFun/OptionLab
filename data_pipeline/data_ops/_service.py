"""DataService facade — thin orchestrator over data_ops submodules."""

from data_pipeline.db import init_db

from . import _globals as _g
from . import _query as _q
from . import _range as _r
from . import _update as _u


class DataService:
    """Facade for data operations."""

    # Re-export class-level attributes for backward compat
    _ENSURE_RANGE_TTL = _r._ENSURE_RANGE_TTL
    _ensure_range_memo = _r._ensure_range_memo
    _ensure_range_lock = _r._ensure_range_lock
    _ensure_range_inflight = _r._ensure_range_inflight
    _ensure_range_inflight_lock = _r._ensure_range_inflight_lock
    _BACKFILL_MIN_DATE = _r._BACKFILL_MIN_DATE
    _SENTINEL_GAP_THRESHOLD_DAYS = _r._SENTINEL_GAP_THRESHOLD_DAYS
    _SENTINEL_MIN_DB_SPAN_DAYS = _r._SENTINEL_MIN_DB_SPAN_DAYS

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
        from data_pipeline.db import fetch_df

        df = fetch_df(
            "SELECT * FROM clean_prices WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        if not df.empty:
            return True
        df2 = fetch_df(
            "SELECT * FROM raw_prices WHERE ticker=? AND date=?",
            (ticker, date.isoformat()),
        )
        return not df2.empty

    @staticmethod
    def ensure_range(ticker: str, start, end) -> bool:
        return _r.ensure_range(ticker, start, end)

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

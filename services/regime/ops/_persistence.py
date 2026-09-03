"""Regime log persistence: thin delegates to ``data_pipeline.repos``.

The actual SQL lives in ``data_pipeline.repos`` (the single SQL-building home,
ADR 0003 / architecture review §2 `db-access`); these wrappers keep the
``services.regime`` call surface stable.
"""

import datetime as dt

import pandas as pd

from data_pipeline.repos import (
    load_regime_log,
    previous_regime_log_row,
    upsert_regime_log_rows,
)


def _load_log_df() -> pd.DataFrame:
    return load_regime_log()


def _previous_log_row(date: dt.date) -> dict | None:
    return previous_regime_log_row(date)


def _upsert_log_rows(rows: list[dict]) -> None:
    upsert_regime_log_rows(rows)

"""Regime log persistence: SQLite read/write helpers."""

import datetime as dt

import pandas as pd

from data_pipeline.db import fetch_df, init_db, upsert_many

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

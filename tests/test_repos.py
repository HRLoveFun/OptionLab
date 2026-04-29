"""Tests for data_pipeline/repos.py."""

from __future__ import annotations

from data_pipeline.db import init_db
from data_pipeline.repos import PriceRepo, PriceRow


def _seed():
    init_db()
    rows = [
        PriceRow("ZZZ", "2024-01-02", 1.0, 2.0, 0.5, 1.5, 1.5, 100.0),
        PriceRow("ZZZ", "2024-01-03", 1.5, 2.5, 1.0, 2.0, 2.0, 200.0),
        PriceRow("ZZZ", "2024-01-04", 2.0, 3.0, 1.5, 2.5, 2.5, 300.0),
    ]
    PriceRepo.upsert_many("ZZZ", rows)


def test_latest_date_and_count():
    _seed()
    assert PriceRepo.latest_date("ZZZ") == "2024-01-04"
    assert PriceRepo.row_count("ZZZ") == 3
    assert PriceRepo.latest_date("DOESNOTEXIST") is None
    assert PriceRepo.row_count("DOESNOTEXIST") == 0


def test_get_range_filters_dates():
    _seed()
    df = PriceRepo.get_range("ZZZ", start="2024-01-03")
    assert len(df) == 2
    assert df["close"].iloc[-1] == 2.5


def test_upsert_many_replaces_on_conflict():
    _seed()
    rows = [PriceRow("ZZZ", "2024-01-04", 9.0, 9.0, 9.0, 9.0, 9.0, 999.0)]
    n = PriceRepo.upsert_many("ZZZ", rows)
    assert n == 1
    df = PriceRepo.get_range("ZZZ", start="2024-01-04", end="2024-01-04")
    assert df["close"].iloc[0] == 9.0

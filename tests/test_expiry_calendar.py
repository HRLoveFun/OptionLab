"""Tests for core.options.simulation.expiry_calendar.generate_expiry_calendar.

Uses real calendar expectations (no mocks). The reference date 2026-09-04 is a
Friday (America/New_York). ``now`` is injected so the intraday DTE fraction is
deterministic: DTE = (date - ref).days + (16 - ref.hours) / 24, both endpoints
in US/Eastern. Columns with under one hour (or already expired — the ref day at
or after the 16:00 close) left are dropped.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from core.options.simulation.expiry_calendar import generate_expiry_calendar

REF = dt.date(2026, 9, 4)  # Friday
ET = ZoneInfo("America/New_York")
NOW_AM = dt.datetime(2026, 9, 4, 10, 0, tzinfo=ET)  # 6h to close -> frac 0.25
NOW_LATE = dt.datetime(2026, 9, 4, 15, 30, tzinfo=ET)  # <1h to close -> dropped
NOW_PM = dt.datetime(2026, 9, 4, 18, 0, tzinfo=ET)  # after close -> expired


def test_returns_expected_count():
    # 12 weekly standard + 10 daily, with no date overlap (weekly starts after
    # the last daily day), so 22 distinct columns.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    assert len(cal) == 22


def test_first_entry_is_same_day_with_intraday_fraction():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    first = cal[0]
    assert first["date"] == "2026-09-04"
    assert first["kind"] == "daily"
    # 16:00 - 10:00 = 6h = 0.25 days.
    assert first["dte"] == pytest.approx(0.25)
    assert first["label"] == "2026-09-04 (0.25D)"


def test_daily_dtes_carry_the_fraction():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    dailies = [e for e in cal if e["kind"] == "daily"]
    assert [e["date"] for e in dailies] == [
        "2026-09-04",
        "2026-09-07",
        "2026-09-08",
        "2026-09-09",
        "2026-09-10",
        "2026-09-11",
        "2026-09-14",
        "2026-09-15",
        "2026-09-16",
        "2026-09-17",
    ]
    assert [e["dte"] for e in dailies] == pytest.approx(
        [0.25, 3.25, 4.25, 5.25, 6.25, 7.25, 10.25, 11.25, 12.25, 13.25]
    )


def test_after_close_drops_expired_same_day_column():
    # At 18:00 ET the same-day expiration is already gone: dte = -2/24 <= 0.
    # The daily series rolls forward and still yields 10 columns.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_PM)
    dates = [e["date"] for e in cal]
    assert "2026-09-04" not in dates
    dailies = [e for e in cal if e["kind"] == "daily"]
    assert len(dailies) == 10
    assert dailies[0]["date"] == "2026-09-07"
    # 3 whole days minus the 2 hours past the close: 3 - 2/24.
    assert dailies[0]["dte"] == pytest.approx(3 - 2 / 24)
    # The last daily day is now 09-18, so the weekly ladder starts 09-25.
    standards = [e for e in cal if e["kind"] == "standard"]
    assert standards[0]["date"] == "2026-09-25"


def test_sub_hour_column_floored_to_one_hour():
    # At 15:30 ET only 30 minutes are left: 0.5/24 = 0.0208 days. The column is
    # kept (not dropped) with its DTE raised to the one-hour floor.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_LATE)
    first = cal[0]
    assert first["date"] == "2026-09-04"
    assert first["kind"] == "daily"
    assert first["dte"] == pytest.approx(1 / 24)
    assert first["label"] == "2026-09-04 (0.04D)"
    # Every later column keeps its own (larger) fractional DTE.
    assert [e["dte"] for e in cal[1:11]] == pytest.approx(
        [3.020833, 4.020833, 5.020833, 6.020833, 7.020833, 10.020833, 11.020833, 12.020833, 13.020833, 14.020833]
    )


def test_exactly_at_close_is_expired():
    # The instant the market closes the same-day expiration is gone: dte == 0.
    now = dt.datetime(2026, 9, 4, 16, 0, tzinfo=ET)
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=now)
    assert "2026-09-04" not in {e["date"] for e in cal}
    assert cal[0]["date"] == "2026-09-07"


def test_labor_day_included_by_default():
    # Default: no holiday adjustment, so 2026-09-07 (Labour Day Monday) stays.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    dates = [e["date"] for e in cal]
    assert "2026-09-07" in dates


def test_standard_weekly_fridays():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    standards = [e for e in cal if e["kind"] == "standard"]
    # Weekly Fridays strictly after the last daily day (2026-09-17).
    expected_dates = [
        "2026-09-18",
        "2026-09-25",
        "2026-10-02",
        "2026-10-09",
        "2026-10-16",
        "2026-10-23",
        "2026-10-30",
        "2026-11-06",
        "2026-11-13",
        "2026-11-20",
        "2026-11-27",
        "2026-12-04",
    ]
    assert [e["date"] for e in standards] == expected_dates


def test_cycle_tags():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    standards = [e for e in cal if e["kind"] == "standard"]
    # The weekly ladder tags every entry "weekly".
    assert all(e["cycle"] == "weekly" for e in standards)
    assert standards[0]["date"] == "2026-09-18"


def test_weekly_dtes_carry_the_fraction():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    standards = [e for e in cal if e["kind"] == "standard"]
    assert standards[0]["dte"] == pytest.approx(14.25)  # 09-18, 6h left
    assert standards[1]["dte"] == pytest.approx(21.25)  # 09-25
    assert standards[-1]["dte"] == pytest.approx(91.25)  # 12-04


def test_sorted_and_unique():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, now=NOW_AM)
    dates = [e["date"] for e in cal]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_accepts_iso_string():
    cal = generate_expiry_calendar("2026-09-04", n_standard=3, n_daily=2, now=NOW_AM)
    assert cal[0]["date"] == "2026-09-04"


def test_holiday_friday_dropped_from_weekly_ladder():
    # Force the first weekly Friday (2026-09-18) to be a holiday. It rolls back
    # to 09-17, which already sits inside the daily range, so it is excluded and
    # the ladder starts the following Friday (09-25).
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}, now=NOW_AM)
    standards = [e for e in cal if e["kind"] == "standard"]
    assert standards[0]["date"] == "2026-09-25"
    assert standards[0]["dte"] == pytest.approx(21.25)
    assert all(e["cycle"] == "weekly" for e in standards)


def test_holidays_param_excludes_dates():
    # When holidays are supplied, those dates are skipped in the daily series.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 7)}, now=NOW_AM)
    dates = {e["date"] for e in cal}
    assert "2026-09-07" not in dates


def test_holiday_friday_not_duplicated_with_daily():
    # The holiday Friday 9/18 rolls back to 9/17, which already exists in the
    # daily series; it is dropped from the weekly ladder so 9/17 appears once
    # (as daily), not twice.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}, now=NOW_AM)
    sept17 = [e for e in cal if e["date"] == "2026-09-17"]
    assert len(sept17) == 1
    assert sept17[0]["kind"] == "daily"
    # And 9/18 itself is absent (it was a holiday, not a listed weekly Friday).
    assert "2026-09-18" not in {e["date"] for e in cal}

"""Tests for core.options.simulation.expiry.generate_expiry_calendar.

Uses real calendar expectations (no mocks): the reference date 2026-09-04 is a
Friday. The calendar returns ``n_daily`` consecutive business days (starting at
``ref``) plus ``n_standard`` weekly Fridays strictly after the last daily day,
each tagged ``cycle="weekly"``. DTE is ``(date - ref).days + 1``. Passing an
explicit ``holidays`` set re-enables the Friday roll-back behaviour.
"""

import datetime as dt

from core.options.simulation.expiry import generate_expiry_calendar

REF = dt.date(2026, 9, 4)  # Friday


def test_returns_expected_count():
    # 12 weekly standard + 10 daily, with no date overlap (weekly starts after
    # the last daily day), so 22 distinct columns.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    assert len(cal) == 22


def test_first_entry_is_reference_day_as_daily_1dte():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    first = cal[0]
    assert first["date"] == "2026-09-04"
    assert first["kind"] == "daily"
    assert first["dte"] == 1  # DTE is +1, so the same-day column reads 1D


def test_labor_day_included_by_default():
    # Default: no holiday adjustment, so 2026-09-07 (Labour Day Monday) stays.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    dates = [e["date"] for e in cal]
    assert "2026-09-07" in dates


def test_standard_weekly_fridays():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    standards = [e for e in cal if e["kind"] == "standard"]
    # Weekly Fridays strictly after the last daily day (2026-09-17).
    expected_dates = [
        "2026-09-18", "2026-09-25", "2026-10-02", "2026-10-09",
        "2026-10-16", "2026-10-23", "2026-10-30", "2026-11-06",
        "2026-11-13", "2026-11-20", "2026-11-27", "2026-12-04",
    ]
    assert [e["date"] for e in standards] == expected_dates


def test_cycle_tags():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    standards = [e for e in cal if e["kind"] == "standard"]
    # The weekly ladder tags every entry "weekly".
    assert all(e["cycle"] == "weekly" for e in standards)
    assert standards[0]["date"] == "2026-09-18"


def test_sorted_and_unique():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    dates = [e["date"] for e in cal]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_accepts_iso_string():
    cal = generate_expiry_calendar("2026-09-04", n_standard=3, n_daily=2)
    assert cal[0]["date"] == "2026-09-04"


def test_holiday_friday_dropped_from_weekly_ladder():
    # Force the first weekly Friday (2026-09-18) to be a holiday. It rolls back
    # to 09-17, which already sits inside the daily range, so it is excluded and
    # the ladder starts the following Friday (09-25).
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}
    )
    standards = [e for e in cal if e["kind"] == "standard"]
    assert standards[0]["date"] == "2026-09-25"
    assert standards[0]["dte"] == 22
    assert all(e["cycle"] == "weekly" for e in standards)


def test_holidays_param_excludes_dates():
    # When holidays are supplied, those dates are skipped in the daily series.
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 7)}
    )
    dates = {e["date"] for e in cal}
    assert "2026-09-07" not in dates


def test_holiday_friday_not_duplicated_with_daily():
    # The holiday Friday 9/18 rolls back to 9/17, which already exists in the
    # daily series; it is dropped from the weekly ladder so 9/17 appears once
    # (as daily), not twice.
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}
    )
    sept17 = [e for e in cal if e["date"] == "2026-09-17"]
    assert len(sept17) == 1
    assert sept17[0]["kind"] == "daily"
    # And 9/18 itself is absent (it was a holiday, not a listed weekly Friday).
    assert "2026-09-18" not in {e["date"] for e in cal}

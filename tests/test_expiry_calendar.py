"""Tests for core.options.simulation.expiry.generate_expiry_calendar.

Uses real calendar expectations (no mocks): the reference date 2026-09-04 is a
Friday. By default NO holiday adjustment is applied (only weekends are skipped),
so third-Friday expirations are returned as-is; passing an explicit ``holidays``
set re-enables the roll-back behaviour.
"""

import datetime as dt

from core.options.simulation.expiry import generate_expiry_calendar

REF = dt.date(2026, 9, 4)  # Friday


def test_returns_expected_count():
    # 12 standard + 10 daily; with no holiday adjustment the daily series keeps
    # 2026-09-07 (Labour Day Monday), so 9/18 only appears once (as standard).
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    assert len(cal) == 22


def test_first_entry_is_reference_day_as_daily_0dte():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    first = cal[0]
    assert first["date"] == "2026-09-04"
    assert first["kind"] == "daily"
    assert first["dte"] == 0  # same-day (0DTE)


def test_labor_day_included_by_default():
    # Default: no holiday adjustment, so 2026-09-07 (Labour Day Monday) stays.
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    dates = [e["date"] for e in cal]
    assert "2026-09-07" in dates


def test_standard_third_fridays():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    standards = [e for e in cal if e["kind"] == "standard"]
    expected_dates = [
        "2026-09-18", "2026-10-16", "2026-11-20", "2026-12-18",
        "2027-01-15", "2027-02-19", "2027-03-19", "2027-04-16",
        "2027-05-21", "2027-06-18", "2027-07-16", "2027-08-20",
    ]
    assert [e["date"] for e in standards] == expected_dates


def test_cycle_tags():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    by_date = {e["date"]: e for e in cal}
    assert by_date["2027-01-15"]["cycle"] == "leaps"
    assert by_date["2026-09-18"]["cycle"] == "quarterly"
    assert by_date["2026-12-18"]["cycle"] == "quarterly"
    assert by_date["2027-03-19"]["cycle"] == "quarterly"
    assert by_date["2027-06-18"]["cycle"] == "quarterly"
    assert by_date["2026-10-16"]["cycle"] == "monthly"
    assert by_date["2027-02-19"]["cycle"] == "monthly"


def test_sorted_and_unique():
    cal = generate_expiry_calendar(REF, n_standard=12, n_daily=10)
    dates = [e["date"] for e in cal]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))


def test_accepts_iso_string():
    cal = generate_expiry_calendar("2026-09-04", n_standard=3, n_daily=2)
    assert cal[0]["date"] == "2026-09-04"


def test_third_friday_rolls_back_on_injected_holiday():
    # Force the September 3rd Friday (2026-09-18) to be a holiday and confirm the
    # listed expiration rolls back to the prior business day (Thursday 09-17).
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}
    )
    standards = [e for e in cal if e["kind"] == "standard"]
    assert standards[0]["date"] == "2026-09-17"
    assert standards[0]["dte"] == 13


def test_holidays_param_excludes_dates():
    # When holidays are supplied, those dates are skipped in the daily series.
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 7)}
    )
    dates = {e["date"] for e in cal}
    assert "2026-09-07" not in dates


def test_injected_holiday_collision_keeps_standard():
    # Standard 9/18 rolls back to 9/17, which also appears in the daily series
    # -> de-duplicated with the standard entry winning.
    cal = generate_expiry_calendar(
        REF, n_standard=12, n_daily=10, holidays={dt.date(2026, 9, 18)}
    )
    sept17 = [e for e in cal if e["date"] == "2026-09-17"]
    assert len(sept17) == 1
    assert sept17[0]["kind"] == "standard"

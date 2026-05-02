"""Date parsing and manipulation helpers."""

import datetime as dt


def parse_month_str(value: str) -> dt.date | None:
    """Parse a YYYYMM or YYYY-MM string into a date (first of month)."""
    if not value:
        return None
    for fmt in ("%Y%m", "%Y-%m"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def exclusive_month_end(month_date: dt.date | None) -> dt.date | None:
    """Return the first day of the next month for horizon end handling."""
    if month_date is None:
        return None
    year = month_date.year + (1 if month_date.month == 12 else 0)
    month = 1 if month_date.month == 12 else month_date.month + 1
    return dt.date(year, month, 1)

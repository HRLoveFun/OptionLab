"""Tests for utils/utils.py — parse helpers and constants."""
import datetime as dt
import pytest

from utils.utils import parse_month_str, exclusive_month_end


class TestParseMonthStr:
    def test_yyyymm(self):
        assert parse_month_str("202301") == dt.date(2023, 1, 1)

    def test_yyyy_mm(self):
        assert parse_month_str("2023-01") == dt.date(2023, 1, 1)

    def test_empty_string(self):
        assert parse_month_str("") is None

    def test_invalid(self):
        assert parse_month_str("not-a-date") is None

    def test_partial(self):
        assert parse_month_str("2023") is None


class TestExclusiveMonthEnd:
    def test_normal_month(self):
        assert exclusive_month_end(dt.date(2023, 6, 1)) == dt.date(2023, 7, 1)

    def test_december_wraps_year(self):
        assert exclusive_month_end(dt.date(2023, 12, 1)) == dt.date(2024, 1, 1)

    def test_none_input(self):
        assert exclusive_month_end(None) is None

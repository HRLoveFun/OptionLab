"""Parity: stdlib mirror in scripts/gen_pages_fixtures.py matches core calendar."""

import datetime as dt
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo

from core.options.simulation.expiry import generate_expiry_calendar

# Same fixed wall clock as gen_pages_fixtures.REF_NOW — the intraday DTE
# fraction must be pinned on BOTH sides of the parity comparison.
_NOW = dt.datetime(2026, 9, 4, 10, 0, tzinfo=ZoneInfo("America/New_York"))


def _load_gen():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gen_pages_fixtures.py"
    spec = importlib.util.spec_from_file_location("gen_pages_fixtures", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_calendar_mirror_matches_core():
    gen = _load_gen()
    got = gen.gen_calendar()["expirations"]
    want = generate_expiry_calendar("2026-09-04", 12, 10, now=_NOW)
    assert got == want

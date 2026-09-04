"""Parity: stdlib mirror in scripts/gen_pages_fixtures.py matches core calendar."""

import importlib.util
from pathlib import Path

from core.options.simulation.expiry import generate_expiry_calendar


def _load_gen():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gen_pages_fixtures.py"
    spec = importlib.util.spec_from_file_location("gen_pages_fixtures", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_calendar_mirror_matches_core():
    gen = _load_gen()
    got = gen.gen_calendar()["expirations"]
    want = generate_expiry_calendar("2026-09-04", 12, 10)
    assert got == want

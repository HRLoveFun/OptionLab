"""Parity: stdlib mirror in scripts/gen_pages_fixtures.py matches core calendar."""

import importlib.util
from pathlib import Path

from core.options.simulation.expiry_calendar import generate_expiry_calendar


def _load_gen():
    path = Path(__file__).resolve().parents[1] / "scripts" / "gen_pages_fixtures.py"
    spec = importlib.util.spec_from_file_location("gen_pages_fixtures", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_calendar_mirror_matches_core():
    gen = _load_gen()
    got = gen.gen_calendar()["expirations"]
    # Parity is checked against the SAME runtime as-of instant the generator used,
    # so the test never hard-codes a date and stays valid as the fixture rolls
    # forward on every deploy.
    want = generate_expiry_calendar(gen.REF_DATE, 12, 10, now=gen.REF_NOW)
    assert got == want

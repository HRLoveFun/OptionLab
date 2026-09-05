"""Deterministic Pages fixtures (no network, no yfinance).

Writes (committed to site/fixtures/):
  - expiry_calendar.json    — stdlib mirror of core calendar (parity: tests/test_pages_fixtures.py)
  - odds_with_vol.nvda.json — demo vol-context table derived from the committed chain fixture

Live-data fixtures (option_chain, market_review_ts, regime_*, validate_tickers)
are refreshed by scripts/build_pages_site.py --refresh-snapshot instead.
"""

from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "site" / "fixtures"
REF_DATE = "2026-09-04"
# Fixed wall clock (10:00 ET, mid-session) so the intraday DTE fraction
# (16:00 ET close minus now) is deterministic in the committed fixture.
REF_NOW = dt.datetime(2026, 9, 4, 10, 0, tzinfo=ZoneInfo("America/New_York"))
TICKER = "NVDA"
SPOT = 182.45


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _adjust_to_business_day(d: dt.date, forward: bool) -> dt.date:
    # Mirror of core.options.simulation.expiry._adjust_to_business_day with
    # holidays=frozenset() (fixtures use no holiday adjustment — weekends only).
    step = dt.timedelta(days=1 if forward else -1)
    guard = 0
    while d.weekday() in (5, 6) and guard < 10:
        guard += 1
        d += step
    return d


def _fmt_dte(dte: float) -> str:
    return f"{dte:.2f}".rstrip("0").rstrip(".")


def _make_entry(d: dt.date, ref: dt.date, kind: str, cycle, frac: float):
    # Mirror of core: fractional DTE floored at one hour, expired (<= 0) -> None.
    raw = (d - ref).days + frac
    if raw <= 0:
        return None
    dte = max(round(raw, 6), 1 / 24)
    return {
        "date": d.isoformat(),
        "dte": dte,
        "label": f"{d.isoformat()} ({_fmt_dte(dte)}D)",
        "kind": kind,
        "cycle": cycle,
    }


def _next_friday(d: dt.date) -> dt.date:
    friday = d + dt.timedelta(days=1)
    while friday.weekday() != 4:
        friday += dt.timedelta(days=1)
    return friday


def gen_calendar() -> dict:
    # Stdlib-only mirror of core.options.simulation.expiry.generate_expiry_calendar
    # (ref, n_standard=12, n_daily=10, holidays=None). Kept dependency-free so
    # the Pages workflow runs without numpy/scipy. Parity is covered by
    # tests/test_pages_fixtures.py.
    ref = dt.date.fromisoformat(REF_DATE)
    frac = (16 * 3600 - (REF_NOW.hour * 3600 + REF_NOW.minute * 60 + REF_NOW.second)) / 86400
    daily: list[dict] = []
    d = _adjust_to_business_day(ref, forward=True)
    guard = 0
    while len(daily) < 10 and guard < 400:
        guard += 1
        entry = _make_entry(d, ref, "daily", None, frac)
        if entry is not None:
            daily.append(entry)
        d = _adjust_to_business_day(d + dt.timedelta(days=1), forward=True)
    standard: list[dict] = []
    last_daily = dt.date.fromisoformat(daily[-1]["date"]) if daily else ref
    cur = last_daily
    guard = 0
    while len(standard) < 12 and guard < 600:
        guard += 1
        cur = _next_friday(cur)
        eff = _adjust_to_business_day(cur, forward=False)
        if eff > last_daily:
            entry = _make_entry(eff, ref, "standard", "weekly", frac)
            if entry is not None:
                standard.append(entry)
    by_date: dict[str, dict] = {}
    for entry in standard + daily:
        by_date.setdefault(entry["date"], entry)
    exps = sorted(by_date.values(), key=lambda e: e["date"])
    return {"status": "ok", "reference_date": REF_DATE, "expirations": exps}


def gen_odds(target_pct: float = 10.0) -> dict:
    """Vol-context demo table derived from the COMMITTED chain fixture.

    WHY synthetic (not the service): the live /api/odds_with_vol shape
    ({spot, atm_iv_pct, prob_touch, odds}) has no vol_context/odds_by_expiry,
    so the tab's Module-4B table renders empty against the real backend too.
    This fixture keeps the same demo table working with whichever chain
    (synthetic or live snapshot) is committed.
    """
    chain = json.loads((OUT_DIR / "option_chain.nvda.json").read_text(encoding="utf-8"))
    spot = chain["spot"]
    today = dt.date.today()
    rows = []
    for exp in chain["expirations"]:
        d = max((dt.date.fromisoformat(exp) - today).days, 1)
        iv = 0.32 + 0.01 * d / 30
        t = d / 365.0
        # simplified lognormal touch prob
        z = (target_pct / 100) / (iv * math.sqrt(t))
        p_itm = round(max(0.02, min(0.98, 0.5 - z * 0.18)), 4)
        rows.append(
            {
                "expiry": exp,
                "dte": d,
                "iv": round(iv, 4),
                "p_itm_call": p_itm,
                "p_itm_put": round(1 - p_itm, 4),
                "expected_move": round(iv * math.sqrt(t), 4),
            }
        )
    return {
        "status": "ok",
        "ticker": chain.get("ticker", TICKER),
        "target_pct": target_pct,
        "spot": spot,
        "vol_context": {
            "implied_vol": 0.325,
            "realized_vol": 0.281,
            "vol_premium": 0.044,
            "vol_regime": "elevated",
            "expected_move_1d": round(0.325 / math.sqrt(365), 4),
            "prob_above_target": 0.214,
            "prob_below_target": 0.196,
        },
        "odds_by_expiry": rows,
        "sample": True,
        "sample_note": "Demo vol-context table for the GitHub Pages site.",
    }


def main() -> None:
    """Write the deterministic fixtures (expiry calendar + odds demo table).

    Live-data fixtures (option_chain, market_review_ts, regime, validate)
    are refreshed by scripts/build_pages_site.py --refresh-snapshot and are
    deliberately NOT touched here.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "expiry_calendar.json").write_text(json.dumps(gen_calendar(), indent=2) + "\n")
    (OUT_DIR / "odds_with_vol.nvda.json").write_text(json.dumps(gen_odds(), indent=2) + "\n")
    print(f"wrote deterministic fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()

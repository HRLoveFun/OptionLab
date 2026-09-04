"""Generate deterministic Pages fixtures (no network, no yfinance).

Outputs (committed to site/fixtures/):
  - expiry_calendar.json      — from core pure calendar
  - option_chain.nvda.json    — synthetic NVDA snapshot matching /api/option_chain shape
  - odds_with_vol.nvda.json   — vol_context + odds_by_expiry matching frontend table
  - market_review_ts.nvda.json — Chart.js payload matching build_timeseries shape

All synthetic but realistic; labelled sample in UI.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "site" / "fixtures"
REF_DATE = "2026-09-04"
TICKER = "NVDA"
SPOT = 182.45


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs_call(s, k, t, r, sigma) -> float:
    if t <= 0 or sigma <= 0:
        return max(s - k, 0.0)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return s * _norm_cdf(d1) - k * math.exp(-r * t) * _norm_cdf(d2)


def _adjust_to_business_day(d: dt.date, forward: bool) -> dt.date:
    # Mirror of core.options.simulation.expiry._adjust_to_business_day with
    # holidays=frozenset() (fixtures use no holiday adjustment — weekends only).
    step = dt.timedelta(days=1 if forward else -1)
    guard = 0
    while d.weekday() in (5, 6) and guard < 10:
        guard += 1
        d += step
    return d


def _make_entry(d: dt.date, ref: dt.date, kind: str, cycle):
    dte = (d - ref).days + 1
    return {
        "date": d.isoformat(),
        "dte": dte,
        "label": f"{d.isoformat()} ({dte}D)",
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
    daily: list[dict] = []
    d = _adjust_to_business_day(ref, forward=True)
    guard = 0
    while len(daily) < 10 and guard < 400:
        guard += 1
        daily.append(_make_entry(d, ref, "daily", None))
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
            standard.append(_make_entry(eff, ref, "standard", "weekly"))
    by_date: dict[str, dict] = {}
    for entry in standard + daily:
        by_date.setdefault(entry["date"], entry)
    exps = sorted(by_date.values(), key=lambda e: e["date"])
    return {"status": "ok", "reference_date": REF_DATE, "expirations": exps}


def gen_option_chain() -> dict:
    rng = random.Random(42)
    ref = dt.date.fromisoformat(REF_DATE)
    # 3 expiries within 45 DTE so default max_dte filter keeps them
    exp_dates = [
        (ref + dt.timedelta(days=14)).isoformat(),
        (ref + dt.timedelta(days=28)).isoformat(),
        (ref + dt.timedelta(days=42)).isoformat(),
    ]
    # 15 strikes ±30% around spot
    strikes = [round(SPOT * m, 2) for m in (0.70, 0.78, 0.85, 0.90, 0.94, 0.97, 1.0, 1.03, 1.06, 1.10, 1.15, 1.20, 1.25, 1.30, 1.32)]
    chain = {}
    for idx, exp in enumerate(exp_dates):
        dte = (dt.date.fromisoformat(exp) - ref).days
        t = max(dte, 1) / 365.0
        calls, puts = [], []
        for k in strikes:
            money = k / SPOT
            # smile: ATM 32%, wings up to ~55%
            iv = 0.32 + 0.35 * abs(math.log(money)) + 0.02 * idx
            iv = min(max(iv, 0.15), 0.90)
            call_px = _bs_call(SPOT, k, t, 0.05, iv)
            put_px = call_px - SPOT + k * math.exp(-0.05 * t)  # parity
            call_px = max(call_px, 0.05)
            put_px = max(put_px, 0.05)
            spread = 0.04 + rng.random() * 0.04
            for is_call, px in (True, call_px), (False, put_px):
                mid = round(px, 2)
                half = max(mid * spread / 2, 0.01)
                bid = round(max(mid - half, 0.01), 2)
                ask = round(mid + half, 2)
                last = round(mid + (rng.random() - 0.5) * half, 2)
                oi = int(rng.gauss(2500, 1800))
                oi = max(oi, 0)
                vol = int(rng.gauss(800, 600))
                vol = max(vol, 0)
                row = {
                    "strike": k,
                    "lastPrice": last,
                    "bid": bid,
                    "ask": ask,
                    "volume": vol,
                    "openInterest": oi,
                    "iv": round(iv * 100, 1),
                    "itm": (SPOT > k) if is_call else (SPOT < k),
                    "liq_score": "OK",
                    "liq_reason": "sample",
                }
                (calls if is_call else puts).append(row)
        chain[exp] = {"calls": calls, "puts": puts}
    return {
        "ticker": TICKER,
        "spot": SPOT,
        "expirations": exp_dates,
        "chain": chain,
        "sample": True,
        "sample_note": f"Synthetic {TICKER} snapshot for GitHub Pages demo (ref {REF_DATE}, not live).",
    }


def gen_odds(chain_fixture: dict, target_pct: float = 10.0) -> dict:
    spot = chain_fixture["spot"]
    rows = []
    for exp in chain_fixture["expirations"]:
        d = (dt.date.fromisoformat(exp) - dt.date.fromisoformat(REF_DATE)).days
        iv = 0.32 + 0.01 * d / 30
        t = max(d, 1) / 365.0
        # prob ITM approx via BS d2
        fwd = spot  # simplified
        for side in ("call", "put"):
            pass
        # simplified lognormal touch prob
        z = (target_pct / 100) / (iv * math.sqrt(t))
        p_touch = round(2 * (1 - _norm_cdf(abs(z))), 4)
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
        "ticker": TICKER,
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
        "sample_note": f"Derived from synthetic {TICKER} chain (ref {REF_DATE}).",
    }


def gen_market_review() -> dict:
    rng = random.Random(7)
    n = 240
    ref = dt.date.fromisoformat(REF_DATE)
    dates = [(ref - dt.timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
    assets = {}
    # main instrument random walk up ~18% over window
    px = 150.0
    main_prices = []
    for _ in range(n):
        px *= 1 + rng.gauss(0.0009, 0.016)
        main_prices.append(round(px, 2))
    # benchmarks: SPX-like drift, Gold-like flat
    def walk(start, drift, vol):
        out, p = [], start
        for _ in range(n):
            p *= 1 + rng.gauss(drift, vol)
            out.append(round(p, 2))
        return out

    raw = {
        TICKER: main_prices,
        "SPX": walk(5200, 0.0004, 0.008),
        "Gold": walk(2380, 0.0002, 0.006),
    }
    import math as _m

    for asset, prices in raw.items():
        rets = [0.0]
        for i in range(1, len(prices)):
            rets.append(_m.log(prices[i] / prices[i - 1]) if prices[i - 1] > 0 else 0.0)
        # rolling 20d vol annualised, as fractions (frontend formats)
        roll_vol = []
        for i in range(len(prices)):
            w = rets[max(1, i - 19) : i + 1]
            if len(w) < 5:
                roll_vol.append(None)
                continue
            m = sum(w) / len(w)
            var = sum((x - m) ** 2 for x in w) / (len(w) - 1)
            roll_vol.append(round(_m.sqrt(var) * _m.sqrt(252) * 100, 2))
        # rolling corr vs main (main = 1.0)
        if asset == TICKER:
            roll_corr = [1.0] * len(prices)
        else:
            main_rets = [0.0]
            for i in range(1, len(main_prices)):
                main_rets.append(_m.log(main_prices[i] / main_prices[i - 1]))
            roll_corr = []
            for i in range(len(prices)):
                a = main_rets[max(1, i - 19) : i + 1]
                b = rets[max(1, i - 19) : i + 1]
                if len(a) < 5:
                    roll_corr.append(None)
                    continue
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                cov = sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (len(a) - 1)
                va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
                vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
                roll_corr.append(round(cov / _m.sqrt(va * vb), 3) if va > 0 and vb > 0 else None)
        assets[asset] = {
            "prices": prices,
            "cum_returns": [round((p / prices[0] - 1) * 100, 2) for p in prices],
            "rolling_vol": roll_vol,
            "rolling_corr": roll_corr,
        }
    return {
        "status": "ok",
        "dates": dates,
        "assets": assets,
        "instrument": TICKER,
        "periods": {
            "1M": dates[-30],
            "1Q": dates[-90],
            "YTD": f"{ref.year}-01-01",
        },
        "sample": True,
        "sample_note": f"Synthetic walk for {TICKER}+benchmarks ending {REF_DATE}.",
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cal = gen_calendar()
    chain = gen_option_chain()
    odds = gen_odds(chain)
    mr = gen_market_review()
    (OUT_DIR / "expiry_calendar.json").write_text(json.dumps(cal, indent=2) + "\n")
    (OUT_DIR / "option_chain.nvda.json").write_text(json.dumps(chain, indent=2) + "\n")
    (OUT_DIR / "odds_with_vol.nvda.json").write_text(json.dumps(odds, indent=2) + "\n")
    (OUT_DIR / "market_review_ts.nvda.json").write_text(json.dumps(mr, indent=2) + "\n")
    print(f"wrote 4 fixtures to {OUT_DIR}")


if __name__ == "__main__":
    main()

"""Tests for core/optsim (pricing, margin, scenario grid, listed market) and scripts/optsim.py.

Known-answer checks only: closed-form identities, rule arithmetic, the existing
OptionLab Black-Scholes implementation as an oracle, and chains priced with the
European model on a known smile (so the IVs they imply are known).
"""

import datetime as dt
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from core.options.greeks.black_scholes import greeks_vectorized
from core.optsim import (
    PRODUCTS,
    Market,
    Position,
    Smile,
    american,
    breakeven_iv,
    european,
    implied_vol,
    iv_curve,
    leg_iv,
    listed_market,
    make_leg,
    margin_class,
    nearest_expiry,
    nearest_quote,
    pm_bpr,
    pm_offsets,
    regt_bpr,
    render_grid_png,
    scenario_grid,
    strike_for_delta,
    time_profile,
)

ROOT = Path(__file__).resolve().parents[1]


# ── pricing ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("kind", ["call", "put"])
def test_european_pricing_matches_optionlab_black_scholes(kind):
    S = np.linspace(70, 130, 13)
    ours = european(kind, S, 100.0, 37 / 365, 0.045, 0.0, 0.27)
    ref = greeks_vectorized(S, 100.0, 37 / 365, 0.045, 0.27, option_type=kind)
    for ours_key, ref_key in [
        ("price", "bs_price"),
        ("delta", "delta"),
        ("gamma", "gamma"),
        ("theta", "theta"),
        ("vega", "vega"),
    ]:
        np.testing.assert_allclose(ours[ours_key], ref[ref_key], atol=1e-10)


def test_european_put_call_parity_holds_with_dividends():
    S, K, T, r, q, v = 105.0, 100.0, 0.4, 0.04, 0.02, 0.3
    c = european("call", S, K, T, r, q, v)["price"]
    p = european("put", S, K, T, r, q, v)["price"]
    assert c - p == pytest.approx(S * np.exp(-q * T) - K * np.exp(-r * T), abs=1e-10)


def test_american_put_is_at_least_european_and_intrinsic():
    S = np.linspace(60, 140, 17)
    am = american("put", S, 100.0, 0.25, 0.045, 0.013, 0.25)["price"]
    eu = european("put", S, 100.0, 0.25, 0.045, 0.013, 0.25)["price"]
    assert np.all(am >= eu - 1e-12)
    assert np.all(am >= np.maximum(100.0 - S, 0.0) - 1e-12)


def test_american_call_without_dividends_equals_european():
    S = np.linspace(80, 120, 9)
    am = american("call", S, 100.0, 0.5, 0.045, 0.0, 0.3)
    eu = european("call", S, 100.0, 0.5, 0.045, 0.0, 0.3)
    np.testing.assert_allclose(am["price"], eu["price"], atol=1e-3)
    np.testing.assert_allclose(am["delta"], eu["delta"], atol=5e-3)


def test_american_put_converges_to_a_fine_tree():
    S = np.array([85.0, 95.0, 100.0, 110.0])
    coarse = american("put", S, 100.0, 60 / 365, 0.045, 0.013, 0.3)["price"]
    fine = american("put", S, 100.0, 60 / 365, 0.045, 0.013, 0.3, steps=2000)["price"]
    np.testing.assert_allclose(coarse, fine, atol=5e-3)


@pytest.mark.parametrize("style", ["european", "american"])
def test_expired_option_is_worth_intrinsic(style):
    pricer = european if style == "european" else american
    g = pricer("put", np.array([90.0, 110.0]), 100.0, 0.0, 0.045, 0.0, 0.2)
    np.testing.assert_allclose(g["price"], [10.0, 0.0])
    np.testing.assert_allclose(g["delta"], [-1.0, 0.0])
    np.testing.assert_allclose(g["vega"], [0.0, 0.0])


# ── margin ────────────────────────────────────────────────────────────
def _regt(legs, spot, product="index"):
    kinds = [k for k, *_ in legs]
    strikes = [k_ for _, k_, *_ in legs]
    qtys = [q for *_, q, _ in legs]
    values = np.array([[v] for *_, v in legs])
    bpr, method = regt_bpr(kinds, strikes, qtys, values, np.array([spot]), 100, product)
    return float(bpr[0]), method


def test_regt_naked_short_put_charges_pct_of_spot_less_otm():
    assert _regt([("put", 584.0, -1, 7.65)], 600.0, "etf") == (pytest.approx(7400.0), "naked")


def test_regt_naked_short_put_falls_back_to_ten_percent_of_strike():
    bpr, _ = _regt([("put", 500.0, -1, 0.40)], 600.0, "etf")
    assert bpr == pytest.approx(5000.0)


def test_regt_strangle_takes_greater_side_plus_other_premium():
    # call: 1.0 + max(15 - 10, 10) = 11 ; put: 1.5 + max(15 - 10, 9) = 10.5
    # requirement 11 + 1.5 = 12.5, less proceeds 2.5 -> 10 per share
    bpr, method = _regt([("call", 110.0, -1, 1.0), ("put", 90.0, -1, 1.5)], 100.0)
    assert (bpr, method) == (pytest.approx(1000.0), "naked")


def test_regt_credit_spread_is_width_minus_credit():
    bpr, method = _regt([("put", 100.0, -1, 3.0), ("put", 95.0, 1, 1.5)], 102.0)
    assert (bpr, method) == (pytest.approx(350.0), "defined_risk")


def test_regt_iron_condor_uses_the_wider_wing():
    legs = [("put", 90.0, -1, 1.0), ("put", 85.0, 1, 0.5), ("call", 110.0, -1, 1.2), ("call", 120.0, 1, 0.4)]
    bpr, method = _regt(legs, 100.0)
    assert (bpr, method) == (pytest.approx((10.0 - 1.3) * 100), "defined_risk")


def test_regt_long_option_costs_its_premium():
    assert _regt([("call", 100.0, 2, 3.0)], 100.0) == (pytest.approx(600.0), "defined_risk")


def test_regt_calendar_is_defined_risk_but_a_reverse_calendar_is_not():
    spot = np.array([100.0])
    # Calendar: the long 60-day call covers the short 30-day call; Reg-T is the net debit.
    bpr, method = regt_bpr(
        ["call", "call"], [100.0, 100.0], [-1, 1], [[2.0], [3.5]], spot, 100, "equity", dtes=[30, 60]
    )
    assert (float(bpr[0]), method) == (pytest.approx(150.0), "defined_risk")
    # Reverse calendar: the long expires first and covers nothing — a naked short (20% x 100) plus the long.
    bpr, method = regt_bpr(
        ["call", "call"], [100.0, 100.0], [-1, 1], [[3.5], [2.0]], spot, 100, "equity", dtes=[60, 30]
    )
    assert (float(bpr[0]), method) == (pytest.approx(2200.0), "conservative")


def test_regt_cover_matches_shorts_to_longs_by_expiry():
    kinds, strikes, qtys, values, spot = (
        ["put"] * 4,
        [100.0, 100.0, 95.0, 95.0],
        [-1, -1, 1, 1],
        np.ones((4, 1)),
        [100.0],
    )
    # Longs at 45 and 60 days cover shorts at 30 and 60 days...
    assert regt_bpr(kinds, strikes, qtys, values, spot, 100, "equity", dtes=[30, 60, 45, 60])[1] == "defined_risk"
    # ...longs at 30 and 60 leave one of two 60-day shorts covered only by a long that expires first.
    assert regt_bpr(kinds, strikes, qtys, values, spot, 100, "equity", dtes=[60, 60, 30, 60])[1] == "conservative"


def test_scenario_grid_margins_a_reverse_calendar_as_naked_until_the_long_expires():
    mkt = Market(spot=100.0, rate=0.045, div_yield=0.0)
    legs = [
        make_leg("call", "short", 100.0, 60, mkt, iv=0.25),
        make_leg("call", "long", 100.0, 30, mkt, iv=0.25),
    ]
    rows = time_profile(
        scenario_grid(Position(legs, product="equity"), mkt, n_spots=11, days=[0, 15, 45], iv_shifts=(0.0,))
    )
    assert [r["regt_method"] for r in rows] == ["conservative", "conservative", "naked"]
    normal = [make_leg("call", "short", 100.0, 30, mkt, iv=0.25), make_leg("call", "long", 100.0, 60, mkt, iv=0.25)]
    rows = time_profile(
        scenario_grid(Position(normal, product="equity"), mkt, n_spots=11, days=[0, 15], iv_shifts=(0.0,))
    )
    assert [r["regt_method"] for r in rows] == ["defined_risk", "defined_risk"]
    assert rows[0]["regt"] == pytest.approx(rows[0]["value"])  # the net debit


def test_pm_offsets_span_the_product_range():
    off = pm_offsets("index")
    assert off[0] == 0.0 and len(off) == 11
    assert off.min() == pytest.approx(-0.08) and off.max() == pytest.approx(0.06)
    assert pm_offsets("equity").min() == pytest.approx(-0.15)


@pytest.mark.parametrize(
    ("symbol", "kind", "product"),
    [
        ("^SPX", "index", "index"),
        ("^NDX", None, "index"),  # named high-cap index: the symbol settles it
        ("^RUT", "index", "index_small"),
        ("^VIX", None, "index_small"),  # any other ^ symbol is an index
        ("SPY", "etf", "etf"),
        ("SPY", None, "etf"),  # a failed type lookup cannot demote SPY
        ("IWM", "etf", "index_small"),
        ("XLE", "etf", "equity"),  # narrow-based ETF: the equity requirement
        ("TQQQ", "etf", "equity"),
        ("AAPL", "equity", "equity"),
        ("BTC-USD", "other", "equity"),
        ("ABCD", None, "equity"),  # unknown: the most conservative class
    ],
)
def test_margin_class_follows_the_underlying_type(symbol, kind, product):
    assert margin_class(symbol, kind) == product and product in PRODUCTS


def test_pm_takes_worst_loss_with_per_contract_minimum():
    values = np.array([-500.0, -900.0, -2400.0, -700.0])  # base first
    assert float(pm_bpr(values, n_contracts=1, multiplier=100)) == pytest.approx(1900.0)
    assert float(pm_bpr(np.array([-500.0, -501.0]), n_contracts=2, multiplier=100)) == pytest.approx(75.0)


# ── scenario grid ─────────────────────────────────────────────────────
def _strangle(style="european"):
    mkt = Market(spot=100.0, rate=0.045, div_yield=0.013)
    smile = Smile(atm_iv=0.2, skew=-0.5, curvature=1.0)
    legs = [
        make_leg("put", "short", 90.0, 30, mkt, smile=smile, style=style),
        make_leg("call", "short", 110.0, 30, mkt, smile=smile, style=style),
    ]
    return Position(legs, style=style, product="etf", name="test"), mkt


def test_scenario_grid_pnl_is_zero_at_entry():
    pos, mkt = _strangle()
    g = scenario_grid(pos, mkt, n_spots=21, days=[0, 10, 30])
    flat = int(np.argmin(np.abs(g.iv_shifts)))
    assert g.pnl[flat, 0, g.base_index] == pytest.approx(0.0, abs=1e-9)


def test_scenario_grid_expiry_pnl_equals_payoff_minus_entry():
    pos, mkt = _strangle()
    g = scenario_grid(pos, mkt, n_spots=21, days=[0, 30])
    payoff = -100 * (np.maximum(90.0 - g.spots, 0) + np.maximum(g.spots - 110.0, 0))
    np.testing.assert_allclose(g.pnl[1, -1], payoff - g.entry_value, atol=1e-9)
    assert g.regt[1, -1].max() == 0.0  # expired legs carry no margin


def test_scenario_grid_always_includes_entry_day_and_unshifted_iv():
    pos, mkt = _strangle()
    g = scenario_grid(pos, mkt, n_spots=11, days=[10, 30], iv_shifts=(-0.05, 0.05))
    assert g.days.tolist() == [0.0, 10.0, 30.0]
    assert g.iv_shifts.tolist() == [-0.05, 0.0, 0.05]
    assert time_profile(g)[0]["pnl"] == pytest.approx(0.0, abs=1e-9)


def test_style_switch_keeps_value_close_for_calls_without_dividends():
    mkt = Market(spot=100.0, rate=0.045, div_yield=0.0)
    vals = {}
    for style in ("european", "american"):
        pos = Position([make_leg("call", "long", 100.0, 60, mkt, iv=0.25, style=style)], style=style)
        vals[style] = scenario_grid(pos, mkt, n_spots=11, days=[0, 30], iv_shifts=(0.0,)).value
    np.testing.assert_allclose(vals["american"], vals["european"], atol=0.2)  # dollars per contract


def test_strike_for_delta_hits_the_target():
    mkt = Market(spot=6000.0, rate=0.045, div_yield=0.013)
    smile = Smile(atm_iv=0.16, skew=-0.77, curvature=1.0, floor=0.08)
    k = strike_for_delta("put", -0.16, 45, mkt, smile)
    d = european("put", 6000.0, k, 45 / 365, 0.045, 0.013, smile.iv(k, 6000.0))["delta"]
    assert float(d) == pytest.approx(-0.16, abs=1e-6)


def test_time_profile_has_one_row_per_day_with_both_margins():
    pos, mkt = _strangle("american")
    g = scenario_grid(pos, mkt, n_spots=11, days=[0, 15, 30], iv_shifts=(0.0,))
    rows = time_profile(g)
    assert [r["day"] for r in rows] == [0.0, 15.0, 30.0]
    assert rows[0]["regt"] > 0 and rows[0]["pm"] > 0 and rows[0]["regt_method"] == "naked"


def test_render_grid_png_returns_png_bytes():
    pos, mkt = _strangle()
    png = render_grid_png(scenario_grid(pos, mkt, n_spots=21, days=[0, 10, 20, 30]), dpi=60)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


# ── implied vol and break-even IV ─────────────────────────────────────
@pytest.mark.parametrize("kind", ["call", "put"])
def test_implied_vol_inverts_european_prices(kind):
    S = np.array([80.0, 95.0, 100.0, 105.0, 120.0])
    sigma = np.array([0.15, 0.25, 0.4, 0.6, 1.2])
    price = european(kind, S, 100.0, 50 / 365, 0.045, 0.013, sigma)["price"]
    np.testing.assert_allclose(implied_vol(kind, price, S, 100.0, 50 / 365, 0.045, 0.013), sigma, atol=1e-8)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_implied_vol_inverts_american_tree_prices_below_the_european_root(kind):
    # Not deeper in the money: where exercising now is optimal the price is flat in vol.
    S = np.array([85.0, 100.0, 120.0])
    sigma = np.array([0.2, 0.3, 0.5])
    price = american(kind, S, 100.0, 120 / 365, 0.045, 0.02, sigma, steps=100)["price"]
    am = implied_vol(kind, price, S, 100.0, 120 / 365, 0.045, 0.02, "american", 100)
    np.testing.assert_allclose(am, sigma, atol=1e-5)
    eu = implied_vol(kind, price, S, 100.0, 120 / 365, 0.045, 0.02)
    assert np.all(am <= eu + 1e-12)  # an American option is never worth less at the same vol


def test_implied_vol_is_nan_when_no_vol_in_range_reprices_the_option():
    T, r = 30 / 365, 0.045
    below_floor = implied_vol("call", 15.0, 120.0, 100.0, T, r, 0.0)  # worth over 20 at any vol
    above_cap = implied_vol("call", 99.0, 100.0, 100.0, T, r, 0.0)  # worth ~33 even at 300%
    expired = implied_vol("put", 5.0, 95.0, 100.0, 0.0, r, 0.0)
    free = implied_vol("put", 0.0, 95.0, 100.0, T, r, 0.0)
    assert all(np.isnan(v) for v in (below_floor, above_cap, expired, free))


def test_breakeven_iv_reprices_each_leg_to_its_premium():
    pos, mkt = _strangle()
    spots = np.linspace(85.0, 115.0, 31)
    days = np.array([0.0, 10.0, 20.0, 30.0])
    for leg, row in zip(pos.legs, breakeven_iv(pos, mkt, spots, days), strict=True):
        iv = row["iv"]
        assert iv.shape == (4, 31)
        assert iv[0, 15] == pytest.approx(leg.iv, abs=1e-8)  # day 0 at the entry spot: the leg's own IV
        assert np.isnan(iv[-1]).all()  # day 30 is the expiry: no IV moves an expiring option
        live = np.isfinite(iv[:3])
        T = ((leg.dte - days[:3]) / 365.0)[:, None]
        S = np.broadcast_to(spots, (3, 31))
        value = european(leg.option_type, S, leg.strike, T, mkt.rate, mkt.div_yield, np.where(live, iv[:3], 0.2))
        np.testing.assert_allclose(value["price"][live], leg.premium, atol=1e-6)
        sign = 1.0 if leg.option_type == "call" else -1.0
        assert row["expiry_breakeven"] == pytest.approx(leg.strike + sign * leg.premium)


def test_breakeven_iv_rises_as_an_otm_leg_decays_at_the_entry_spot():
    pos, mkt = _strangle()
    for row in breakeven_iv(pos, mkt, [100.0], [0.0, 10.0, 20.0, 25.0]):
        assert np.all(np.diff(row["iv"][:, 0]) > 0)  # holding its value takes ever more IV


# ── listed market (ticker mode) ───────────────────────────────────────
TODAY = dt.date(2026, 10, 21)


def _known_smile(K):
    k = np.log(np.asarray(K, dtype=float) / 100.0)
    return 0.2 - 0.5 * k + 1.0 * k * k


def _priced_rows(kind, strikes, T, spot=100.0, r=0.045, q=0.01, spread=0.1):
    """Chain rows whose mids are the European price on ``_known_smile``."""
    strikes = np.asarray(strikes, dtype=float)
    iv = _known_smile(strikes)
    mid = european(kind, spot, strikes, T, r, q, iv)["price"]
    return [
        {"strike": k, "bid": max(m - spread / 2, 0.0), "ask": m + spread / 2, "iv": v}
        for k, m, v in zip(strikes, mid, iv, strict=True)
    ]


def test_listed_market_keeps_expiries_a_day_out_with_sorted_unique_quotes():
    chain = {
        "2026-10-21": {"calls": [{"strike": 100, "bid": 1.0, "ask": 1.2, "iv": 0.2}]},  # expires today
        "2026-10-31": {
            "calls": [
                {"strike": 105, "bid": 0, "ask": 1.0, "iv": 0.2},
                {"strike": 95, "bid": 6.0, "ask": 5.0, "iv": None},
                {"strike": 100, "bid": 2.0, "ask": 2.2, "iv": 0.21},
                {"strike": 100, "bid": 9.0, "ask": 9.0, "iv": 0.9},
            ],
            "puts": [],
        },
        "2026-11-30": {"calls": [], "puts": []},  # nothing listed
        "not-a-date": {"calls": [{"strike": 100}]},
    }
    listed = listed_market("TEST", 100.0, chain, today=TODAY, as_of="2026-10-21T14:00:00+00:00")
    assert [e.expiry for e in listed.expiries] == ["2026-10-31"] and listed.as_of.startswith("2026-10-21")
    expiry = listed.expiries[0]
    assert expiry.dte == 10 and [q.strike for q in expiry.calls] == [95.0, 100.0, 105.0]
    crossed, quoted, one_sided = expiry.calls
    assert quoted.mid == pytest.approx(2.1) and quoted.iv == 0.21  # the first row of a repeated strike wins
    assert one_sided.bid is None and one_sided.mid is None  # a zero bid is no bid
    assert crossed.mid is None  # ask below bid
    with pytest.raises(ValueError):
        listed_market("TEST", None, chain, today=TODAY)


def test_nearest_expiry_and_quote_break_ties_towards_more_time_and_the_lower_strike():
    chain = {"2026-10-31": {"puts": [{"strike": 95}, {"strike": 105}]}, "2026-11-10": {"puts": [{"strike": 100}]}}
    listed = listed_market("TEST", 100.0, chain, today=TODAY)
    assert nearest_expiry(listed, 15).expiry == "2026-11-10"  # 10 and 20 DTE are both 5 days off
    assert nearest_quote(listed.expiries[0].puts, 100.0).strike == 95.0


def test_iv_curve_recovers_the_smile_a_chain_was_priced_with():
    T = 30 / 365
    strikes = np.arange(70.0, 131.0, 5.0)
    chain = {"2026-11-20": {"calls": _priced_rows("call", strikes, T), "puts": _priced_rows("put", strikes, T)}}
    expiry = listed_market("TEST", 100.0, chain, today=TODAY).expiries[0]
    curve = iv_curve(expiry, Market(spot=100.0, rate=0.045, div_yield=0.01))
    np.testing.assert_allclose(curve.ivs, _known_smile(curve.strikes), atol=1e-6)
    assert curve.iv(102.5) == pytest.approx(0.5 * float(_known_smile(100.0) + _known_smile(105.0)), abs=1e-6)
    assert curve.iv(10.0) == pytest.approx(float(_known_smile(70.0)), abs=1e-6)  # flat beyond the ends


def test_iv_curve_falls_back_to_the_quoted_iv_without_a_two_sided_quote():
    chain = {"2026-11-20": {"calls": [{"strike": 110, "bid": 0, "ask": 0, "iv": 0.31}], "puts": [{"strike": 90}]}}
    expiry = listed_market("TEST", 100.0, chain, today=TODAY).expiries[0]
    curve = iv_curve(expiry, Market(spot=100.0))
    assert curve.strikes.tolist() == [110.0] and curve.ivs.tolist() == [0.31]
    bare = listed_market("TEST", 100.0, {"2026-11-20": {"puts": [{"strike": 90, "iv": 0.0}]}}, today=TODAY)
    with pytest.raises(ValueError):
        iv_curve(bare.expiries[0], Market(spot=100.0))


@pytest.mark.parametrize("style", ["european", "american"])
def test_leg_iv_prices_a_quoted_leg_at_its_mid_and_an_unquoted_one_on_the_curve(style):
    mkt = Market(spot=100.0, rate=0.045, div_yield=0.01)
    rows = [{"strike": 95, "bid": 1.10, "ask": 1.30, "iv": 0.5}, {"strike": 90, "bid": 0, "ask": 0.4, "iv": 0.33}]
    expiry = listed_market("TEST", 100.0, {"2026-11-20": {"puts": rows}}, today=TODAY).expiries[0]
    curve = iv_curve(expiry, mkt)
    unquoted, quoted = expiry.puts  # sorted by strike: 90, 95
    iv, source = leg_iv("put", quoted, expiry, mkt, curve, style, 100)
    premium = make_leg("put", "short", quoted.strike, expiry.dte, mkt, iv=iv, style=style, steps=100).premium
    assert source == "mid" and premium == pytest.approx(1.20, abs=1e-4)
    iv, source = leg_iv("put", unquoted, expiry, mkt, curve, style, 100)
    assert source == "curve" and iv == pytest.approx(0.33)


# ── CLI ───────────────────────────────────────────────────────────────
def test_cli_writes_png_and_json_for_the_example(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("optsim_cli", ROOT / "scripts" / "optsim.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main([str(ROOT / "docs/optsim/examples/spx_short_strangle.toml"), "--out", str(tmp_path)]) == 0
    assert "Reg-T" in capsys.readouterr().out
    assert len(list(tmp_path.glob("*.png"))) == 1 and len(list(tmp_path.glob("*.json"))) == 1

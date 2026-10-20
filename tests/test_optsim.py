"""Tests for core/optsim (pricing, margin, scenario grid) and scripts/optsim.py.

Known-answer checks only: closed-form identities, rule arithmetic, and the
existing OptionLab Black-Scholes implementation as an oracle.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from core.options.greeks.black_scholes import greeks_vectorized
from core.optsim import (
    Market,
    Position,
    Smile,
    american,
    european,
    make_leg,
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


def test_pm_offsets_span_the_product_range():
    off = pm_offsets("index")
    assert off[0] == 0.0 and len(off) == 11
    assert off.min() == pytest.approx(-0.08) and off.max() == pytest.approx(0.06)
    assert pm_offsets("equity").min() == pytest.approx(-0.15)


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


# ── CLI ───────────────────────────────────────────────────────────────
def test_cli_writes_png_and_json_for_the_example(tmp_path, capsys):
    spec = importlib.util.spec_from_file_location("optsim_cli", ROOT / "scripts" / "optsim.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    assert cli.main([str(ROOT / "docs/optsim/examples/spx_short_strangle.toml"), "--out", str(tmp_path)]) == 0
    assert "Reg-T" in capsys.readouterr().out
    assert len(list(tmp_path.glob("*.png"))) == 1 and len(list(tmp_path.glob("*.json"))) == 1

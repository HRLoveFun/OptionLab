"""End-to-end smoke for the Option Pricing Matrix tab.

The tab drives the pure engine (static/sim/option_pricing_matrix.js) through the
real Flask-served page. Its columns are sourced from /api/expiry_calendar,
which `mock_apis` fulfils with a stable 18-run DTE ladder (the calendar
maths itself is covered by tests/test_expiry_calendar*.py). Assertions run
against the rendered grid, the KPI strip and the CSS-driven visibility
switches.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

_ACTIVE_RE = re.compile(r"\bactive\b")
_HOVER_RE = re.compile(r"\bis-hover\b")
# Persistent mark on the picked sigma-reference column (<col> + header <th>).
_REF_RE = re.compile(r"\bis-ref\b")
# Console errors that are environmental (missing CDN) rather than app bugs.
_RESOURCE_ERR_RE = re.compile(r"Failed to load resource|net::ERR", re.IGNORECASE)
# Sub-pixel layout noise: borders and zoom make exact equality impossible.
_TOLERANCE_PX = 1.0

ROWS = 41  # spot 100 ±20%, integer strikes
# The column count is data-driven: the grid is keyed on the real expiry
# calendar (standard + daily expiries), not on a fixed DTE ladder, so every
# assertion that needs it reads it back from the rendered grid.


def _app_errors(js_errors: list[str]) -> list[str]:
    return [e for e in js_errors if not _RESOURCE_ERR_RE.search(e)]


def _box(locator) -> dict:
    """Bounding box of a locator, failing loudly instead of returning None."""
    box = locator.bounding_box()
    assert box is not None, "locator has no box — is it visible?"
    return box


def _mid(box: dict) -> float:
    return box["x"] + box["width"] / 2


def _open_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('.tab-btn[data-tab="tab-option-pricing-matrix"]').click()
    expect(page.locator("#tab-option-pricing-matrix")).to_have_class(_ACTIVE_RE, timeout=3000)
    expect(page.locator("#opm-matrix")).to_be_visible(timeout=5000)


def _dtes(page: Page) -> list[int]:
    """Days to expiration of every rendered column, left to right."""
    return page.evaluate("() => window.optionPricingMatrixDebug().data.columns.map((c) => c.dte)")


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_renders_default_grid(page: Page, live_server: str, js_errors: list[str]) -> None:
    """Defaults (100 / 25% / 3% / 2% spread) produce a full strike × expiry grid."""
    _open_tab(page, live_server)
    dtes = _dtes(page)
    assert len(dtes) > 1

    # Default inputs: spot 100, IV 25%, rate 3%, spread 2% (buy side).
    expect(page.locator("#opm-spread")).to_have_value("2")
    expect(page.locator('[data-opm-side="buy"]')).to_have_attribute("aria-pressed", "true")

    expect(page.locator("#opm-matrix tbody tr")).to_have_count(ROWS)
    expect(page.locator("#opm-matrix tbody tr").first.locator("td.opm-cell")).to_have_count(len(dtes))
    expect(page.locator("#opm-matrix .opm-half--call")).to_have_count(ROWS * len(dtes))
    expect(page.locator("#opm-matrix .opm-half--put")).to_have_count(ROWS * len(dtes))
    # One column per expiry + the strike and sigma rails
    expect(page.locator("#opm-matrix thead th")).to_have_count(len(dtes) + 2)

    # Column headers read "DTE · period-volatility" (e.g. "1D · 1.3%"),
    # and the page explains what the percentage means.
    first_col = page.locator("#opm-matrix thead th[data-col='0']")
    expect(first_col).to_contain_text(f"{dtes[0]}D")
    # The legend card holds two lists, so scope to the card — a bare
    # .opm-legend-list locator matches both and trips strict mode.
    expect(page.locator(".opm-legend")).to_contain_text("1σ")

    # P1 hero + KPI strip are populated.
    expect(page.locator("#opm-hero-value")).to_contain_text("%", timeout=3000)
    expect(page.locator("#opm-kpi-grid")).to_have_text(f"{ROWS} × {len(dtes)}")
    expect(page.locator("#opm-kpi-sigma")).not_to_have_text("—")
    expect(page.locator("#opm-kpi-call")).not_to_have_text("—")
    expect(page.locator("#opm-kpi-put")).not_to_have_text("—")

    # ATM row is marked, and strikes run 80 → 120 in integer steps.
    expect(page.locator("#opm-matrix tr.opm-row-atm")).to_have_count(1)
    expect(page.locator("#opm-matrix tbody tr").first.locator("th[scope='row']")).to_have_text("80")
    expect(page.locator("#opm-matrix tbody tr").last.locator("th[scope='row']")).to_have_text("120")

    assert _app_errors(js_errors) == [], f"JS errors in option pricing matrix tab: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_toggles_hide_values(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The four switches are independent and CSS-only."""
    _open_tab(page, live_server)

    cell = page.locator("#opm-matrix tbody tr").first.locator("td.opm-cell").first
    price = cell.locator(".opm-val--price").first
    rate = cell.locator(".opm-val--rate").first
    call_half = cell.locator(".opm-half--call")
    put_half = cell.locator(".opm-half--put")

    expect(price).to_be_visible()
    expect(rate).to_be_visible()

    # Hide prices — rates remain, so no hint is shown.
    page.locator('[data-opm-toggle="price"]').click()
    expect(price).to_be_hidden()
    expect(rate).to_be_visible()
    expect(page.locator("#opm-all-hidden")).to_be_hidden()

    # Hiding rates too leaves nothing to show → guidance appears.
    page.locator('[data-opm-toggle="premium"]').click()
    expect(page.locator("#opm-all-hidden")).to_be_visible()

    # Restore both.
    page.locator('[data-opm-toggle="premium"]').click()
    page.locator('[data-opm-toggle="price"]').click()
    expect(price).to_be_visible()

    # Call / Put are independent.
    page.locator('[data-opm-toggle="call"]').click()
    expect(call_half).to_be_hidden()
    expect(put_half).to_be_visible()
    page.locator('[data-opm-toggle="call"]').click()
    expect(call_half).to_be_visible()

    assert _app_errors(js_errors) == [], f"JS errors while toggling: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_recomputes_on_input_change(page: Page, live_server: str, js_errors: list[str]) -> None:
    """Changing IV reprices the grid; changing the tenor re-scales the sigma rail."""
    _open_tab(page, live_server)

    call_kpi = page.locator("#opm-kpi-call")
    sigma_kpi = page.locator("#opm-kpi-sigma")
    before_call = call_kpi.inner_text()
    before_sigma = sigma_kpi.inner_text()

    dtes = _dtes(page)
    page.fill("#opm-iv", "45")
    expect(call_kpi).not_to_have_text(before_call, timeout=3000)
    expect(sigma_kpi).not_to_have_text(before_sigma, timeout=3000)

    # The sigma rail follows the selected reference column.
    sigma_cell = page.locator("#opm-matrix tbody tr").first.locator("td.opm-sigma")
    before_rail = sigma_cell.inner_text()
    # The hero band (ATM premium rate, 1σ move, ATM call/put) is pinned to 30D
    # and must NOT move when the sigma reference column changes.
    hero_call = call_kpi.inner_text()
    hero_put = page.locator("#opm-kpi-put").inner_text()
    hero_sigma = sigma_kpi.inner_text()
    # The select is gone: the column HEADER is the control, and it keeps a
    # persistent .is-ref mark so the picked column is never invisible.
    page.locator("#opm-matrix th.opm-head-dte[data-col='0']").click()
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='0']")).to_have_class(_REF_RE)
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[0]}D")
    expect(sigma_cell).not_to_have_text(before_rail)
    expect(call_kpi).to_have_text(hero_call)
    expect(page.locator("#opm-kpi-put")).to_have_text(hero_put)
    expect(sigma_kpi).to_have_text(hero_sigma)

    # A spread moves the buyer's fill above the mid.
    mid_sub = page.locator("#opm-kpi-call-sub")
    expect(mid_sub).to_contain_text("mid")
    page.fill("#opm-spread", "6")
    expect(page.locator("#opm-kpi-call")).not_to_have_text(before_call, timeout=3000)

    assert _app_errors(js_errors) == [], f"JS errors after input change: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_header_lines_up_with_cells(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The CALL / PUT header halves sit exactly over the halves they label.

    This is the regression guard for the x axis: a header that is merely
    centred in the column reads as if it belongs to the right-hand half.
    """
    _open_tab(page, live_server)

    row = page.locator("#opm-matrix tbody tr").nth(4)
    for side in ("call", "put"):
        head = _box(page.locator(f"#opm-matrix th.opm-head-dte[data-col='3'] .opm-head-half--{side}"))
        cell = _box(row.locator(f"td.opm-cell[data-col='3'] .opm-half--{side}"))
        assert abs(head["x"] - cell["x"]) <= _TOLERANCE_PX, f"{side} half: {head['x']} vs {cell['x']}"
        assert abs(head["width"] - cell["width"]) <= _TOLERANCE_PX, (
            f"{side} half width: {head['width']} vs {cell['width']}"
        )

    # The tenor caption spans the whole column, not one half.
    main = _box(page.locator("#opm-matrix th.opm-head-dte[data-col='3'] .opm-head-main"))
    cell = _box(row.locator("td.opm-cell[data-col='3']"))
    assert abs(_mid(main) - _mid(cell)) <= _TOLERANCE_PX

    # Same check on the last column, where drift is most visible.
    last = len(_dtes(page)) - 1
    head = _box(page.locator(f"#opm-matrix th.opm-head-dte[data-col='{last}'] .opm-head-half--put"))
    cell = _box(row.locator(f"td.opm-cell[data-col='{last}'] .opm-half--put"))
    assert abs(head["x"] - cell["x"]) <= _TOLERANCE_PX

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_sticky_rails_stay_in_register(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The sticky sigma rail is pinned to the measured strike column.

    `width` is only a hint under auto table layout, so a long strike can
    stretch column one past the hard-coded fallback and slide the rail out of
    register with its own header.
    """
    _open_tab(page, live_server)

    def rail_gap() -> float:
        strike = _box(page.locator("#opm-matrix tbody tr").first.locator("th[scope='row']"))
        sigma = _box(page.locator("#opm-matrix tbody tr").first.locator("td.opm-sigma"))
        return abs((strike["x"] + strike["width"]) - sigma["x"])

    assert rail_gap() <= _TOLERANCE_PX

    # Eight-digit strikes are far wider than the 4.4rem rail fallback.
    page.fill("#opm-price", "9876543")
    expect(page.locator("#opm-matrix tbody tr").first.locator("th[scope='row']")).not_to_have_text("80", timeout=5000)
    assert rail_gap() <= _TOLERANCE_PX

    # And the header rail followed the body rail.
    head = _box(page.locator("#opm-head-sigma"))
    sigma = _box(page.locator("#opm-matrix tbody tr").first.locator("td.opm-sigma"))
    assert abs(head["x"] - sigma["x"]) <= _TOLERANCE_PX

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_fill_side_switch_reprices(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The buy / sell switch is exclusive and reprices — unlike the CSS toggles.

    It lives in the panel toolbar because it changes the price basis of every
    cell, so flipping it is a real recompute, not an attribute write.
    """
    _open_tab(page, live_server)

    buy = page.locator('[data-opm-side="buy"]')
    sell = page.locator('[data-opm-side="sell"]')
    # It sits with the Price / Prem. rate / Call / Put switches above the grid.
    expect(page.locator(".opm-matrix-toolbar__right [data-opm-side='buy']")).to_have_count(1)
    expect(buy).to_have_attribute("aria-pressed", "true")
    expect(sell).to_have_attribute("aria-pressed", "false")

    # A real spread is what separates the two sides of the book.
    page.fill("#opm-spread", "8")
    expect(page.locator("#opm-kpi-call")).not_to_have_text("—", timeout=3000)

    def atm_call() -> dict:
        return page.evaluate(
            "() => { const d = window.optionPricingMatrixDebug().data;"
            " const c = d.rows[d.atm_index].cells[d.ref_column_index].call;"
            " return { mid: c.mid, fill: c.fill, side: d.perspective }; }"
        )

    bought = atm_call()
    assert bought["side"] == "buy"
    assert bought["fill"] > bought["mid"]  # buyer crosses to the ask

    sell.click()
    expect(sell).to_have_attribute("aria-pressed", "true")
    expect(buy).to_have_attribute("aria-pressed", "false")

    sold = atm_call()
    assert sold["side"] == "sell"
    assert sold["fill"] < sold["mid"]  # seller hits the bid
    assert sold["fill"] < bought["fill"]

    # Clicking the side that is already on is a no-op.
    sell.click()
    expect(sell).to_have_attribute("aria-pressed", "true")
    assert atm_call() == sold

    assert _app_errors(js_errors) == [], f"JS errors after flipping fill side: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_spread_floor_is_one_tick(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The spread's DOLLAR effect is floored at $0.01 — the spread % is not.

    A percentage floor would be meaningless: 4% of a 5-cent wing premium is a
    fraction of a cent, which rounds away and makes buy and sell print the same
    number. So even the 1% minimum still leaves the two sides one tick apart on
    cheap wings where 1% of the mid is below a penny.
    """
    _open_tab(page, live_server)

    spread = page.locator("#opm-spread")
    expect(spread).to_have_attribute("min", "1")

    def atm_call() -> dict:
        return page.evaluate(
            "() => { const d = window.optionPricingMatrixDebug().data;"
            " const c = d.rows[d.atm_index].cells[d.ref_column_index].call;"
            " return { mid: c.mid, fill: c.fill }; }"
        )

    def wing_call() -> dict:
        # Highest-strike (deep OTM) call — tiny mid, so the $0.01 floor dominates.
        return page.evaluate(
            "() => { const d = window.optionPricingMatrixDebug().data;"
            " const c = d.rows[d.rows.length - 1].cells[d.ref_column_index].call;"
            " return { mid: c.mid, fill: c.fill }; }"
        )

    # Smallest legal input (1%) → at the ATM the 1% > the $0.01 floor, so the
    # fill sits half of 1% (0.5%) off the mid.
    spread.fill("1")
    spread.press("Tab")
    expect(spread).to_have_value("1")
    bought = atm_call()
    assert abs(bought["fill"] - bought["mid"] * 1.005) < 1e-6

    # The dollar floor still keeps a deep wing one tick off mid: 1% of its tiny
    # mid is below a penny, so the floor carries it (buy side).
    wing = wing_call()
    assert abs(wing["fill"] - (wing["mid"] + 0.01)) < 1e-6

    page.locator('[data-opm-side="sell"]').click()
    sold = atm_call()
    assert abs(sold["fill"] - sold["mid"] * 0.995) < 1e-6
    wing_sold = wing_call()
    assert abs(wing_sold["fill"] - (wing_sold["mid"] - 0.01)) < 1e-6

    # Well above the floor the percentage wins: 8% → half of it, 4%, off the mid.
    page.locator('[data-opm-side="buy"]').click()
    spread.fill("8")
    spread.press("Tab")
    wide = atm_call()
    assert abs(wide["fill"] - wide["mid"] * 1.04) < 1e-6

    # Above the 100% ceiling the input clamps and applies in full.
    spread.fill("1500")
    spread.press("Tab")
    expect(spread).to_have_value("100")
    clamped = atm_call()
    assert abs(clamped["fill"] - clamped["mid"] * 1.5) < 1e-6

    assert _app_errors(js_errors) == [], f"JS errors after clamping the spread: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_crosshair_highlights_one_column(page: Page, live_server: str, js_errors: list[str]) -> None:
    """Hovering pins the x axis; it never rewrites the numbers on screen."""
    _open_tab(page, live_server)

    rail = page.locator("#opm-matrix tbody tr").first.locator("td.opm-sigma")
    before = rail.inner_text()

    dtes = _dtes(page)
    page.locator("#opm-matrix tbody tr").nth(3).locator("td.opm-cell[data-col='7']").hover()
    expect(page.locator("#opm-matrix col.opm-col-dte[data-col='7']")).to_have_class(_HOVER_RE)
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='7']")).to_have_class(_HOVER_RE)
    # Values are untouched by hover — only a click promotes a column.
    expect(rail).to_have_text(before)
    expect(page.locator("#opm-head-sigma")).not_to_have_text(f"σ @{dtes[7]}D")

    # Clicking anywhere in a column — data cell or header — promotes it.
    page.locator("#opm-matrix tbody tr").nth(3).locator("td.opm-cell[data-col='7']").click()
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[7]}D")
    expect(rail).not_to_have_text(before)
    # The header (and its <col>) is the state readout now the select is gone.
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='7']")).to_have_class(_REF_RE)
    expect(page.locator("#opm-matrix col.opm-col-dte[data-col='7']")).to_have_class(_REF_RE)
    expect(page.locator("#opm-matrix .is-ref")).to_have_count(2)

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_reference_is_keyboard_reachable(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The reference column still has a keyboard path without the select.

    `#opm-ref-dte` used to be the only Tab-reachable control for the sigma
    reference. Its replacement — the column header — therefore has to be
    focusable, activatable by Enter / Space, and ArrowLeft / ArrowRight have to
    walk the date axis, or the removal would strand keyboard and screen-reader
    users.
    """
    _open_tab(page, live_server)

    dtes = _dtes(page)
    rail = page.locator("#opm-matrix tbody tr").first.locator("td.opm-sigma")
    before = rail.inner_text()

    head = page.locator("#opm-matrix th.opm-head-dte[data-col='2']")
    expect(head).to_have_attribute("tabindex", "0")
    head.focus()
    expect(head).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[2]}D")
    expect(rail).not_to_have_text(before)
    expect(head).to_have_class(_REF_RE)
    expect(head).to_have_attribute("aria-current", "true")

    # Space activates the next header too — and must be swallowed, or it
    # scrolls the grid out from under the user.
    scroll_before = page.evaluate("() => document.getElementById('opm-matrix-body').scrollTop")
    page.locator("#opm-matrix th.opm-head-dte[data-col='3']").focus()
    page.keyboard.press("Space")
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[3]}D")
    assert page.evaluate("() => document.getElementById('opm-matrix-body').scrollTop") == scroll_before

    # ArrowLeft / ArrowRight walk the date axis with roving focus — repeated
    # presses keep stepping without re-tabbing.
    page.keyboard.press("ArrowRight")
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[4]}D")
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='4']")).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#opm-head-sigma")).to_have_text(f"σ @{dtes[3]}D")
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='3']")).to_be_focused()

    # The mark follows the reference instead of accumulating.
    expect(page.locator("#opm-matrix .is-ref")).to_have_count(2)
    assert head.get_attribute("aria-current") is None

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_masks_stay_opaque_under_crosshair(page: Page, live_server: str, js_errors: list[str]) -> None:
    """Sticky header and left rails stay opaque while highlighted.

    They are masking layers: with the matrix scrolled, a translucent fill lets
    the content sliding behind them show through — the "穿模" clip. The crosshair
    and row-hover tints must sit OVER an opaque base, so the resolved
    `background-color` stays fully opaque (alpha 1) even on hover.
    """
    _open_tab(page, live_server)

    def _alpha(rgb: str) -> float:
        # "rgb(r, g, b)" -> 1.0 (opaque); "rgba(r, g, b, a)" -> a
        m = re.match(r"rgba\([^)]*,\s*([\d.]+)\s*\)$", rgb)
        return float(m.group(1)) if m else 1.0

    # Column crosshair → the DTE header gets .is-hover.
    page.locator("#opm-matrix tbody tr").nth(3).locator("td.opm-cell[data-col='7']").hover()
    expect(page.locator("#opm-matrix th.opm-head-dte[data-col='7']")).to_have_class(_HOVER_RE)
    head_bg = page.locator("#opm-matrix th.opm-head-dte[data-col='7']").evaluate(
        "el => getComputedStyle(el).backgroundColor"
    )
    assert _alpha(head_bg) == 1.0, f"header mask not opaque: {head_bg}"

    # The persistent .is-ref mark is one more tint on the same sticky mask, so
    # it has to be opaque too — the select it replaced is gone, and a
    # translucent reference fill would show the rows scrolling behind it.
    page.locator("#opm-matrix th.opm-head-dte[data-col='7']").click()
    ref_bg = page.locator("#opm-matrix th.opm-head-dte[data-col='7']").evaluate(
        "el => getComputedStyle(el).backgroundColor"
    )
    assert _alpha(ref_bg) == 1.0, f"reference header mask not opaque: {ref_bg}"

    # Row hover → the left strike + sigma rails get the rail tint.
    strike = page.locator("#opm-matrix tbody tr").nth(3).locator("th[scope='row']")
    sigma = page.locator("#opm-matrix tbody tr").nth(3).locator("td.opm-sigma")
    strike_bg = strike.evaluate("el => getComputedStyle(el).backgroundColor")
    sigma_bg = sigma.evaluate("el => getComputedStyle(el).backgroundColor")
    assert _alpha(strike_bg) == 1.0, f"strike rail mask not opaque: {strike_bg}"
    assert _alpha(sigma_bg) == 1.0, f"sigma rail mask not opaque: {sigma_bg}"

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_option_pricing_matrix_corner_stays_on_top_while_scrolled(page: Page, live_server: str, js_errors: list[str]) -> None:
    """The top-left corner never lets a scrolled DTE header paint over it.

    The strike + σ header cells are doubly sticky (top + left) and must out-rank
    the DTE header row (z-index 3) and the left rails (z-index 2). A bare
    `.opm-head-strike` selector loses the specificity duel with `.opm-matrix thead
    th`, collapsing the corner to z-index 3 — then, on horizontal scroll, a DTE
    header slides under the corner and (equal z-index, later in DOM) paints on
    top: the "穿模" clip at the top-left. Assert the corner is the topmost layer
    there after both axes are scrolled.
    """
    _open_tab(page, live_server)

    def topmost_at_corner(left: int, top: int) -> str:
        page.evaluate(
            "([l, t]) => { const s = document.getElementById('opm-matrix-body');"
            " s.scrollLeft = l; s.scrollTop = t; }",
            [left, top],
        )
        page.wait_for_timeout(80)
        return page.evaluate(
            """() => {
                const s = document.getElementById('opm-matrix-body');
                const r = s.getBoundingClientRect();
                const el = document.elementFromPoint(r.left + 3, r.top + 3);
                return el ? el.className || el.tagName : 'none';
            }"""
        )

    # Enough top scroll that the caption has cleared and the header is pinned.
    for label, left, top in (("horizontal", 600, 40), ("both", 600, 300), ("vertical", 0, 300)):
        cls = topmost_at_corner(left, top)
        assert "opm-head-strike" in cls or "opm-head-sigma" in cls, (
            f"{label}: top-left corner shows '{cls}' (clip!)"
        )

    assert _app_errors(js_errors) == [], f"JS errors: {js_errors}"

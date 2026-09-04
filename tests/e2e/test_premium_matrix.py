"""End-to-end smoke for the Premium Matrix tab.

The tab is 100% client-side: it drives the pure engine (static/sim/
premium_matrix.js) through the real Flask-served page and never calls any
API. Assertions therefore run against the rendered grid, the KPI strip and
the CSS-driven visibility switches.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

_ACTIVE_RE = re.compile(r"\bactive\b")
# Console errors that are environmental (missing CDN) rather than app bugs.
_RESOURCE_ERR_RE = re.compile(r"Failed to load resource|net::ERR", re.IGNORECASE)

ROWS = 41      # spot 100 ±20%, integer strikes
COLUMNS = 18   # 1–90 DTE in 5-day steps


def _app_errors(js_errors: list[str]) -> list[str]:
    return [e for e in js_errors if not _RESOURCE_ERR_RE.search(e)]


def _open_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('.tab-btn[data-tab="tab-premium-matrix"]').click()
    expect(page.locator("#tab-premium-matrix")).to_have_class(_ACTIVE_RE, timeout=3000)
    expect(page.locator("#pm-matrix")).to_be_visible(timeout=5000)


@pytest.mark.usefixtures("mock_apis")
def test_premium_matrix_renders_default_grid(
    page: Page, live_server: str, js_errors: list[str]
) -> None:
    """Defaults (100 / 25% / 3% / 0% spread) produce a 41 × 18 grid."""
    _open_tab(page, live_server)

    expect(page.locator("#pm-matrix tbody tr")).to_have_count(ROWS)
    expect(page.locator("#pm-matrix tbody tr").first.locator("td.pm-cell")).to_have_count(COLUMNS)
    expect(page.locator("#pm-matrix .pm-half--call")).to_have_count(ROWS * COLUMNS)
    expect(page.locator("#pm-matrix .pm-half--put")).to_have_count(ROWS * COLUMNS)
    # 18 DTE columns + the strike and sigma rails
    expect(page.locator("#pm-matrix thead th")).to_have_count(COLUMNS + 2)

    # Column headers carry the DTE and the 1σ move for that tenor.
    first_col = page.locator("#pm-matrix thead th[data-col='0']")
    expect(first_col).to_contain_text("1D")
    expect(first_col).to_contain_text("1σ")

    # P1 hero + KPI strip are populated.
    expect(page.locator("#pm-hero-value")).to_contain_text("%", timeout=3000)
    expect(page.locator("#pm-kpi-grid")).to_have_text(f"{ROWS} × {COLUMNS}")
    expect(page.locator("#pm-kpi-sigma")).not_to_have_text("—")
    expect(page.locator("#pm-kpi-call")).not_to_have_text("—")
    expect(page.locator("#pm-kpi-put")).not_to_have_text("—")

    # ATM row is marked, and strikes run 80 → 120 in integer steps.
    expect(page.locator("#pm-matrix tr.pm-row-atm")).to_have_count(1)
    expect(page.locator("#pm-matrix tbody tr").first.locator("th[scope='row']")).to_have_text("80")
    expect(page.locator("#pm-matrix tbody tr").last.locator("th[scope='row']")).to_have_text("120")

    assert _app_errors(js_errors) == [], f"JS errors in premium matrix tab: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_premium_matrix_toggles_hide_values(
    page: Page, live_server: str, js_errors: list[str]
) -> None:
    """The four switches are independent and CSS-only."""
    _open_tab(page, live_server)

    cell = page.locator("#pm-matrix tbody tr").first.locator("td.pm-cell").first
    price = cell.locator(".pm-val--price").first
    rate = cell.locator(".pm-val--rate").first
    call_half = cell.locator(".pm-half--call")
    put_half = cell.locator(".pm-half--put")

    expect(price).to_be_visible()
    expect(rate).to_be_visible()

    # Hide prices — rates remain, so no hint is shown.
    page.locator('[data-pm-toggle="price"]').click()
    expect(price).to_be_hidden()
    expect(rate).to_be_visible()
    expect(page.locator("#pm-all-hidden")).to_be_hidden()

    # Hiding rates too leaves nothing to show → guidance appears.
    page.locator('[data-pm-toggle="premium"]').click()
    expect(page.locator("#pm-all-hidden")).to_be_visible()

    # Restore both.
    page.locator('[data-pm-toggle="premium"]').click()
    page.locator('[data-pm-toggle="price"]').click()
    expect(price).to_be_visible()

    # Call / Put are independent.
    page.locator('[data-pm-toggle="call"]').click()
    expect(call_half).to_be_hidden()
    expect(put_half).to_be_visible()
    page.locator('[data-pm-toggle="call"]').click()
    expect(call_half).to_be_visible()

    assert _app_errors(js_errors) == [], f"JS errors while toggling: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_premium_matrix_recomputes_on_input_change(
    page: Page, live_server: str, js_errors: list[str]
) -> None:
    """Changing IV reprices the grid; changing the tenor re-scales the sigma rail."""
    _open_tab(page, live_server)

    call_kpi = page.locator("#pm-kpi-call")
    sigma_kpi = page.locator("#pm-kpi-sigma")
    before_call = call_kpi.inner_text()
    before_sigma = sigma_kpi.inner_text()

    page.fill("#pm-iv", "45")
    expect(call_kpi).not_to_have_text(before_call, timeout=3000)
    expect(sigma_kpi).not_to_have_text(before_sigma, timeout=3000)

    # The sigma rail follows the selected reference column.
    sigma_cell = page.locator("#pm-matrix tbody tr").first.locator("td.pm-sigma")
    before_rail = sigma_cell.inner_text()
    page.select_option("#pm-ref-dte", "0")
    expect(page.locator("#pm-head-sigma")).to_have_text("σ @1D")
    expect(sigma_cell).not_to_have_text(before_rail)

    # A spread moves the buyer's fill above the mid.
    mid_sub = page.locator("#pm-kpi-call-sub")
    expect(mid_sub).to_contain_text("mid")
    page.fill("#pm-spread", "6")
    expect(page.locator("#pm-kpi-call")).not_to_have_text(before_call, timeout=3000)

    assert _app_errors(js_errors) == [], f"JS errors after input change: {js_errors}"

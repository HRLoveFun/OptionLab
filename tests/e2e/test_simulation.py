"""End-to-end smoke for the client-side Simulation tab.

The tab is 100% client-side: it exercises the pure engine (static/sim/*)
through the real Flask-served page and never calls /api/simulate_expiry.
Chart.js is loaded from a CDN; if the e2e runner has no network the chart
canvas is simply not drawn, but the matrix / detail / hero still render and
the app raises no JS error — so the smoke asserts on those DOM signals plus
canvas presence, tolerating CDN resource-load failures.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect


_ACTIVE_RE = re.compile(r"\bactive\b")
# Console errors that are environmental (missing CDN) rather than app bugs.
_RESOURCE_ERR_RE = re.compile(r"Failed to load resource|net::ERR", re.IGNORECASE)


def _app_errors(js_errors: list[str]) -> list[str]:
    return [e for e in js_errors if not _RESOURCE_ERR_RE.search(e)]


@pytest.mark.usefixtures("mock_apis")
def test_simulation_open_input_render(
    page: Page, live_server: str, js_errors: list[str]
) -> None:
    """Open tab → enter spot/strikes/IVs/expiries → Simulate → charts/matrix render."""
    page.goto(live_server, wait_until="domcontentloaded")

    # 1) open the tab
    page.locator('.tab-btn[data-tab="tab-simulation"]').click()
    expect(page.locator("#tab-simulation")).to_have_class(_ACTIVE_RE, timeout=3000)

    # 2) input parameters (spot is required; the rest have defaults)
    page.fill("#sim-spot", "100")
    page.fill("#sim-strikes", "95, 100, 105")
    page.fill("#sim-ivs", "20, 30")
    page.fill("#sim-expiries", "7, 30, 60")

    # 3) run the client-side simulation
    page.locator('[data-action="sim-run"]').click()

    # 4) hero P&L at spot renders
    expect(page.locator("#sim-hero-value")).to_contain_text("$", timeout=3000)

    # matrix: one row per strike, one cell per (dte × iv) combo
    expect(page.locator("#sim-matrix-body tr[data-strike]")).to_have_count(3)
    expect(page.locator("#sim-matrix-body td[data-idx]")).to_have_count(18)  # 3 × (3 dte × 2 iv)

    # detail: one row per combo for the selected strike
    expect(page.locator("#sim-detail-body tbody tr")).to_have_count(6)

    # chart container is present (Chart.js draws only when the CDN is reachable)
    expect(page.locator("#sim-payoff-chart")).to_be_visible()

    assert _app_errors(js_errors) == [], f"JS errors in simulation tab: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_simulation_dual_iv_unlinked(
    page: Page, live_server: str, js_errors: list[str]
) -> None:
    """Unlinking forward vol must not break rendering (Decision B dual-IV path)."""
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('.tab-btn[data-tab="tab-simulation"]').click()

    page.fill("#sim-spot", "100")
    page.fill("#sim-strikes", "100")
    page.fill("#sim-ivs", "30")
    page.fill("#sim-forward-ivs", "45")
    page.uncheck("#sim-link-iv")

    page.locator('[data-action="sim-run"]').click()

    expect(page.locator("#sim-hero-value")).to_contain_text("$", timeout=3000)
    # 4 expiries × 1 entry IV = 4 combos
    expect(page.locator("#sim-detail-body tbody tr")).to_have_count(4)

    assert _app_errors(js_errors) == [], f"JS errors (dual IV): {js_errors}"

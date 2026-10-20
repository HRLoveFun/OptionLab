"""End-to-end smoke for the Position Simulator tab.

The tab posts hypothetical inputs to the REAL /api/optsim — `mock_apis` falls
back to the live server for it, and the engine is pure computation, so no
network is involved. Chart.js and Alpine come from CDNs: without network the
canvases stay blank and the banners stay cloaked, but the hero, KPI strip and
tables are written by static/optsim.js directly, so the smoke asserts on those
and reads the panel phase from `appState`.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

_ACTIVE_RE = re.compile(r"\bactive\b")
# Console errors that are environmental (missing CDN) or the expected 400 of
# the validation test, rather than app bugs.
_RESOURCE_ERR_RE = re.compile(r"Failed to load resource|net::ERR", re.IGNORECASE)


def _app_errors(js_errors: list[str]) -> list[str]:
    return [e for e in js_errors if not _RESOURCE_ERR_RE.search(e)]


def _panel(page: Page) -> dict:
    return page.evaluate("() => window.appState.panels.get('optsim')")


def _open(page: Page, live_server: str, open_tab) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    open_tab("tab-optsim")
    expect(page.locator("#tab-optsim")).to_have_class(_ACTIVE_RE, timeout=3000)
    expect(page.locator("#optsim-hero-value")).to_contain_text("$", timeout=15000)


@pytest.mark.usefixtures("mock_apis")
def test_optsim_tab_runs_the_default_strangle_on_first_visit(
    page: Page, live_server: str, js_errors: list[str], open_tab
) -> None:
    _open(page, live_server, open_tab)

    expect(page.locator("#optsim-hero-label")).to_have_text("Net credit")
    expect(page.locator("#optsim-legs-body tr")).to_have_count(2)
    expect(page.locator("#optsim-resolved tbody tr")).to_have_count(2)
    expect(page.locator("#optsim-kpi-margin-label")).to_have_text("Reg-T margin")
    expect(page.locator("#optsim-kpi-margin-sub")).to_contain_text("naked")
    # One row per date slice at the entry spot, the last one at expiry.
    expect(page.locator("#optsim-profile tbody tr").last).to_contain_text("(expiry)")
    expect(page.locator("#optsim-chart-pnl")).to_be_attached()

    assert _app_errors(js_errors) == [], f"JS errors in optsim tab: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_optsim_switches_margin_in_place_and_reprices_american(
    page: Page, live_server: str, js_errors: list[str], open_tab
) -> None:
    _open(page, live_server, open_tab)
    requests: list[str] = []
    page.on("request", lambda r: requests.append(r.url) if "/api/optsim" in r.url else None)

    page.locator('[data-optsim-margin="pm"]').click()
    expect(page.locator("#optsim-kpi-margin-label")).to_have_text("Portfolio margin")
    expect(page.locator('[data-optsim-margin="pm"]')).to_have_attribute("aria-pressed", "true")
    assert requests == [], "the margin switch must not re-run the simulation"

    page.locator('[data-optsim-style="american"]').click()
    expect(page.locator("#optsim-hero-sub")).to_contain_text("100-step tree", timeout=30000)
    assert len(requests) == 1
    assert _panel(page)["phase"] == "loaded"

    assert _app_errors(js_errors) == [], f"JS errors in optsim tab: {js_errors}"


@pytest.mark.usefixtures("mock_apis")
def test_optsim_surfaces_server_validation_errors(page: Page, live_server: str, open_tab) -> None:
    _open(page, live_server, open_tab)

    page.fill("#optsim-spot", "")
    page.locator('[data-action="optsim-run"]').click()
    page.wait_for_function("() => window.appState.panels.get('optsim').phase === 'error'", timeout=10000)
    assert _panel(page)["message"] == "spot is required"

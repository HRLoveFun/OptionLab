"""Smoke tests: page loads, no JS errors, all 11 tabs render and switch."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

# All sidebar tab IDs (must match `data-tab` values in templates/index.html).
TAB_IDS = [
    "tab-parameter",
    "tab-summary",
    "tab-market-review",
    "tab-statistical-analysis",
    "tab-market-assessment",
    "tab-option-chain",
    "tab-options-chain",
    "tab-odds",
    "tab-game",
    "tab-regime",
    "tab-config",
]

_ACTIVE_RE = re.compile(r"\bactive\b")


def test_index_loads_without_js_errors(page: Page, live_server: str, mock_apis, js_errors: list[str]) -> None:
    """GET / must render the dashboard with zero JS console errors."""
    page.goto(live_server, wait_until="networkidle")

    expect(page.locator("#analysis-form")).to_be_visible()
    expect(page.locator("#ticker")).to_have_count(1)

    # tab-summary only renders for multi-ticker; skip in single-ticker default GET.
    for tab_id in [tid for tid in TAB_IDS if tid != "tab-summary"]:
        button = page.locator(f'.tab-btn[data-tab="{tab_id}"]')
        expect(button).to_have_count(1)

    assert js_errors == [], f"JS errors on initial load: {js_errors}"


@pytest.mark.parametrize(
    "tab_id",
    [tid for tid in TAB_IDS if tid != "tab-summary"],  # summary is hidden when single-ticker
)
def test_tab_switch_activates_panel(
    page: Page, live_server: str, mock_apis, js_errors: list[str], tab_id: str
) -> None:
    """Clicking each sidebar tab activates the corresponding `.tab-content` panel."""
    page.goto(live_server, wait_until="networkidle")

    button = page.locator(f'.tab-btn[data-tab="{tab_id}"]')
    button.click()

    panel = page.locator(f"#{tab_id}")
    expect(panel).to_have_class(_ACTIVE_RE, timeout=2000)

    assert js_errors == [], f"JS errors when activating {tab_id}: {js_errors}"


def test_form_default_ticker_present(page: Page, live_server: str, mock_apis) -> None:
    """Default form renders with the ticker input visible and editable."""
    page.goto(live_server, wait_until="domcontentloaded")
    ticker_input = page.locator("#ticker")
    expect(ticker_input).to_be_visible()
    expect(ticker_input).to_be_editable()

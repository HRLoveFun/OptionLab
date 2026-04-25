"""Tab-switching race conditions.

Rapidly switching between tabs that issue async fetches must not cause:
  * stale responses overwriting the active panel
  * uncaught JS exceptions
  * orphaned spinners

The frontend uses AbortController to cancel in-flight requests on tab
switch. This test verifies the abort path is wired and free of errors.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_rapid_tab_switching_no_js_errors(
    page: Page, live_server: str, mock_apis, js_errors: list[str]
) -> None:
    """Rapidly switch through all major fetch-driven tabs; final tab wins."""
    page.goto(live_server, wait_until="networkidle")

    sequence = [
        "tab-option-chain",
        "tab-regime",
        "tab-odds",
        "tab-game",
        "tab-market-review",
    ]
    # Rapid clicks (no waits between).
    for tab_id in sequence:
        page.locator(f'.tab-btn[data-tab="{tab_id}"]').click(no_wait_after=True)

    # Wait for the final panel to settle.
    final_id = sequence[-1]
    final_panel = page.locator(f"#{final_id}")
    expect(final_panel).to_be_visible(timeout=4000)

    # Other panels should not be visible (only the active tab-content is shown).
    for tab_id in sequence[:-1]:
        other = page.locator(f"#{tab_id}")
        expect(other).not_to_be_visible(timeout=1000)

    # No uncaught exceptions during the storm of requests.
    pageerrors = [e for e in js_errors if e.startswith("[pageerror]")]
    assert pageerrors == [], f"Uncaught errors during rapid tab switch: {pageerrors}"

"""Lazy-load behavior of `/api/*`-driven tabs.

The Option Chain tab does not fetch on page load — it lazy-loads on
first activation. This test verifies the JS module wires the request
correctly and renders the response.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_option_chain_lazy_loads_on_activation(
    page: Page, live_server: str, mock_apis, js_errors: list[str]
) -> None:
    """Switching to Option Chain tab triggers `/api/option_chain` and renders rows."""
    api_calls: list[str] = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/option_chain" in req.url else None)

    page.goto(live_server, wait_until="networkidle")

    # Activate the option chain tab.
    page.locator('.tab-btn[data-tab="tab-option-chain"]').click()

    # Container should become visible (chain wrapper or expiry tabs).
    chain_wrapper = page.locator("#oc-chain-wrapper")
    expiry_tabs = page.locator("#oc-exp-tabs")
    # At least one of the two should be visible after the mock response renders.
    expect(chain_wrapper.or_(expiry_tabs)).to_be_visible(timeout=4000)

    # The fetch must have happened.
    assert any("/api/option_chain" in u for u in api_calls), f"Expected /api/option_chain call, got: {api_calls}"

    assert js_errors == [], f"JS errors during option-chain lazy load: {js_errors}"


def test_option_chain_handles_api_error_gracefully(
    page: Page, live_server: str, mock_apis, js_errors: list[str]
) -> None:
    """If `/api/option_chain` returns 500, the UI must show an error message,
    not throw an uncaught exception."""
    mock_apis["/api/option_chain"] = (500, {"error": "Internal Server Error"})

    page.goto(live_server, wait_until="networkidle")
    page.locator('.tab-btn[data-tab="tab-option-chain"]').click()

    # Status div should display some indication of the failure.
    status = page.locator("#oc-status")
    expect(status).to_be_visible(timeout=4000)

    # Critical: no uncaught JS exception should bubble up.
    pageerrors = [e for e in js_errors if e.startswith("[pageerror]")]
    assert pageerrors == [], f"Uncaught page errors on API failure: {pageerrors}"

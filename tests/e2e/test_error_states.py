"""Error-state rendering — option-chain banner shows on backend failure."""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_option_chain_500_renders_error_banner(
    page: Page,
    live_server: str,
    mock_apis,
    js_errors: list[str],
) -> None:
    # Force the option-chain endpoint to fail.
    mock_apis["/api/option_chain"] = (500, {"error": "Synthetic backend failure"})

    page.goto(live_server, wait_until="domcontentloaded")

    # Activate parameter tab so #ticker becomes interactive.
    page.click('.tab-btn[data-tab="tab-parameter"]')

    # Provide a ticker so loadOptionChain has something to query.
    page.fill("#ticker", "TEST_AAPL")
    page.locator("#ticker").blur()

    # Activate the Option Chain tab.
    page.click('.tab-btn[data-tab="tab-option-chain"]')
    expect(page.locator("#tab-option-chain")).to_have_class(
        __import__("re").compile(r"\bactive\b"), timeout=2_000
    )

    # Click the reload button to trigger the request.
    page.click('[data-action="oc-reload"]')

    # The error banner should appear with role=alert.
    err_banner = page.locator(
        "#tab-option-chain .panel-banner--error[role='alert']"
    )
    expect(err_banner).to_be_visible(timeout=5_000)
    # Ensure the error message text propagated from the response body or a
    # generic fallback — both are acceptable, but *something* must render.
    expect(err_banner).not_to_have_text("", timeout=2_000)

    # An expected error path should not produce uncaught JS exceptions.
    fatal = [e for e in js_errors if "[pageerror]" in e]
    assert fatal == [], f"Uncaught JS errors during error-state: {fatal}"

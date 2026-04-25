"""Position cascade dropdown — ticker → expiry → strike chain.

Exercises the real `/api/preload_option_chain` route plus the JS
`onPositionTickerChange` / `onPositionExpiryChange` handlers. The
yfinance layer used inside `OptionsChainAnalyzer` is patched at the
backend process level via `yf_stub`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_position_cascade_populates_dropdowns(
    page: Page,
    live_server: str,
    yf_stub: None,
    js_errors: list[str],
) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.click('.tab-btn[data-tab="tab-parameter"]')

    # Provide a ticker so `getValidTickers()` picks it up.
    page.fill("#ticker", "TEST_AAPL")
    # Trigger blur so the validator publishes the ticker into appState.
    page.locator("#ticker").blur()

    # Add a positions row.
    page.click("button:has-text('Add Position')")
    row = page.locator("#positions-tbody tr").last
    expect(row).to_be_visible()

    ticker_select = row.locator("[name=pos_ticker]")
    expiry_select = row.locator("[name=pos_expiry]")
    strike_select = row.locator("[name=pos_strike]")

    # Pick the ticker we entered. select_option triggers `change`, which
    # fires the cascade and posts to /api/preload_option_chain.
    ticker_select.select_option("TEST_AAPL")

    # Expiry dropdown should populate from the cache.
    expect(expiry_select.locator("option")).not_to_have_count(1, timeout=10_000)

    first_expiry = expiry_select.locator("option").nth(1).get_attribute("value")
    assert first_expiry, "no expiry produced by cascade"
    expiry_select.select_option(first_expiry)

    # Strike dropdown should populate after selecting an expiry.
    expect(strike_select.locator("option")).not_to_have_count(1, timeout=5_000)

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors during cascade: {fatal}"

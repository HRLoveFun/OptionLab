"""End-to-end form submission flow.

Exercises the *real* Flask backend: form POST → DataService pipeline →
template render → table visible. The yfinance layer is patched at the
backend process level via the `yf_stub` fixture; the synthetic ticker
``TEST_AAPL`` routes through the existing fixture branch in
`data_pipeline.ingest.ohlcv`.
"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_form_submit_renders_summary(
    page: Page,
    live_server: str,
    yf_stub: None,
    seed_test_data: None,
    js_errors: list[str],
) -> None:
    """Submit the analysis form with a TEST_ ticker and assert the page
    re-renders with the ticker echoed back.

    Batch B7: the bar posts `ticker` only — the horizon is owned by the market
    modules' toolbars and mirrored into the bar's hidden inputs by
    `state/marketParamsState.js`, so the test no longer types a start month.
    """
    page.goto(live_server, wait_until="domcontentloaded")
    # The Parameters bar is always visible (batch B6).
    page.fill("#ticker", "TEST_AAPL")

    # The marketParams store must have mirrored its horizon before submit,
    # otherwise POST / fails its start_time validation.
    expect(page.locator("#start_time")).not_to_have_value("", timeout=5_000)

    # POST the form and wait for navigation to complete.
    with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
        page.click("#analysis-form button[type=submit]")

    # The submitted ticker round-trips through the form so the input value
    # must reflect what we submitted.
    expect(page.locator("#ticker")).to_have_value("TEST_AAPL", timeout=5_000)

    # No fatal JS errors on a real backend round-trip.
    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors after submit: {fatal}"

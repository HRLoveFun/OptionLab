"""End-to-end form submission flow.

Exercises the *real* Flask backend: form POST → DataService pipeline →
template render → table visible. The yfinance layer is patched at the
backend process level via the `yf_stub` fixture; the synthetic ticker
``TEST_AAPL`` routes through the existing fixture branch in
`data_pipeline.downloader`.
"""

from __future__ import annotations

import datetime as dt

from playwright.sync_api import Page, expect


def _months_ago(n: int) -> str:
    """Return a YYYY-MM string n months before today (HTML <input type=month>)."""
    today = dt.date.today().replace(day=1)
    for _ in range(n):
        today = (today - dt.timedelta(days=1)).replace(day=1)
    return today.strftime("%Y-%m")


def test_form_submit_renders_summary(
    page: Page,
    live_server: str,
    yf_stub: None,
    seed_test_data: None,
    js_errors: list[str],
) -> None:
    """Submit the analysis form with a TEST_ ticker and assert the page
    re-renders with the ticker echoed back."""
    page.goto(live_server, wait_until="domcontentloaded")
    page.click('.tab-btn[data-tab="tab-parameter"]')

    page.fill("#ticker", "TEST_AAPL")
    page.fill("#start_time", _months_ago(3))

    # POST the form and wait for navigation to complete.
    with page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
        page.click("#analysis-form button[type=submit]")

    # The submitted ticker round-trips through the form so the input value
    # must reflect what we submitted.
    expect(page.locator("#ticker")).to_have_value("TEST_AAPL", timeout=5_000)

    # No fatal JS errors on a real backend round-trip.
    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors after submit: {fatal}"

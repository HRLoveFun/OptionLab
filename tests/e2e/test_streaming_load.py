"""Streaming/initial load performance — DOMContentLoaded timing budgets.

These assertions are deliberately loose so they don't flake on slower CI
boxes. Tighten once a baseline is established.
"""

from __future__ import annotations

import time

from playwright.sync_api import Page, expect


def test_dom_content_loaded_under_2s(
    page: Page,
    live_server: str,
    mock_apis,
    js_errors: list[str],
) -> None:
    """The shell HTML + critical JS should reach DOMContentLoaded quickly.

    Run a warm-up navigation first so we don't measure cold-start cost
    (matplotlib import, DataService init, etc.) which is unrelated to
    the streaming budget we actually care about.
    """
    # Warm-up — pay the cold-start cost once.
    page.goto(live_server, wait_until="domcontentloaded")

    t0 = time.monotonic()
    page.goto(live_server, wait_until="domcontentloaded")
    elapsed = time.monotonic() - t0

    # Form must be in the DOM by DOMContentLoaded (visibility depends on
    # which tab is active server-side, so don't assert on display).
    expect(page.locator("#analysis-form")).to_have_count(1)
    expect(page.locator("#ticker")).to_have_count(1)

    assert elapsed < 2.0, f"DOMContentLoaded took {elapsed:.2f}s (budget 2s)"

    fatal = [e for e in js_errors if "[pageerror]" in e]
    assert fatal == [], f"JS errors during initial load: {fatal}"


def test_first_ticker_validation_under_5s(
    page: Page,
    live_server: str,
    mock_apis,
    js_errors: list[str],
) -> None:
    """End-to-end: load page → enter a ticker → validation roundtrip < 5s.

    With `mock_apis` the validation endpoint resolves immediately, so this
    primarily measures DOM hydration + Alpine init + event-handler latency.
    """
    page.goto(live_server, wait_until="domcontentloaded")
    page.click('.tab-btn[data-tab="tab-parameter"]')

    t0 = time.monotonic()
    page.fill("#ticker", "TEST_AAPL")
    page.locator("#ticker").blur()

    # Wait for the validation badge container to receive any content,
    # which indicates the validator pipeline ran end-to-end. Note the JS
    # validator has an internal 500ms debounce, so use a generous timeout.
    page.wait_for_function(
        """() => {
            const c = document.getElementById('ticker-badges')
                  || document.getElementById('ticker-validation');
            return c && c.innerHTML.trim().length > 0;
        }""",
        timeout=5_000,
    )
    elapsed = time.monotonic() - t0

    assert elapsed < 5.0, f"first-ticker pipeline took {elapsed:.2f}s (budget 5s)"

    fatal = [e for e in js_errors if "[pageerror]" in e]
    assert fatal == [], f"JS errors during ticker validation: {fatal}"

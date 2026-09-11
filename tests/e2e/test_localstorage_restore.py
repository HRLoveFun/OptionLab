"""LocalStorage restoration of the module parameter groups (batch B7).

One key per group — `marketParams`, `assessmentParams`, `optionFilter` — plus the
bar's own `marketAnalysisForm` convenience copy for the ticker.
"""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect


def test_localstorage_restores_module_params(
    page: Page,
    live_server: str,
    mock_apis,
    js_errors: list[str],
) -> None:
    page.goto(live_server, wait_until="domcontentloaded")

    # Seed localStorage *before* DOMContentLoaded handlers re-fire on reload.
    saved_form = {"ticker": "TEST_AAPL", "positions": []}
    page.evaluate(
        """({form}) => {
            localStorage.setItem('marketAnalysisForm', JSON.stringify(form));
            localStorage.setItem('marketParams', JSON.stringify(
                { from: '2024-01', to: '2024-03', frequency: 'W' }));
            localStorage.setItem('assessmentParams', JSON.stringify(
                { side_bias: 'Neutral', risk_threshold: '75', rolling_window: '90',
                  account_size: '100000', max_risk_pct: '2' }));
            localStorage.setItem('optionFilter', JSON.stringify(
                { max_dte: '30', moneyness_low: '0.80', moneyness_high: '1.20',
                  max_contracts: '500', refresh_interval: '120' }));
        }""",
        {"form": saved_form},
    )

    page.reload(wait_until="domcontentloaded")

    # The bar's ticker survives, and the marketParams store mirrors the horizon
    # into the bar's submit-only hidden inputs.
    expect(page.locator("#ticker")).to_have_value("TEST_AAPL", timeout=5_000)
    expect(page.locator("#start_time")).to_have_value("2024-01")
    expect(page.locator("#end_time")).to_have_value("2024-03")

    # The Option Chain toolbar is the only module toolbar present before a run.
    expect(page.locator("#oc-max-dte")).to_have_value("30")
    expect(page.locator("#oc-moneyness-low")).to_have_value("0.80")
    expect(page.locator("#oc-moneyness-high")).to_have_value("1.20")
    expect(page.locator("#oc-refresh-interval")).to_have_value("120")

    # The stores expose the restored values (the market toolbars render only in
    # streaming mode, i.e. after a run).
    assert page.evaluate("() => appState.marketParams.get().from") == "2024-01"
    assert page.evaluate("() => appState.marketParams.get().frequency") == "W"
    assert page.evaluate("() => appState.assessmentParams.get().side_bias") == "Neutral"
    assert page.evaluate("() => appState.optionFilter.get().moneyness_high") == "1.20"

    # Storage round-trip is intact (no accidental mutation of the group keys).
    assert json.loads(page.evaluate("() => localStorage.getItem('marketParams')"))["from"] == "2024-01"

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors during reload restore: {fatal}"

"""LocalStorage form-state restoration after page reload."""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect


def test_localstorage_restores_form_state(
    page: Page,
    live_server: str,
    mock_apis,
    js_errors: list[str],
) -> None:
    page.goto(live_server, wait_until="domcontentloaded")

    # Seed localStorage *before* DOMContentLoaded handlers re-fire on reload.
    saved_form = {
        "ticker": "TEST_AAPL",
        "start_time": "202401",
        "end_time": "202403",
        "positions": [],
    }
    saved_cfg = {
        "frequency": "W",
        "side_bias": "Neutral",
        "risk_threshold": "75",
        "rolling_window": "90",
        "max_dte": "30",
        "moneyness_low": "0.80",
        "moneyness_high": "1.20",
        "max_contracts": "500",
        "refresh_interval": "120",
    }
    page.evaluate(
        """({form, cfg}) => {
            localStorage.setItem('marketAnalysisForm', JSON.stringify(form));
            localStorage.setItem('marketAnalysisConfig', JSON.stringify(cfg));
        }""",
        {"form": saved_form, "cfg": saved_cfg},
    )

    page.reload(wait_until="domcontentloaded")

    # Form fields should be hydrated from `marketAnalysisForm`.
    expect(page.locator("#ticker")).to_have_value("TEST_AAPL", timeout=5_000)
    expect(page.locator("#start_time")).to_have_value("2024-01")
    expect(page.locator("#end_time")).to_have_value("2024-03")

    # Hidden fields should be synced from `marketAnalysisConfig`.
    freq = page.locator("#frequency").input_value()
    side = page.locator("#side_bias").input_value()
    risk = page.locator("#risk_threshold").input_value()
    rw = page.locator("#rolling_window").input_value()
    assert freq == "W"
    assert side == "Neutral"
    assert risk == "75"
    assert rw == "90"

    # Storage round-trip is intact (no accidental mutation).
    raw_form = page.evaluate("() => localStorage.getItem('marketAnalysisForm')")
    assert json.loads(raw_form)["ticker"] == "TEST_AAPL"

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors during reload restore: {fatal}"

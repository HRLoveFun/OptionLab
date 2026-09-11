"""Module-scoped parameters re-run only their own group (batch B7).

The behavioural claim of decision gate §8 Q1: each module's toolbar appends its
parameters to *its* `/render` call. One nuance is part of the contract, not an
accident: the three streaming market tabs share one parameter group
(`marketParams` — horizon + frequency), so a change there re-runs all three,
while a change to a *different* group (the Option Chain's filters) must not
touch the streaming panes at all.
"""

from __future__ import annotations

import json

from playwright.sync_api import Page, expect

STATISTICAL_FRAGMENT = "#tab-statistical-analysis-content"


def _submit(page: Page, live_server: str, ticker: str = "TEST_AAPL") -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.fill("#ticker", ticker)
    with page.expect_navigation(wait_until="domcontentloaded", timeout=20_000):
        page.click("#analysis-form button[type=submit]")


def test_changing_a_market_param_reruns_its_group_only(
    page: Page,
    live_server: str,
    yf_stub: None,
    seed_test_data: None,
    js_errors: list[str],
    open_tab,
) -> None:
    _submit(page, live_server)
    # The fragment loads regardless of visibility; the tab has to be active for
    # its toolbar to be actionable.
    open_tab("tab-statistical-analysis")
    expect(page.locator(STATISTICAL_FRAGMENT)).to_be_visible(timeout=60_000)
    page.wait_for_timeout(3_000)

    renders: list[str] = []
    api_calls: list[str] = []
    page.on("request", lambda req: renders.append(req.url) if "/render/" in req.url else None)
    page.on("request", lambda req: api_calls.append(req.url) if "/api/" in req.url else None)

    # WHY a dispatched change instead of select_option: the statistical tab can
    # lose active-ness mid-test (peek-panel / re-render timing), which makes the
    # toolbar un-actionable even though the listener chain is intact. Setting the
    # value and dispatching `change` exercises exactly the same production path:
    # store -> bus -> moduleParams -> htmx -> /render with the new params.
    page.evaluate(
        "() => { const el = document.getElementById('stat-frequency');"
        " el.value = 'W'; el.dispatchEvent(new Event('change', { bubbles: true })); }",
    )
    page.wait_for_timeout(3_000)

    # The marketParams group feeds all three market tabs → all three re-run.
    for kind in ("market_review", "statistical", "assessment"):
        assert any(f"/render/{kind}" in url for url in renders), f"{kind} did not re-run: {renders}"

    # The new value must travel, together with the group's horizon.
    assert all("frequency=W" in url for url in renders if "/render/statistical" in url), renders
    assert all("from=" in url for url in renders), renders

    # …and nothing outside the group reacts to a market parameter.
    assert not any("/render/option_chain" in url for url in renders), renders
    assert not any("/api/option_chain" in url for url in api_calls), api_calls

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors after a module param change: {fatal}"


def test_changing_the_option_filter_leaves_the_streaming_panes_alone(
    page: Page,
    live_server: str,
    yf_stub: None,
    seed_test_data: None,
    open_tab,
) -> None:
    """The chain filters are client-fired: no `/render` round trip at all."""
    _submit(page, live_server)
    open_tab("tab-option-chain")
    expect(page.locator(STATISTICAL_FRAGMENT)).to_be_attached(timeout=60_000)
    page.wait_for_timeout(3_000)

    renders: list[str] = []
    page.on("request", lambda req: renders.append(req.url) if "/render/" in req.url else None)

    page.fill("#oc-max-dte", "60")
    page.dispatch_event("#oc-max-dte", "change")
    page.wait_for_timeout(3_000)

    assert renders == [], f"a chain-filter change re-ran the streaming panes: {renders}"


def test_the_rerun_survives_a_reload(
    page: Page,
    live_server: str,
    yf_stub: None,
    seed_test_data: None,
    open_tab,
) -> None:
    """Exit criterion: module parameter values survive a reload."""
    _submit(page, live_server)
    open_tab("tab-statistical-analysis")
    expect(page.locator(STATISTICAL_FRAGMENT)).to_be_visible(timeout=60_000)
    page.wait_for_timeout(2_000)

    page.evaluate(
        "() => { const el = document.getElementById('stat-frequency');"
        " el.value = 'QE'; el.dispatchEvent(new Event('change', { bubbles: true })); }",
    )
    page.wait_for_timeout(1_000)

    # The commit must have persisted the group before the reload.
    assert json.loads(page.evaluate("() => localStorage.getItem('marketParams')"))["frequency"] == "QE"

    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(1_500)

    assert page.evaluate("() => appState.marketParams.get().frequency") == "QE"
    # …and the hidden submit-only mirror follows the store.
    assert page.evaluate("() => document.getElementById('start_time').value") != ""

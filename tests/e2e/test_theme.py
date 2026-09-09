"""Theme toggle e2e: header button visible on desktop + mobile, switches
between Light/Dark and persists the choice across reloads."""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_theme_defaults_to_dark_and_toggles_to_light(
    page: Page, live_server: str, mock_apis, js_errors: list[str]
) -> None:
    """Dark is the default theme; one click switches to Light and persists."""
    page.goto(live_server, wait_until="domcontentloaded")

    btn = page.locator("#theme-toggle")
    expect(btn).to_be_visible()

    html = page.locator("html")
    expect(html).to_have_attribute("data-theme", "dark")
    # Dark is the default, not a stored choice: first load must persist
    # nothing so a future "honor prefers-color-scheme" default stays open.
    assert page.evaluate("() => localStorage.getItem('theme')") is None

    btn.click()
    expect(html).to_have_attribute("data-theme", "light")
    assert page.evaluate("() => localStorage.getItem('theme')") == "light"

    # Choice survives a reload (the pre-init script applies it pre-CSS).
    page.reload(wait_until="domcontentloaded")
    expect(html).to_have_attribute("data-theme", "light")

    # And back to dark — now an explicit choice, so it does persist.
    page.locator("#theme-toggle").click()
    expect(html).to_have_attribute("data-theme", "dark")
    assert page.evaluate("() => localStorage.getItem('theme')") == "dark"

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors during theme toggle: {fatal}"


def test_theme_toggle_repaints_theme_dependent_tab_content(
    page: Page, live_server: str, mock_apis, js_errors: list[str], open_tab
) -> None:
    """A runtime toggle re-resolves --regime-* tokens: regime.js caches them
    from getComputedStyle, so it must repaint from the last payload on the
    'theme:changed' bus event rather than stay frozen on the old theme."""
    page.goto(live_server, wait_until="networkidle")
    open_tab("tab-regime")

    hero = page.locator("#regime-current-body .regime-hero:not(.regime-hero--placeholder)")
    expect(hero).to_be_visible()

    # Stamp the rendered hero; a repaint replaces #regime-current-body's
    # innerHTML, so the stamped node is gone once regime.js reacts.
    page.evaluate("() => document.querySelector('#regime-current-body .regime-hero').setAttribute('data-stale', '1')")
    page.locator("#theme-toggle").click()
    page.wait_for_function(
        "() => { const el = document.querySelector('#regime-current-body .regime-hero');"
        " return el && !el.hasAttribute('data-stale'); }"
    )

    fatal = [e for e in js_errors if "favicon" not in e.lower()]
    assert fatal == [], f"JS errors during regime repaint: {fatal}"


def test_theme_button_visible_on_mobile_viewport(page: Page, live_server: str, mock_apis) -> None:
    """The toggle stays visible in the top-right on a phone-sized viewport."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server, wait_until="domcontentloaded")

    btn = page.locator("#theme-toggle")
    expect(btn).to_be_visible()

    box = btn.bounding_box()
    assert box is not None, "theme toggle has no layout box on mobile"
    viewport_w = 390
    # Right edge must sit inside the viewport (top-right placement) and the
    # button must be large enough to tap comfortably.
    assert box["x"] + box["width"] <= viewport_w + 1
    assert box["x"] >= viewport_w * 0.5, "theme toggle should sit in the right half of the header"
    assert box["width"] >= 24 and box["height"] >= 24

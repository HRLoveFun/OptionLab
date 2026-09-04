"""TEMP diagnostic — detect the premium-matrix top-left corner clip on scroll.

Run with PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH pointed at a system Chrome:
  PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  python -m pytest tests/e2e/test_debug_pm_clip.py -s
"""
from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

_ACTIVE_RE = re.compile(r"\bactive\b")


def _open_tab(page: Page, live_server: str) -> None:
    page.goto(live_server, wait_until="domcontentloaded")
    page.locator('.tab-btn[data-tab="tab-premium-matrix"]').click()
    expect(page.locator("#tab-premium-matrix")).to_have_class(_ACTIVE_RE, timeout=3000)
    expect(page.locator("#pm-matrix")).to_be_visible(timeout=5000)


@pytest.mark.usefixtures("mock_apis")
def test_debug_pm_clip(page: Page, live_server: str, js_errors: list[str]) -> None:
    _open_tab(page, live_server)
    box = page.locator("#pm-matrix-body")
    box.scroll_into_view_if_needed()

    def probe(label: str, left: int, top: int):
        page.evaluate(
            "([l, t]) => { const s = document.getElementById('pm-matrix-body');"
            " s.scrollLeft = l; s.scrollTop = t; }",
            [left, top],
        )
        page.wait_for_timeout(150)
        info = page.evaluate(
            """() => {
                const s = document.getElementById('pm-matrix-body');
                const r = s.getBoundingClientRect();
                const x = r.left + 3, y = r.top + 3;
                const el = document.elementFromPoint(x, y);
                const cl = el ? (el.className || el.tagName) : 'none';
                const desc = el ? (el.tagName + '.' + (typeof el.className === 'string' ? el.className : '')) : 'none';
                return { x, y, tag: el ? el.tagName : 'none', cls: cl, desc,
                         scrollLeft: s.scrollLeft, scrollTop: s.scrollTop };
            }"""
        )
        print(f"[{label}] {info}")
        path = f"/tmp/pm_clip_{label}.png"
        box.screenshot(path=path)
        print(f"[{label}] screenshot -> {path}")
        return info

    # scrollTop > 0 so the caption clears and the sticky header is pinned at the
    # top of the scroll viewport (otherwise the probe point hits the caption).
    h = probe("horizontal_only", 600, 40)
    v = probe("both", 600, 300)
    v0 = probe("vertical_only", 0, 300)

    # Dump computed styles of the competing layers.
    dump = page.evaluate(
        """() => {
            const pick = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return { sel, missing: true };
                const cs = getComputedStyle(el);
                const r = el.getBoundingClientRect();
                return { sel, position: cs.position, left: cs.left, top: cs.top,
                         zIndex: cs.zIndex, x: Math.round(r.x), y: Math.round(r.y) };
            };
            return {
                corner_strike: pick('#pm-matrix thead th.pm-head-strike'),
                corner_sigma: pick('#pm-matrix thead th.pm-head-sigma'),
                dte0: pick('#pm-matrix thead th.pm-head-dte[data-col="0"]'),
                dte3: pick('#pm-matrix thead th.pm-head-dte[data-col="3"]'),
                rail_strike: pick('#pm-matrix tbody th[scope="row"]'),
                rail_sigma: pick('#pm-matrix tbody td.pm-sigma'),
            };
        }"""
    )
    import json
    print("COMPUTED:", json.dumps(dump, indent=2))

    # The top-left corner must be a header cell (.pm-head-strike / .pm-head-sigma),
    # NOT a data cell (.pm-cell) and NOT a scrolled DTE header (.pm-head-dte).
    for name, info in (("horizontal_only", h), ("both", v), ("vertical_only", v0)):
        cls = info["cls"]
        assert "pm-head-strike" in cls or "pm-head-sigma" in cls, (
            f"{name}: top-left corner shows '{cls}' (clip!)"
        )

    print("JS errors:", js_errors)

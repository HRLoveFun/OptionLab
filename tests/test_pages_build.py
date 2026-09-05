"""Assemble-only Pages build test (CI-safe: needs jinja2, no DB/network).

Renders into a temp dir from the COMMITTED snapshot so the test never
touches the real site/ tree, then asserts the identical-UI invariants:
all tab bodies present, no backend URLs that break the /OptionLab/ subpath,
shim + banner injected, legacy redirects emitted.
"""

import json
from pathlib import Path

from scripts.build_pages_site import REDIRECTS, assemble

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_assemble_matches_flask_partials(tmp_path):
    out = assemble(tmp_path / "site")
    html = (out).read_text(encoding="utf-8")

    # every tab body from templates/index.html must survive the static render
    for tab_id in (
        "tab-parameter",
        "tab-market-review",
        "tab-statistical-analysis",
        "tab-market-assessment",
        "tab-option-chain",
        "tab-options-chain",
        "tab-odds",
        "tab-regime",
        "tab-simulation",
        "tab-option-pricing-matrix",
        "tab-config",
    ):
        assert f'id="{tab_id}"' in html, tab_id

    # no streaming placeholders / absolute backend paths in static output
    assert 'hx-get="/render/' not in html
    assert '"/static/' not in html and "'/static/" not in html
    assert "hx-get" not in html

    # Pages delta: shim + demo banner + prefilled demo ticker
    assert "./pages-shim.js" in html
    assert "pages-demo-banner" in html
    assert 'id="ticker" name="ticker" value="NVDA"' in html

    # snapshot content baked in (real analysis artefacts, not empty states)
    assert "data:image/png;base64," in html
    assert "tab-market-review-content" in html

    # static/ copied verbatim (identical CSS/JS)
    for rel in (
        "static/styles.css",
        "static/main.js",
        "static/option-chain.js",
        "static/sim/grid.js",
        "static/state/store.js",
    ):
        src = (REPO_ROOT / rel).read_bytes()
        assert (tmp_path / "site" / rel).read_bytes() == src, rel

    # legacy demo URLs redirect into the identical app tabs
    for rel in REDIRECTS:
        assert (tmp_path / "site" / rel).exists(), rel


def test_snapshot_schema():
    snap = json.loads((REPO_ROOT / "site" / "snapshot" / "snapshot.json").read_text(encoding="utf-8"))
    assert snap["meta"]["ticker"] == "NVDA"
    for kind in ("market_review", "statistical", "assessment", "options_chain"):
        assert kind in snap["slices"], kind
    assert "market_review_table" in snap["slices"]["market_review"]

    for name in (
        "market_review_ts.nvda.json",
        "validate_tickers.json",
        "regime_current.json",
        "regime_history.json",
        "expiry_calendar.json",
        "odds_with_vol.nvda.json",
    ):
        p = REPO_ROOT / "site" / "fixtures" / name
        body = json.loads(p.read_text(encoding="utf-8"))
        assert body.get("status") == "ok", name
    # option_chain mirrors the live route shape ({expirations, chain, spot})
    chain = json.loads((REPO_ROOT / "site" / "fixtures" / "option_chain.nvda.json").read_text(encoding="utf-8"))
    assert chain["expirations"] and chain["chain"] and chain["spot"]

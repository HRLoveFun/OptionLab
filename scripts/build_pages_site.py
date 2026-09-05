"""Build the GitHub Pages site as an identical-UI static mirror of the Flask app.

Strategy (single-source UI — users learn ONE interface):
  * Render the REAL templates/index.html with streaming_mode=False and a
    committed data snapshot, so every tab uses the REAL partials, REAL
    static/*.js and REAL static/styles.css.
  * Backend calls from JS are answered on Pages by site/pages-shim.js
    (fetch-level stub serving site/fixtures/*.json). static/* is UNTOUCHED.
  * Modules that need live compute (analysis run, portfolio) show the same
    code paths as an offline Flask app + a demo banner explains the snapshot.

Two modes:
  * default (CI: needs only jinja2): load site/snapshot/snapshot.json +
    render + copy static/ + write legacy redirects. Deterministic, offline.
  * --refresh-snapshot (local dev, full deps + market_data.sqlite + network
    for the option chain): recompute slices/fixtures and rewrite
    site/snapshot/snapshot.json + API fixtures. Commit the result.

Usage:
  python scripts/build_pages_site.py [--out site] [--ticker NVDA]
  python scripts/build_pages_site.py --refresh-snapshot [--ticker NVDA]
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"
SITE_DIR = REPO_ROOT / "site"
SNAPSHOT_PATH = SITE_DIR / "snapshot" / "snapshot.json"
FIXTURES_DIR = SITE_DIR / "fixtures"

DEMO_TICKER = "NVDA"

# Legacy hand-built demo pages (pre-convergence) → identical app tab.
# Showcase slugs map to the same tabs; summary has no single-ticker home.
REDIRECTS = {
    "sim/index.html": ("tab-simulation", "Simulation"),
    "option-pricing-matrix/index.html": ("tab-option-pricing-matrix", "Option Pricing Matrix"),
    "option-chain/index.html": ("tab-option-chain", "Option Chain"),
    "odds/index.html": ("tab-odds", "Expiry Odds"),
    "market-review/index.html": ("tab-market-review", "Market Review"),
    "showcase/statistical.html": ("tab-statistical-analysis", "Statistical Analysis"),
    "showcase/assessment.html": ("tab-market-assessment", "Assessment & Projections"),
    "showcase/volatility.html": ("tab-options-chain", "Volatility Analysis"),
    "showcase/regime.html": ("tab-regime", "Market Regime"),
    "showcase/parameter.html": ("tab-parameter", "Parameters"),
    "showcase/summary.html": ("", "Summary"),
}

BANNER_HTML = """    <!-- PAGES DEMO BANNER (build-injected; not part of the Flask app) -->
    <div id="pages-demo-banner" role="status" aria-live="polite"
         style="padding:8px 16px; background:#eff6ff; color:#1e40af;
                border-bottom:1px solid #bfdbff; font-size:13px; text-align:center;">
        静态演示快照 <strong id="pages-demo-ticker">{ticker}</strong>（数据截至 {data_through}）——
        界面与交互同本地版一致；实时行情与分析运行需本地 <code>python app.py</code>。
        <a href="#tab-parameter" style="color:#1e40af; text-decoration:underline; margin-left:8px;">去 Parameter 页</a>
    </div>
"""


# --------------------------------------------------------------------------
# snapshot refresh (local, full deps)
# --------------------------------------------------------------------------

def _assert_jsonable(obj, path="root"):
    """Snapshot must survive a JSON round-trip (no DataFrames, datetimes…)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_jsonable(v, f"{path}.{k}")
        return
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _assert_jsonable(v, f"{path}[{i}]")
        return
    raise TypeError(f"snapshot value at {path} is not JSON-serializable: {type(obj)}")


def _demo_form_data(ticker: str) -> dict:
    from utils.constants import (
        DEFAULT_FREQUENCY,
        DEFAULT_RISK_THRESHOLD,
        DEFAULT_ROLLING_WINDOW,
        DEFAULT_SIDE_BIAS,
    )

    today = dt.date.today()
    return {
        "ticker": ticker,
        "tickers": [ticker],
        "tickers_raw": ticker,
        "frequency": DEFAULT_FREQUENCY,
        "frequency_display": "Monthly",
        "start_time": f"{today.year - 5}-{today.month:02d}",
        "end_time": "",
        "parsed_start_time": today - dt.timedelta(days=365 * 2),
        "parsed_end_time": today,
        "rolling_window": DEFAULT_ROLLING_WINDOW,
        "risk_threshold": DEFAULT_RISK_THRESHOLD,
        "side_bias": DEFAULT_SIDE_BIAS,
        "target_bias": 0,
        "streaming_mode": False,
    }


def refresh_snapshot(ticker: str = DEMO_TICKER) -> dict:
    """Recompute snapshot.json + live-data fixtures. Returns the snapshot."""
    import logging

    logging.basicConfig(level=logging.WARNING)
    from services.market.analysis import AnalysisService
    from services.market.facade import MarketService
    from services.options.chain import OptionsChainService

    form = _demo_form_data(ticker)
    slices: dict = {}

    # Deterministic fixtures first (expiry calendar + odds demo table).
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import gen_pages_fixtures

    gen_pages_fixtures.main()

    print(f"[snapshot] market_review slice for {ticker} …")
    slices["market_review"] = AnalysisService.generate_market_review_slice(dict(form)) or {}
    print(f"[snapshot] statistical slice for {ticker} …")
    slices["statistical"] = AnalysisService.generate_statistical_slice(dict(form)) or {}
    print(f"[snapshot] assessment slice for {ticker} …")
    slices["assessment"] = AnalysisService.generate_assessment_slice(dict(form)) or {}

    print(f"[snapshot] options_chain analysis for {ticker} (live chain) …")
    try:
        slices["options_chain"] = OptionsChainService.generate_options_chain_analysis(ticker) or {}
        chain_live = True
    except Exception as e:  # offline CI/dev without Yahoo access
        print(f"[snapshot] WARNING: live chain unavailable ({e}); fragment renders its error state")
        slices["options_chain"] = {"oc_error": str(e)}
        chain_live = False
    _assert_jsonable(slices)

    snapshot = {
        "meta": {
            "ticker": ticker,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "live_option_chain": chain_live,
        },
        "index": {k: v for k, v in form.items() if not k.startswith("parsed_")},
        "slices": slices,
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    kb = SNAPSHOT_PATH.stat().st_size / 1024
    print(f"[snapshot] wrote {SNAPSHOT_PATH} ({kb:.0f} KB)")

    _refresh_api_fixtures(ticker)
    return snapshot


def _refresh_api_fixtures(ticker: str) -> None:
    """Regenerate API fixtures from local DB / live services (deterministic)."""
    from services.market.facade import MarketService

    # -- market_review_ts: real DB-backed payload (same producer as the route)
    print("[snapshot] market_review_ts fixture …")
    mrts = {"status": "ok", **MarketService.market_review_timeseries(ticker)}
    data_through = max(mrts.get("dates") or ["?"])
    (FIXTURES_DIR / "market_review_ts.nvda.json").write_text(
        json.dumps({**mrts, "sample_note": f"NVDA snapshot for GitHub Pages demo (data through {data_through})."},
                   ensure_ascii=False), encoding="utf-8")

    # -- option_chain: live filtered records (same producer as the route);
    #    keep the committed synthetic file when Yahoo is unreachable.
    print("[snapshot] option_chain fixture (live, fallback: keep committed) …")
    try:
        from services.options.chain import OptionsChainService

        live = OptionsChainService.fetch_records_filtered(ticker)
        if live.get("expirations"):
            (FIXTURES_DIR / "option_chain.nvda.json").write_text(
                json.dumps({**live, "ticker": ticker,
                            "sample_note": f"NVDA chain snapshot for GitHub Pages demo ({live['expirations'][0]}…)."},
                           ensure_ascii=False), encoding="utf-8")
            print(f"[snapshot]   live chain: spot {live.get('spot')}, {len(live['expirations'])} expiries")
        else:
            print("[snapshot]   live chain empty; keeping committed fixture")
    except Exception as e:
        print(f"[snapshot]   live chain unavailable ({e}); keeping committed fixture")

    # -- regime: deterministic, from the persisted regime_log (never live-mix)
    print("[snapshot] regime fixtures from regime_log …")
    conn = sqlite3.connect(REPO_ROOT / "market_data.sqlite")
    conn.row_factory = sqlite3.Row
    log_rows = [dict(r) for r in conn.execute("SELECT * FROM regime_log ORDER BY date")]
    conn.close()
    if not log_rows:
        raise RuntimeError("regime_log is empty — cannot build regime fixtures")
    latest = log_rows[-1]
    current = {
        "status": "ok",
        "label": {
            "date": latest["date"],
            "vol_regime": latest["vol_regime"],
            "dir_regime": latest["dir_regime"],
            "vix_value": latest["vix_value"],
            "sma_20": latest["sma_20"],
            "sma_slope_5d": latest["sma_slope_5d"],
            "close_vs_sma_pct": latest["close_vs_sma_pct"],
            "notes": latest.get("notes") or "",
        },
        "data_complete": True,
        "source": "log",
        "sample_note": "Persisted regime_log snapshot for GitHub Pages demo.",
    }
    (FIXTURES_DIR / "regime_current.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    import pandas as pd

    from core.regime import coverage_report

    df = pd.DataFrame(log_rows).set_index(pd.to_datetime([r["date"] for r in log_rows]))
    history = {
        "status": "ok",
        "rows": [
            {k: r[k] for k in ("date", "vol_regime", "dir_regime", "vix_value", "sma_20",
                               "sma_slope_5d", "close_vs_sma_pct") if k in r}
            for r in log_rows
        ],
        "coverage": coverage_report(df),
        "source": "log",
    }
    (FIXTURES_DIR / "regime_history.json").write_text(
        json.dumps(history, ensure_ascii=False), encoding="utf-8")

    # -- validate_tickers: NVDA + benchmark tickers, latest closes from DB
    print("[snapshot] validate_tickers fixture …")
    conn = sqlite3.connect(REPO_ROOT / "market_data.sqlite")
    tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM market_review_prices")]
    results = {}
    for t in tickers:
        row = conn.execute(
            "SELECT close FROM market_review_prices WHERE ticker=? ORDER BY date DESC LIMIT 1", (t,)).fetchone()
        price = round(float(row[0]), 2) if row and row[0] is not None else None
        results[t] = {"valid": price is not None, "price": price, "message": "demo snapshot"}
    conn.close()
    (FIXTURES_DIR / "validate_tickers.json").write_text(
        json.dumps({"status": "ok", "results": results,
                    "sample_note": "Demo validation snapshot (NVDA + benchmarks)."},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[snapshot] fixtures done ({len(results)} tickers)")


# --------------------------------------------------------------------------
# assemble (CI-safe: jinja2 only)
# --------------------------------------------------------------------------

def _jinja_env():
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)

    def url_for(endpoint, **values):
        if endpoint == "static":
            return "./static/" + values.get("filename", "")
        return "#"

    env.globals["url_for"] = url_for
    env.filters["tojson"] = lambda v: json.dumps(v, ensure_ascii=False)
    return env


def _redirect_page(tab_id: str, title: str) -> str:
    target = f"../#{tab_id}" if tab_id else "../"
    label = f"“{title}” tab" if tab_id else "portal"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="0; url={target}" />
  <link rel="canonical" href="{target}" />
  <title>{title} — OptionLab demo</title>
</head>
<body>
  <p>This demo page moved into the identical app UI — continuing to the {label}…
  <a href="{target}">continue</a>.</p>
</body>
</html>
"""


def assemble(out_dir: Path, ticker: str = DEMO_TICKER) -> Path:
    from jinja2 import __version__ as _v  # noqa: F401  (fail fast without jinja2)

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if snapshot.get("meta", {}).get("ticker") != ticker:
        print(f"[assemble] WARNING: snapshot is for {snapshot.get('meta', {}).get('ticker')}, asked {ticker}")
    slices = snapshot.get("slices", {})
    index_vars = dict(snapshot.get("index", {}))

    try:
        mrts = json.loads((FIXTURES_DIR / "market_review_ts.nvda.json").read_text(encoding="utf-8"))
        data_through = max(mrts.get("dates") or ["?"])
    except Exception:
        data_through = snapshot.get("meta", {}).get("generated_at", "?")[:10]

    context = {**index_vars, "ticker": ticker, "tickers": [ticker], "tickers_raw": ticker,
               "streaming_mode": False}
    for kind in ("market_review", "statistical", "assessment", "options_chain"):
        context.update(slices.get(kind) or {})

    html = _jinja_env().get_template("index.html").render(**context)

    # -- Pages adaptations (only delta vs the Flask app) --
    html = re.sub(r'    <!-- Probe: Alpine mounts x-data.*?\n', "", html, flags=re.DOTALL)  # orphan comment
    html = re.sub(r'<div id="scaffold-probe".*?</div>\s*', "", html, flags=re.DOTALL)  # dev probe: no backend
    html = html.replace('"/static/', '"./static/').replace("'/static/", "'./static/")
    banner = BANNER_HTML.format(ticker=ticker, data_through=data_through)
    html = html.replace("</header>", "</header>\n" + banner, 1)
    shim_tag = '<script src="./pages-shim.js"></script>'
    if "</head>" in html:
        # Early: must precede the inline /health/status poll so no request
        # escapes the demo stub (app scripts only call fetch at runtime).
        html = html.replace("</head>", "    " + shim_tag + "\n</head>", 1)
    else:
        html = html.replace("</body>", shim_tag + "\n</body>", 1) if "</body>" in html else html + shim_tag
    html = "<!-- GENERATED by scripts/build_pages_site.py — do not edit by hand. -->\n" + html

    # Demo ships in the "post-analysis" state: ticker input prefilled so all
    # auto-load tab handlers (option chain / odds / sim) work on first click,
    # exactly like the Flask app after submitting the form.
    html = html.replace('id="ticker" name="ticker" value=""',
                        f'id="ticker" name="ticker" value="{ticker}"', 1)
    # -- sanity: identical-UI invariants --
    assert 'hx-get="/render/' not in html, "streaming placeholders leaked into static build"
    assert '"/static/' not in html and "'/static/" not in html, "absolute /static/ paths break the /OptionLab/ subpath"
    for tab_id in ("tab-parameter", "tab-market-review", "tab-statistical-analysis",
                   "tab-market-assessment", "tab-option-chain", "tab-options-chain",
                   "tab-odds", "tab-regime", "tab-simulation", "tab-option-pricing-matrix", "tab-config"):
        assert f'id="{tab_id}"' in html, f"missing tab body: {tab_id}"
    assert "./pages-shim.js" in html and "pages-demo-banner" in html

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    # static/ verbatim (identical CSS/JS) + shim (already lives in site/)
    dest_static = out_dir / "static"
    if dest_static.exists():
        shutil.rmtree(dest_static)
    shutil.copytree(STATIC_DIR, dest_static,
                    ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))

    # Drop pre-convergence leftovers (replaced by redirects / site/static).
    for stale_js in (out_dir / "sim").glob("*.js"):
        stale_js.unlink()
    for stale_dir in ("vendor", "assets"):
        shutil.rmtree(out_dir / stale_dir, ignore_errors=True)

    # legacy demo pages → redirect into the identical app tabs
    for rel, (tab_id, title) in REDIRECTS.items():
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_redirect_page(tab_id, title), encoding="utf-8")

    print(f"[assemble] wrote {out_dir}/index.html ({len(html) / 1024:.0f} KB) + static/ + {len(REDIRECTS)} redirects")
    return out_dir / "index.html"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the Pages mirror of the Flask app.")
    ap.add_argument("--out", default=str(SITE_DIR), help="output dir (default: site/)")
    ap.add_argument("--ticker", default=DEMO_TICKER)
    ap.add_argument("--refresh-snapshot", action="store_true",
                    help="recompute snapshot.json + live fixtures (needs full deps + DB)")
    args = ap.parse_args(argv)

    if args.refresh_snapshot:
        sys.path.insert(0, str(REPO_ROOT))
        refresh_snapshot(args.ticker)
    assemble(Path(args.out), args.ticker)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

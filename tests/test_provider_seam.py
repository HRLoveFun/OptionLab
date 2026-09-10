"""Contract tests for the data-provider seam (ADR 0011, batch B1).

Domain:    Tests — Provider Seam
Context:
  - Batch B1 moved every yfinance call behind ``data_pipeline/providers/`` and
    introduced the canonical schema + registry. These tests pin the parts of
    that contract that are otherwise invisible: the single-import invariant, the
    canonical mapping units, and the registry's resolution rules.
Contracts:
  - Only production code under ``data_pipeline/providers/`` imports yfinance.
  - ``to_canonical_bars`` / ``to_option_chain_snapshot`` apply the unit rules in
    ``providers/base.py`` (decimal IV, nullable bid/ask, no ``inTheMoney``).
  - ``get_provider`` defaults to yfinance and rejects unknown names loudly.
  - ``data_pipeline.yf_client`` still re-exports the legacy callables unchanged.
Dependencies UPWARD:
  - (none — stdlib + pytest + the package under test)
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROVIDER_DIR = REPO_ROOT / "data_pipeline" / "providers"

# Production roots only: doc_guard's `single-yf-exit` rule deliberately exempts
# tests/ and scripts/ (test doubles patch `yfinance.download` on the module).
PRODUCTION_ROOTS = ("app.py", "routes", "core", "data_pipeline", "services", "utils")


def _production_python_files() -> list[Path]:
    out: list[Path] = []
    for sub in PRODUCTION_ROOTS:
        p = REPO_ROOT / sub
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out.extend(x for x in p.rglob("*.py") if "__pycache__" not in x.parts)
    return sorted(out)


def _imports_yfinance(path: Path) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(a.name.split(".", 1)[0] == "yfinance" for a in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".", 1)[0] == "yfinance":
                return True
    return False


def test_only_provider_seam_imports_yfinance():
    """B1 exit criterion: production code imports yfinance only under providers/."""
    offenders = [str(p.relative_to(REPO_ROOT)) for p in _production_python_files() if _imports_yfinance(p)]
    assert offenders, "expected at least one importer inside data_pipeline/providers/"
    for rel in offenders:
        assert Path(rel).is_relative_to(Path("data_pipeline") / "providers"), (
            f"{rel} imports yfinance outside data_pipeline/providers/ — see ADR 0011"
        )


def test_doc_guard_single_yf_exit_allows_provider_modules():
    """The rescoped guard must not flag the provider package itself."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "doc_guard.py"),
            "--json",
            "--rule",
            "single-yf-exit",
            "--files",
            str(PROVIDER_DIR / "yfinance_provider.py"),
            str(PROVIDER_DIR / "yf_snapshot.py"),
        ],
        capture_output=True,
        text=True,
    )
    assert "single-yf-exit" not in (result.stdout or ""), result.stdout
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
def test_registry_defaults_to_yfinance():
    from data_pipeline.providers import available_providers, get_provider
    from data_pipeline.providers.base import MarketDataProvider

    assert available_providers() == ("yfinance",)
    provider = get_provider()
    assert provider.name == "yfinance"
    assert isinstance(provider, MarketDataProvider)
    # Instances are cached per resolved name.
    assert get_provider("yfinance") is provider


def test_registry_rejects_unknown_provider():
    from data_pipeline.providers import get_provider

    with pytest.raises(ValueError, match="unknown data provider"):
        get_provider("does-not-exist")


def test_registry_honours_env_override(monkeypatch):
    from data_pipeline.providers import get_provider

    monkeypatch.setenv("MARKET_DATA_PROVIDER", "nope")
    with pytest.raises(ValueError):
        get_provider()


# ---------------------------------------------------------------------------
# Canonical mapping
# ---------------------------------------------------------------------------
def _yf_bars_frame() -> pd.DataFrame:
    idx = pd.DatetimeIndex(["2026-01-02", "2026-01-05"])
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.0, 102.0],
            "Adj Close": [100.5, 101.5],
            "Volume": [1_000_000, 1_100_000],
        },
        index=idx,
    )


def test_to_canonical_bars_renames_and_orders_columns():
    from data_pipeline.providers.base import CANONICAL_BAR_COLUMNS
    from data_pipeline.providers.yfinance_provider import to_canonical_bars

    out = to_canonical_bars(_yf_bars_frame())

    assert tuple(out.columns) == CANONICAL_BAR_COLUMNS
    assert out["adj_close"].tolist() == [100.5, 101.5]
    assert out["close"].tolist() == [101.0, 102.0]
    assert out.index.is_monotonic_increasing


def test_to_canonical_bars_handles_empty_and_missing_columns():
    from data_pipeline.providers.base import CANONICAL_BAR_COLUMNS
    from data_pipeline.providers.yfinance_provider import to_canonical_bars

    assert tuple(to_canonical_bars(None).columns) == CANONICAL_BAR_COLUMNS
    assert tuple(to_canonical_bars(pd.DataFrame()).columns) == CANONICAL_BAR_COLUMNS

    partial = pd.DataFrame({"Close": [1.0]}, index=pd.DatetimeIndex(["2026-01-02"]))
    out = to_canonical_bars(partial)
    assert tuple(out.columns) == CANONICAL_BAR_COLUMNS
    assert out["adj_close"].isna().all()


def _legacy_chain_payload() -> dict:
    calls = pd.DataFrame(
        {
            "strike": [100.0, 105.0],
            "bid": [2.0, float("nan")],
            "ask": [2.2, float("nan")],
            "lastPrice": [2.1, 0.4],
            "impliedVolatility": [0.25, 0.30],
            "openInterest": [500.0, 120.0],
            "volume": [10.0, 0.0],
            "inTheMoney": [True, False],
        }
    )
    puts = pd.DataFrame(
        {
            "strike": [100.0],
            "bid": [1.5],
            "ask": [1.7],
            "lastPrice": [1.6],
            "impliedVolatility": [0.28],
            "openInterest": [300.0],
            "volume": [5.0],
            "inTheMoney": [False],
        }
    )
    return {
        "ticker": "AAPL",
        "spot": 101.0,
        "expiries": ["2026-01-16"],
        "chain": {"2026-01-16": {"calls": calls, "puts": puts}},
    }


def test_to_option_chain_snapshot_applies_canonical_units():
    from data_pipeline.providers.yf_snapshot import to_option_chain_snapshot

    snap = to_option_chain_snapshot(_legacy_chain_payload())

    assert snap.provider == "yfinance"
    assert snap.symbol == "AAPL"
    assert snap.spot == 101.0
    assert snap.expiries == ("2026-01-16",)

    calls = snap.legs("2026-01-16", "calls")
    assert [leg.strike for leg in calls] == [100.0, 105.0]
    # iv stays a decimal (0.25 == 25 %); futu's percent form is normalised at the
    # provider boundary — see providers/base.py.
    assert calls[0].iv == 0.25
    assert calls[1].iv == pytest.approx(0.30)
    # NaN quotes become None rather than 0 — "absent" must stay expressible.
    assert calls[1].bid is None
    assert calls[1].ask is None
    assert calls[0].open_interest == 500.0

    # inTheMoney is deliberately NOT canonical (derivable, and futu has none).
    assert not hasattr(calls[0], "in_the_money")

    assert len(snap.legs("2026-01-16", "puts")) == 1
    assert snap.legs("1999-01-01", "calls") == ()


def test_to_option_chain_snapshot_tolerates_empty_payload():
    from data_pipeline.providers.base import OptionChainSnapshot
    from data_pipeline.providers.yf_snapshot import to_option_chain_snapshot

    snap = to_option_chain_snapshot({"ticker": "MSFT", "spot": None, "expiries": [], "chain": {}})
    assert isinstance(snap, OptionChainSnapshot)
    assert snap.expiries == ()
    assert snap.spot is None


# ---------------------------------------------------------------------------
# Compatibility shim
# ---------------------------------------------------------------------------
def test_yf_client_reexports_legacy_callables_unchanged():
    from data_pipeline import yf_client
    from data_pipeline.providers import yf_snapshot, yfinance_provider

    assert yf_client.fetch_spot is yf_snapshot.fetch_spot
    assert yf_client.fetch_spots_bulk is yf_snapshot.fetch_spots_bulk
    assert yf_client.fetch_option_chain is yf_snapshot.fetch_option_chain
    assert yf_client.fetch_close_panel is yfinance_provider.fetch_close_panel
    assert yf_client.fetch_daily_ohlcv is yfinance_provider.fetch_daily_ohlcv

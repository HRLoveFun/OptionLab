"""Tests for market regime labeling (core.regime) and service idempotency."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from core.regime import (
    DirRegime,
    VolRegime,
    classify_vol,
    coverage_report,
    label_regime,
    label_series,
    regime_transitions,
)


# ── classify_vol ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "vix,expected",
    [
        (10.0, VolRegime.LOW),
        (14.99, VolRegime.LOW),
        (15.0, VolRegime.MID),
        (19.99, VolRegime.MID),
        (20.0, VolRegime.HIGH),
        (29.99, VolRegime.HIGH),
        (30.0, VolRegime.STRESS),
        (65.0, VolRegime.STRESS),
        (None, VolRegime.UNKNOWN),
        (float("nan"), VolRegime.UNKNOWN),
    ],
)
def test_classify_vol_thresholds(vix, expected):
    assert classify_vol(vix) is expected


# ── label_regime with synthetic series ────────────────────────────
def _series(prices, end):
    dates = pd.date_range(end=pd.Timestamp(end), periods=len(prices), freq="B")
    return pd.Series(prices, index=dates, dtype=float)


def test_label_regime_uptrend_low_vol():
    # Monotonic uptrend → UP_TREND; low VIX → LOW_VOL
    end = dt.date(2024, 1, 31)
    spy = _series(np.linspace(100, 150, 60), end)
    vix = _series([12.0] * 60, end)
    out = label_regime(end, vix, spy)
    assert out.vol_regime is VolRegime.LOW
    assert out.dir_regime is DirRegime.UP
    assert out.vix_value == 12.0
    assert out.sma_slope_5d > 0.005
    assert out.close_vs_sma_pct > 0


def test_label_regime_downtrend_stress_vol():
    end = dt.date(2024, 3, 20)
    spy = _series(np.linspace(150, 100, 60), end)
    vix = _series([35.0] * 60, end)
    out = label_regime(end, vix, spy)
    assert out.vol_regime is VolRegime.STRESS
    assert out.dir_regime is DirRegime.DOWN
    assert out.sma_slope_5d < -0.005


def test_label_regime_chop_when_flat():
    end = dt.date(2024, 5, 10)
    spy = _series([100.0 + ((-1) ** i) * 0.2 for i in range(60)], end)
    vix = _series([17.0] * 60, end)
    out = label_regime(end, vix, spy)
    assert out.vol_regime is VolRegime.MID
    assert out.dir_regime is DirRegime.CHOP


def test_label_regime_missing_data_returns_unknown():
    end = dt.date(2024, 1, 10)
    out = label_regime(end, vix_series=None, spy_close=None)
    assert out.vol_regime is VolRegime.UNKNOWN
    assert out.dir_regime is DirRegime.UNKNOWN
    assert out.vix_value is None


def test_label_regime_insufficient_history():
    end = dt.date(2024, 1, 10)
    short_spy = _series(np.linspace(100, 110, 10), end)  # < 25 rows
    out = label_regime(end, None, short_spy)
    assert out.dir_regime is DirRegime.UNKNOWN


def test_label_regime_to_dict_json_safe():
    end = dt.date(2024, 1, 31)
    spy = _series(np.linspace(100, 150, 60), end)
    out = label_regime(end, None, spy).to_dict()
    assert out["date"] == "2024-01-31"
    assert out["vol_regime"] == "UNKNOWN_VOL"
    assert out["vix_value"] is None  # None, not NaN


# ── label_series + transitions ────────────────────────────────────
def test_label_series_and_transitions():
    end = dt.date(2024, 6, 30)
    # Up for 30 days, then down for 30 days
    prices = np.concatenate([np.linspace(100, 150, 30), np.linspace(150, 100, 30)])
    spy = _series(prices, end)
    vix = _series([14.0] * 30 + [25.0] * 30, end)
    df = label_series(vix, spy).dropna(subset=["sma_20"])
    assert not df.empty
    vols = set(df["vol_regime"])
    assert "LOW_VOL" in vols
    assert "HIGH_VOL" in vols
    transitions = regime_transitions(df)
    assert len(transitions) >= 1

    cov = coverage_report(df)
    assert cov["charter_exit_condition_met"] is True
    assert cov["unique_composite_regimes"] >= 2


def test_coverage_report_empty():
    out = coverage_report(pd.DataFrame())
    assert out["charter_exit_condition_met"] is False
    assert out["unique_composite_regimes"] == 0


# ── Idempotent log persistence ────────────────────────────────────
def test_regime_log_idempotent(monkeypatch):
    """Re-running append_today on the same date should update, not duplicate."""
    import pandas as pd_mod

    from services import regime_service as svc

    end = dt.date(2024, 4, 15)
    fake_spy = _series(np.linspace(100, 150, 70), end)
    fake_vix = _series([13.0] * 70, end)

    def _fake_fetch(ticker, start, e):
        if ticker == svc.VIX_TICKER:
            return fake_vix
        return fake_spy

    monkeypatch.setattr(svc, "_fetch_close_series", _fake_fetch)

    # First append
    r1 = svc.RegimeService.append_today(as_of=end)
    # Second append — same date
    r2 = svc.RegimeService.append_today(as_of=end)

    assert r1["label"]["date"] == "2024-04-15"
    assert r2["label"]["date"] == "2024-04-15"

    df = svc._load_log_df()
    assert len(df) == 1  # idempotency


def test_regime_backfill_persists_range(monkeypatch):
    from services import regime_service as svc

    end = dt.date(2024, 5, 31)
    fake_spy = _series(np.linspace(100, 150, 200), end)
    fake_vix = _series([16.0] * 200, end)

    def _fake_fetch(ticker, start, e):
        return fake_vix if ticker == svc.VIX_TICKER else fake_spy

    monkeypatch.setattr(svc, "_fetch_close_series", _fake_fetch)

    result = svc.RegimeService.backfill(days=30, end_date=end)
    assert result["persisted_rows"] > 0

    df = svc._load_log_df()
    assert len(df) == result["persisted_rows"]
    # Running twice should not duplicate
    result2 = svc.RegimeService.backfill(days=30, end_date=end)
    df2 = svc._load_log_df()
    assert len(df2) == result2["persisted_rows"]


# ── Regression tests for the "No data / 500" bug ──────────────────
def test_label_series_empty_inputs_returns_structured_df():
    """Empty inputs must return an indexable DataFrame with expected columns.

    Regression: previously returned bare DataFrame, causing
    ``.dropna(subset=['sma_20'])`` to KeyError in the service layer.
    """
    out = label_series(pd.Series(dtype=float), pd.Series(dtype=float))
    assert out.empty
    for col in ("sma_20", "vol_regime", "dir_regime"):
        assert col in out.columns
    # The critical invariant: this call must not raise
    out.dropna(subset=["sma_20"])


def test_fetch_df_aggregate_query_without_date_column():
    """Regression: ``fetch_df`` must not try to index by 'date' on queries
    that don't select a date column (e.g. ``SELECT MAX(date)``)."""
    from data_pipeline.db import fetch_df, init_db

    init_db()
    df = fetch_df("SELECT MAX(date) as max_date FROM raw_prices WHERE ticker=?", ("DOES_NOT_EXIST",))
    # Single-row result with a NULL max_date — must not raise
    assert "max_date" in df.columns
    assert df.iloc[0]["max_date"] is None


def test_regime_history_empty_db_returns_ok(monkeypatch):
    """Regression: hitting /api/regime/history on a fresh DB must not 500."""
    from services import regime_service as svc

    # Simulate no market data available (DataService returns empty series)
    monkeypatch.setattr(svc, "_fetch_close_series", lambda *a, **k: pd.Series(dtype=float))

    result = svc.RegimeService.history(days=180)
    assert result["rows"] == []
    assert result["coverage"]["charter_exit_condition_met"] is False
    assert result["source"] in ("live", "log")


def test_ensure_history_triggers_bootstrap_when_thin(monkeypatch):
    """When the DB has < MIN_TRADING_ROWS rows for a ticker, _ensure_history
    must invoke the full pipeline. This is the fix for the "spy_insufficient_history:13"
    symptom where DataService only seeds 7 days per access.
    """
    from services import regime_service as svc

    called = {"ticker": None, "days": None}

    def _fake_bootstrap(ticker, days=svc.BOOTSTRAP_DAYS):
        called["ticker"] = ticker
        called["days"] = days

    monkeypatch.setattr(svc, "_bootstrap_history", _fake_bootstrap)
    monkeypatch.setattr(svc, "_count_clean_rows", lambda t: 7)  # thin DB

    svc._ensure_history("SPY")
    assert called["ticker"] == "SPY"
    assert called["days"] >= svc.SMA_WINDOW + svc.SLOPE_LOOKBACK


def test_ensure_history_noop_when_db_populated(monkeypatch):
    """When the DB already has enough rows, no bootstrap should run."""
    from services import regime_service as svc

    called = []
    monkeypatch.setattr(svc, "_bootstrap_history", lambda *a, **k: called.append(True))
    monkeypatch.setattr(svc, "_count_clean_rows", lambda t: 500)  # plenty

    svc._ensure_history("SPY")
    assert called == []



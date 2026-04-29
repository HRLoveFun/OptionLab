"""Tests for core/signals.py."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import signals as S


def _synthetic(n: int = 400, seed: int = 0, drift: float = 0.0, vol: float = 0.01) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(loc=drift, scale=vol, size=n)
    close = 100 * np.exp(np.cumsum(rets))
    idx = pd.bdate_range("2022-01-01", periods=n)
    return pd.DataFrame({"Close": close, "High": close * 1.005, "Low": close * 0.995}, index=idx)


def test_hv_pct_returns_positive_pct():
    df = _synthetic(vol=0.012)
    close = S._close(df)
    val = S.hv_pct(close, n=20)
    assert val is not None and 5 < val < 100  # annualised 1.2% daily ≈ 19%


def test_hv_pct_returns_none_when_too_few_points():
    df = _synthetic(n=5)
    assert S.hv_pct(S._close(df), n=20) is None


def test_hv_percentile_in_range():
    df = _synthetic(vol=0.012)
    pct = S.hv_percentile(S._close(df), n=20, lookback=252)
    assert pct is not None and 0 <= pct <= 100


def test_hv_vs_iv_labels():
    df = _synthetic(vol=0.01)
    close = S._close(df)
    hv = S.hv_pct(close, 20)
    assert hv is not None
    rich = S.hv_vs_iv(close, iv_pct=hv * 1.5)
    fair = S.hv_vs_iv(close, iv_pct=hv * 1.0)
    cheap = S.hv_vs_iv(close, iv_pct=hv * 0.5)
    assert rich is not None and rich["label"] == "rich"
    assert fair is not None and fair["label"] == "fair"
    assert cheap is not None and cheap["label"] == "cheap"


def test_rsi_returns_value_in_range():
    df = _synthetic()
    val = S.rsi(S._close(df), n=14)
    assert val is not None and 0 <= val <= 100


def test_bollinger_position_classifies():
    df = _synthetic()
    band = S.bollinger_position(S._close(df), n=20, k=2.0)
    assert band is not None
    assert band["position"] in {"below", "lower_band", "inside", "upper_band", "above"}
    assert band["lower"] < band["ma"] < band["upper"]


def test_mean_reversion_score_in_unit_interval():
    df = _synthetic()
    mr = S.mean_reversion_score(S._close(df))
    assert mr is not None
    assert -1.0 <= mr["score"] <= 1.0
    assert mr["label"] in {"oversold", "neutral", "overbought"}


def test_build_signals_full_bundle():
    df = _synthetic()
    out = S.build_signals(df, current_iv_pct=25.0)
    for key in ("hv_20", "hv_60", "rsi_14", "bollinger_20", "mean_reversion", "vol_premium"):
        assert key in out
    assert out["vol_premium"] is not None


def test_build_signals_handles_missing_close_column():
    df = pd.DataFrame({"Volume": [1, 2, 3]})
    out = S.build_signals(df)
    assert all(v is None for v in out.values())

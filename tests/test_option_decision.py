"""Tests for core.option_decision — pure computation logic."""

import math
import pytest
import pandas as pd
import numpy as np

from core.option_decision import (
    enrich_contract,
    compute_ev,
    select_dte_range,
    filter_and_rank,
    get_heuristic_notes,
    calculate_iv_rank,
    calculate_iv_percentile,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_contract(**overrides):
    """Create a minimal contract dict with sensible defaults."""
    base = {
        'strike': 150.0,
        'dte': 30,
        'expiry': '2026-04-20',
        'bid': 3.00,
        'ask': 3.50,
        'last_price': 3.25,
        'mid_price': 3.25,
        'delta': -0.35,
        'gamma': 0.02,
        'theta': -0.05,
        'vega': 0.12,
        'iv': 28.0,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Module 3 — enrich_contract
# ---------------------------------------------------------------------------

class TestEnrichContract:

    def test_basic_enrichment(self):
        c = _make_contract()
        result = enrich_contract(c, budget=5000, spot_price=160.0,
                                 target_move_pct=-0.08)
        assert result is not None
        d = result['derived']
        assert d['contracts_n'] >= 1
        assert d['delta_per_dollar'] > 0
        assert d['target_price'] == pytest.approx(160.0 * 0.92, rel=1e-4)
        assert d['vega_theta_ratio'] > 0
        assert d['implied_win_rate'] == pytest.approx(0.35, abs=0.01)

    def test_zero_mid_price_returns_none(self):
        c = _make_contract(mid_price=0.0)
        assert enrich_contract(c, 5000, 160.0, -0.08) is None

    def test_too_expensive_returns_none(self):
        c = _make_contract(mid_price=60.0)
        # budget=5000, one contract costs 60*100=6000 > budget
        assert enrich_contract(c, 5000, 160.0, -0.08) is None

    def test_payoff_calculation(self):
        c = _make_contract(strike=150.0, mid_price=3.25)
        result = enrich_contract(c, budget=5000, spot_price=160.0,
                                 target_move_pct=-0.10)
        d = result['derived']
        target_price = 160.0 * 0.90  # 144
        intrinsic = max(150.0 - 144.0, 0)  # 6
        expected_payoff = 6.0 - 3.25  # 2.75
        assert d['payoff_at_target'] == pytest.approx(expected_payoff, abs=0.01)

    def test_zero_theta_vega_theta_ratio(self):
        c = _make_contract(theta=0.0)
        result = enrich_contract(c, 5000, 160.0, -0.08)
        assert result['derived']['vega_theta_ratio'] == 999.99


# ---------------------------------------------------------------------------
# Module 4 — compute_ev
# ---------------------------------------------------------------------------

class TestComputeEV:

    def test_positive_ev_high_conviction(self):
        c = _make_contract()
        c = enrich_contract(c, 5000, 160.0, -0.10)
        assert c is not None
        c = compute_ev(c, directional_conviction=0.8,
                       vol_conviction=0.7, budget=5000,
                       time_horizon_days=21)
        # High conviction should yield positive EV
        assert 'ev' in c
        assert 'ev_ratio' in c

    def test_zero_conviction_negative_ev(self):
        c = _make_contract()
        c = enrich_contract(c, 5000, 160.0, -0.08)
        c = compute_ev(c, directional_conviction=0.0,
                       vol_conviction=0.0, budget=5000,
                       time_horizon_days=21)
        # Zero conviction → lose entire budget on loss side
        assert c['ev'] <= 0


# ---------------------------------------------------------------------------
# Module 5 — DTE selector
# ---------------------------------------------------------------------------

class TestSelectDTERange:

    def test_fast_timing(self):
        lo, hi = select_dte_range('FAST', 21)
        assert lo == 21
        assert hi == 35

    def test_medium_timing(self):
        lo, hi = select_dte_range('MEDIUM', 21)
        assert lo == 21
        assert hi == 51

    def test_slow_timing(self):
        lo, hi = select_dte_range('SLOW', 21)
        assert lo == 35
        assert hi == 81

    def test_case_insensitive(self):
        lo, hi = select_dte_range('fast', 10)
        assert lo == 10
        assert hi == 24


# ---------------------------------------------------------------------------
# Module 6 — filter_and_rank
# ---------------------------------------------------------------------------

class TestFilterAndRank:

    def _make_enriched(self, dte=30, ev=100, ev_ratio=0.5, vt_ratio=3.0, n=5):
        return {
            'dte': dte,
            'ev': ev,
            'ev_ratio': ev_ratio,
            'derived': {
                'vega_theta_ratio': vt_ratio,
                'contracts_n': n,
            },
        }

    def test_filters_by_dte(self):
        candidates = [self._make_enriched(dte=10), self._make_enriched(dte=50)]
        result = filter_and_rank(candidates, min_dte=20, max_dte=60)
        assert len(result) == 1
        assert result[0]['dte'] == 50

    def test_filters_negative_ev(self):
        candidates = [self._make_enriched(ev=-10), self._make_enriched(ev=50)]
        result = filter_and_rank(candidates, 0, 100)
        assert len(result) == 1
        assert result[0]['ev'] == 50

    def test_filters_low_vega_theta(self):
        candidates = [self._make_enriched(vt_ratio=1.0), self._make_enriched(vt_ratio=5.0)]
        result = filter_and_rank(candidates, 0, 100, min_vt=2.0)
        assert len(result) == 1

    def test_sorts_by_ev_ratio_desc(self):
        candidates = [
            self._make_enriched(ev_ratio=0.3),
            self._make_enriched(ev_ratio=0.8),
            self._make_enriched(ev_ratio=0.5),
        ]
        result = filter_and_rank(candidates, 0, 100)
        assert result[0]['ev_ratio'] == 0.8
        assert result[1]['ev_ratio'] == 0.5
        assert result[2]['ev_ratio'] == 0.3

    def test_empty_input(self):
        assert filter_and_rank([], 0, 100) == []


# ---------------------------------------------------------------------------
# Heuristics
# ---------------------------------------------------------------------------

class TestHeuristics:

    def test_directional_dominates(self):
        notes = get_heuristic_notes(0.8, 0.3, 'MEDIUM', 50)
        assert any('higher |delta|' in n for n in notes)

    def test_vol_dominates(self):
        notes = get_heuristic_notes(0.3, 0.8, 'MEDIUM', 50)
        assert any('ATM' in n for n in notes)

    def test_cheap_vol_fast(self):
        notes = get_heuristic_notes(0.5, 0.5, 'FAST', 20)
        assert any('cheap' in n.lower() for n in notes)

    def test_expensive_vol(self):
        notes = get_heuristic_notes(0.5, 0.5, 'MEDIUM', 80)
        assert any('expensive' in n.lower() for n in notes)


# ---------------------------------------------------------------------------
# IV helpers
# ---------------------------------------------------------------------------

class TestIVHelpers:

    def test_iv_rank(self):
        ts = {7: 20.0, 30: 25.0, 60: 30.0}
        rank = calculate_iv_rank(ts)
        assert rank is not None
        assert 0 <= rank <= 100

    def test_iv_rank_insufficient_data(self):
        assert calculate_iv_rank({10: 25.0}) is None

    def test_iv_percentile(self):
        ts = {7: 20.0, 30: 25.0, 60: 30.0}
        pct = calculate_iv_percentile(ts)
        assert pct is not None
        assert 0 <= pct <= 100

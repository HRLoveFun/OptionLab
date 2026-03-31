"""Tests for option chain filtering in app.py."""
import pytest
from datetime import datetime, timedelta


def test_filter_dte():
    """Verify expirations beyond max_dte are excluded."""
    from app import _filter_option_chain

    today = datetime.now().date()
    exp_near = (today + timedelta(days=10)).strftime('%Y-%m-%d')
    exp_far = (today + timedelta(days=60)).strftime('%Y-%m-%d')

    data = {
        'expirations': [exp_near, exp_far],
        'chain': {
            exp_near: {
                'calls': [{'strike': 100}],
                'puts': [{'strike': 100}],
            },
            exp_far: {
                'calls': [{'strike': 100}],
                'puts': [{'strike': 100}],
            },
        },
        'spot': 100.0,
    }

    result = _filter_option_chain(data, max_dte=30)
    assert exp_near in result['expirations']
    assert exp_far not in result['expirations']


def test_filter_moneyness():
    """Verify strikes outside moneyness range are excluded."""
    from app import _filter_option_chain

    today = datetime.now().date()
    exp = (today + timedelta(days=10)).strftime('%Y-%m-%d')

    data = {
        'expirations': [exp],
        'chain': {
            exp: {
                'calls': [
                    {'strike': 50},   # moneyness 0.5 → out
                    {'strike': 90},   # moneyness 0.9 → in
                    {'strike': 110},  # moneyness 1.1 → in
                    {'strike': 200},  # moneyness 2.0 → out
                ],
                'puts': [{'strike': 100}],
            },
        },
        'spot': 100.0,
    }

    result = _filter_option_chain(data, max_dte=30, moneyness_low=0.7, moneyness_high=1.3)
    calls = result['chain'][exp]['calls']
    strikes = [c['strike'] for c in calls]
    assert 90 in strikes
    assert 110 in strikes
    assert 50 not in strikes
    assert 200 not in strikes


def test_filter_compress_moneyness():
    """When total contracts exceed max_contracts, moneyness should narrow."""
    from app import _filter_option_chain

    today = datetime.now().date()
    exp = (today + timedelta(days=5)).strftime('%Y-%m-%d')

    # Generate many strikes
    calls = [{'strike': 70 + i} for i in range(60)]
    puts = [{'strike': 70 + i} for i in range(60)]

    data = {
        'expirations': [exp],
        'chain': {
            exp: {'calls': calls, 'puts': puts},
        },
        'spot': 100.0,
    }

    # With max_contracts=20, should narrow moneyness
    result = _filter_option_chain(data, max_dte=30, moneyness_low=0.7,
                                   moneyness_high=1.3, max_contracts=20)
    total = sum(len(d['calls']) + len(d['puts']) for d in result['chain'].values())
    assert total <= 20


def test_filter_no_spot():
    """No spot price → return data unmodified."""
    from app import _filter_option_chain

    data = {
        'expirations': ['2026-04-15'],
        'chain': {'2026-04-15': {'calls': [{'strike': 100}], 'puts': []}},
        'spot': None,
    }
    result = _filter_option_chain(data)
    assert result == data

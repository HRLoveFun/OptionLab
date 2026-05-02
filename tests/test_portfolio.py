"""Tests for portfolio attribution + tracked-strategies service."""

from __future__ import annotations

import os

os.environ.setdefault("RATE_LIMIT_DISABLED", "1")

from datetime import date, timedelta

import pytest

from core.portfolio import Position, aggregate_greeks, attribute_pnl
from core.strategies import long_call


def _pos(spot=100.0, days_ago=5):
    legs = long_call(strike=100, premium=3.0, dte=30, iv=0.25)
    return Position(
        ticker="AAPL",
        legs=legs,
        entry_date=date.today() - timedelta(days=days_ago),
        entry_spot=spot,
        entry_net_premium=300.0,
        qty=1,
    )


def test_aggregate_greeks_long_call_has_positive_delta():
    pos = _pos()
    agg = aggregate_greeks([pos], spots={"AAPL": 100.0})
    assert agg["net"]["delta"] > 0
    assert agg["net"]["vega"] > 0
    assert "AAPL" in agg["by_ticker"]


def test_aggregate_skips_missing_spot():
    pos = _pos()
    agg = aggregate_greeks([pos], spots={})
    assert agg["net"]["delta"] == 0
    assert agg["by_ticker"] == {}


def test_attribute_pnl_long_call_up_market():
    pos = _pos(spot=100.0, days_ago=5)
    out = attribute_pnl(pos, spot_now=110.0, today=date.today())
    assert out["delta_pnl"] > 0
    # Theta is negative for long options (time decay).
    assert out["theta_pnl"] < 0
    assert out["vega_pnl"] == 0  # No iv_now provided
    assert out["days_held"] == 5


def test_attribute_pnl_with_iv_drop_hurts_long_vega():
    pos = _pos()
    out = attribute_pnl(pos, spot_now=100.0, iv_now={0: 0.20}, today=date.today())
    # IV down 5 points on a long call → negative vega P&L
    assert out["vega_pnl"] < 0


def test_create_and_list_position():
    from data_pipeline.db import init_db
    from services.portfolio_service import create_position, list_positions

    init_db()
    res = create_position(
        {
            "ticker": "MSFT",
            "template": "long_call",
            "expiry": "2099-12-31",
            "entry_spot": 400.0,
            "entry_net_premium": 500.0,
            "qty": 1,
            "legs": [
                {"side": "long", "option_type": "call", "strike": 400, "premium": 5.0, "dte": 30, "iv": 0.25}
            ],
        }
    )
    assert res["status"] == "ok" and res["id"]
    rows = list_positions()
    assert any(r["ticker"] == "MSFT" for r in rows)


def test_create_position_rejects_missing_ticker():
    from services.portfolio_service import create_position
    from utils.api_errors import ApiError

    with pytest.raises(ApiError):
        create_position({"legs": [{"side": "long", "option_type": "call", "strike": 1, "premium": 1}]})


def test_portfolio_snapshot_uses_mocked_spots(monkeypatch):
    from data_pipeline.db import init_db
    from services import portfolio_service as ps

    init_db()
    ps.create_position(
        {
            "ticker": "TSLA",
            "template": "long_call",
            "expiry": "2099-12-31",
            "entry_spot": 250.0,
            "entry_net_premium": 700.0,
            "qty": 1,
            "legs": [
                {"side": "long", "option_type": "call", "strike": 250, "premium": 7.0, "dte": 30, "iv": 0.4}
            ],
        }
    )
    monkeypatch.setattr(ps, "fetch_spots_bulk", lambda ts: {"TSLA": 270.0})
    snap = ps.portfolio_snapshot()
    assert snap["status"] == "ok"
    pos0 = next(p for p in snap["positions"] if p["ticker"] == "TSLA")
    assert pos0["spot_now"] == 270.0
    assert pos0["pnl_attribution"]["delta_pnl"] > 0
    assert snap["aggregate"]["net"]["delta"] > 0

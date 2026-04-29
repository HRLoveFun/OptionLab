"""Tracked-strategies CRUD service.

Persists user-saved positions in ``tracked_strategies`` and computes live
P&L / aggregate Greeks across all open ones. The wire schema for a leg
mirrors :class:`core.strategies.Leg`: ``side / option_type / strike /
premium / qty / dte / iv``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from core.portfolio import Position, aggregate_greeks, attribute_pnl
from core.strategies import Leg
from data_pipeline.db import get_conn
from data_pipeline.yf_client import fetch_spots_bulk
from utils.api_errors import ApiError

logger = logging.getLogger(__name__)


def _legs_from_payload(raw: list[dict[str, Any]]) -> list[Leg]:
    if not isinstance(raw, list) or not raw:
        raise ApiError("legs must be a non-empty list", code="bad_legs")
    legs: list[Leg] = []
    for i, row in enumerate(raw):
        try:
            legs.append(
                Leg(
                    side=row["side"],
                    option_type=row["option_type"],
                    strike=float(row["strike"]),
                    premium=float(row["premium"]),
                    qty=int(row.get("qty", 1) or 1),
                    dte=int(row.get("dte", 30)),
                    iv=float(row.get("iv", 0.25)),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiError(f"leg {i} invalid: {exc}", code="bad_legs") from exc
    return legs


def _legs_to_json(legs: list[Leg]) -> str:
    return json.dumps([asdict(le) for le in legs])


def _legs_from_json(s: str) -> list[Leg]:
    return [Leg(**row) for row in json.loads(s)]


def create_position(payload: dict[str, Any]) -> dict[str, Any]:
    """Insert a new tracked position."""
    ticker = (payload.get("ticker") or "").strip().upper()
    if not ticker:
        raise ApiError("ticker is required", code="ticker_required")
    template = payload.get("template") or "custom"
    expiry = payload.get("expiry") or ""
    legs = _legs_from_payload(payload.get("legs", []))
    qty = int(payload.get("qty", 1) or 1)
    entry_spot = float(payload.get("entry_spot") or 0.0)
    entry_net_premium = float(payload.get("entry_net_premium") or 0.0)
    entry_date = payload.get("entry_date") or date.today().isoformat()
    notes = payload.get("notes")
    entry_meta = payload.get("entry_meta") or {}

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO tracked_strategies
              (ticker, template, expiry, entry_date, entry_spot,
               entry_net_premium, qty, legs_json, entry_meta_json,
               status, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ticker,
                template,
                expiry,
                entry_date,
                entry_spot,
                entry_net_premium,
                qty,
                _legs_to_json(legs),
                json.dumps(entry_meta),
                "open",
                notes,
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
    return {"status": "ok", "id": new_id}


def _row_to_dict(row, columns) -> dict[str, Any]:
    return {col: row[i] for i, col in enumerate(columns)}


def list_positions(status: str | None = "open") -> list[dict[str, Any]]:
    cols = (
        "id ticker template expiry entry_date entry_spot entry_net_premium "
        "qty legs_json entry_meta_json status notes closed_date closed_value"
    ).split()
    where = "WHERE status = ?" if status else ""
    params = (status,) if status else ()
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {', '.join(cols)} FROM tracked_strategies {where} ORDER BY id DESC",
            params,
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = _row_to_dict(r, cols)
        d["legs"] = _legs_from_json(d.pop("legs_json"))
        d["entry_meta"] = json.loads(d.pop("entry_meta_json") or "{}")
        out.append(d)
    return out


def close_position(position_id: int, closed_value: float) -> dict[str, Any]:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE tracked_strategies SET status='closed', closed_date=?, closed_value=? WHERE id=?",
            (date.today().isoformat(), float(closed_value), int(position_id)),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ApiError(f"position {position_id} not found", code="not_found", status=404)
    return {"status": "ok", "id": position_id}


def portfolio_snapshot() -> dict[str, Any]:
    """Return per-position P&L attribution + aggregate Greeks across all open positions.

    Spots are fetched in one bulk call. Per-leg current IV is NOT fetched
    (would multiply yfinance calls); attribution uses entry IV → vega term
    is zero unless caller supplied ``current_iv`` per leg in entry_meta.
    """
    rows = list_positions(status="open")
    if not rows:
        return {"status": "ok", "positions": [], "aggregate": {"net": {}, "by_ticker": {}}}

    tickers = sorted({r["ticker"] for r in rows})
    spots = fetch_spots_bulk(tickers)

    positions: list[Position] = []
    out_positions: list[dict[str, Any]] = []
    today = date.today()
    for r in rows:
        legs = r["legs"]
        try:
            entry_dt = date.fromisoformat(r["entry_date"])
        except ValueError:
            entry_dt = today
        pos = Position(
            ticker=r["ticker"],
            legs=legs,
            entry_date=entry_dt,
            entry_spot=float(r["entry_spot"] or 0.0),
            entry_net_premium=float(r["entry_net_premium"] or 0.0),
            qty=int(r["qty"] or 1),
        )
        positions.append(pos)
        spot_now = spots.get(r["ticker"])
        attr = None
        if spot_now is not None and pos.entry_spot > 0:
            attr = attribute_pnl(pos, spot_now=spot_now, today=today)
        out_positions.append(
            {
                "id": r["id"],
                "ticker": r["ticker"],
                "template": r["template"],
                "expiry": r["expiry"],
                "entry_date": r["entry_date"],
                "entry_spot": pos.entry_spot,
                "entry_net_premium": pos.entry_net_premium,
                "qty": pos.qty,
                "spot_now": spot_now,
                "legs": [asdict(le) for le in legs],
                "pnl_attribution": attr,
            }
        )

    agg = aggregate_greeks(positions, spots)
    return {
        "status": "ok",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "positions": out_positions,
        "aggregate": agg,
        "spots": spots,
    }

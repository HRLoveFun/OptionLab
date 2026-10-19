#!/usr/bin/env python3
"""optsim CLI: value and risk of a hypothetical option position over spot, time and IV.

Usage:
    python scripts/optsim.py docs/optsim/examples/spx_short_strangle.toml
    python scripts/optsim.py docs/optsim/examples/spy_short_put.toml --style european --margin pm

Reads a TOML scenario, prints a summary (legs, entry, margins, time profile at the
entry spot) and writes <out>/<name>.png and <out>/<name>.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.optsim import (  # noqa: E402
    Market,
    Position,
    Smile,
    breakevens,
    make_leg,
    option_greeks,
    render_grid_png,
    scenario_grid,
    strike_for_delta,
    time_profile,
)


def build(cfg: dict, style: str | None, product: str | None) -> tuple[Position, Market, dict]:
    style = style or cfg.get("style", "european")
    product = product or cfg.get("product", "index")
    m = cfg["market"]
    market = Market(spot=float(m["spot"]), rate=float(m.get("rate", 0.045)), div_yield=float(m.get("div_yield", 0.0)))
    smile = Smile(**cfg["smile"]) if "smile" in cfg else None
    legs = []
    for spec in cfg["legs"]:
        kind, dte = spec["type"], int(spec["dte"])
        if "strike" in spec:
            strike = float(spec["strike"])
        else:
            if smile is None:
                raise SystemExit("delta-selected legs need a [smile] table")
            strike = strike_for_delta(kind, float(spec["delta"]), dte, market, smile, spec.get("strike_step"))
        legs.append(
            make_leg(
                kind,
                spec.get("side", "long"),
                strike,
                dte,
                market,
                smile=smile,
                iv=spec.get("iv"),
                qty=int(spec.get("qty", 1)),
                style=style,
            )
        )
    position = Position(
        legs, style=style, multiplier=int(cfg.get("multiplier", 100)), product=product, name=cfg.get("name", "")
    )
    return position, market, cfg.get("grid", {})


def _fmt(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}"


def summarize(position: Position, market: Market, grid, binding: str) -> list[str]:
    out = [f"{position.name} | style {position.style} | product {position.product} | multiplier {position.multiplier}"]
    out.append(f"Market  S={_fmt(market.spot, 2)}  r={market.rate:.2%}  q={market.div_yield:.2%}")
    out.append("Legs")
    for leg in position.legs:
        g = option_greeks(
            leg.option_type,
            market.spot,
            leg.strike,
            leg.dte / 365,
            market.rate,
            market.div_yield,
            leg.iv,
            position.style,
        )
        out.append(
            f"  {leg.side:5s} {leg.qty} {leg.option_type:4s}  K={_fmt(leg.strike, 2):>10s}  {leg.dte:3d}d  "
            f"IV {leg.iv:6.2%}  premium {leg.premium:9.2f}  delta {float(g['delta']):+.3f}"
        )
    prof = time_profile(grid)
    flat = int(np.argmin(np.abs(grid.iv_shifts)))
    be = breakevens(grid.spots, grid.pnl[flat, -1])
    side = "net credit" if grid.entry_value < 0 else "net debit"
    out.append(
        f"Entry   {side} {_fmt(abs(grid.entry_value))}   breakevens at day {int(grid.days[-1])}: "
        + (" / ".join(_fmt(b, 1) for b in be) or "none in range")
    )
    regt, pm = prof[0]["regt"], prof[0]["pm"]
    bind = regt if binding == "regt" else pm
    rom = f"   max-profit return on margin {-grid.entry_value / bind:.1%}" if grid.entry_value < 0 and bind > 0 else ""
    out.append(f"Margin  Reg-T {_fmt(regt)} ({prof[0]['regt_method']})   PM {_fmt(pm)}   binding: {binding}{rom}")
    out.append(f"Time profile at S={_fmt(market.spot, 2)}, IV unchanged")
    head = f"{'day':>5} {'value':>11} {'P&L':>10} {'delta':>9} {'gamma':>9} {'theta/d':>9} {'vega/vp':>9} {'Reg-T':>10} {'PM':>10}"
    out.append(head)
    for r in prof:
        out.append(
            f"{r['day']:5.0f} {_fmt(r['value']):>11} {_fmt(r['pnl']):>10} {r['delta']:9.2f} {r['gamma']:9.4f} "
            f"{r['theta']:9.1f} {r['vega']:9.1f} {_fmt(r['regt']):>10} {_fmt(r['pm']):>10}"
        )
    shifts = [
        f"IV {s * 100:+.0f}vp: {_fmt(grid.pnl[v, 0, grid.base_index])}" for v, s in enumerate(grid.iv_shifts) if s != 0
    ]
    if shifts:
        out.append("P&L at entry spot under IV shifts   " + "   ".join(shifts))
    return out


def to_json(position: Position, market: Market, grid) -> dict:
    r = lambda a, nd=2: np.round(np.asarray(a, dtype=float), nd).tolist()  # noqa: E731
    return {
        "name": position.name,
        "style": position.style,
        "product": position.product,
        "multiplier": position.multiplier,
        "market": vars(market),
        "legs": [vars(leg) for leg in position.legs],
        "entry_value": grid.entry_value,
        "spots": r(grid.spots),
        "days": r(grid.days, 0),
        "iv_shifts": r(grid.iv_shifts, 4),
        "profile": time_profile(grid),
        "grid": {k: r(getattr(grid, k), 4) for k in ("pnl", "delta", "gamma", "theta", "vega", "regt")},
        "pm_at_entry_spot": r(grid.pm),
        "regt_method": grid.regt_method,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("config", type=Path)
    ap.add_argument("--style", choices=("european", "american"), help="override the exercise style")
    ap.add_argument(
        "--product", choices=("index", "etf", "index_small", "equity"), help="override the margin product class"
    )
    ap.add_argument("--margin", choices=("regt", "pm"), help="binding margin regime for the summary")
    ap.add_argument("--out", type=Path, default=Path("data/optsim"))
    args = ap.parse_args(argv)

    cfg = tomllib.loads(args.config.read_text(encoding="utf-8"))
    position, market, grid_cfg = build(cfg, args.style, args.product)
    grid = scenario_grid(
        position,
        market,
        spot_range=float(grid_cfg.get("spot_range", 0.15)),
        n_spots=int(grid_cfg.get("n_spots", 61)),
        days=grid_cfg.get("days"),
        iv_shifts=tuple(grid_cfg.get("iv_shifts", (-0.05, 0.0, 0.05))),
    )
    binding = args.margin or grid_cfg.get("margin", "regt")
    print("\n".join(summarize(position, market, grid, binding)))

    args.out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", (position.name or args.config.stem).lower()).strip("-") + f"-{position.style}"
    (args.out / f"{slug}.png").write_bytes(render_grid_png(grid))
    (args.out / f"{slug}.json").write_text(json.dumps(to_json(position, market, grid), indent=1), encoding="utf-8")
    print(f"Wrote {args.out / (slug + '.png')} and {args.out / (slug + '.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

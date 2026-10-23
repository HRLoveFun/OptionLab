"""Margin requirements: Reg-T (strategy-based) and portfolio margin (risk-based).

Domain:    Option Simulation — Margin
Context:
  - Both functions return buying-power reduction (BPR) in dollars: the capital
    a position ties up beyond the premium it received. Reg-T lets short-option
    proceeds count toward the requirement, so a naked short needs
    max(pct·S − OTM, 10%) and a credit spread needs width − credit; under
    portfolio margin the requirement is the worst modelled loss.
  - Reg-T covers three cases exactly or conservatively:
      defined_risk  every short covered by a long of the same type that expires
                    no earlier (verticals, condors, butterflies, calendars, long options)
      naked         no long legs (short puts/calls, straddles, strangles)
      conservative  anything else: each side priced alone, uncovered shorts as naked
    A long that expires before the short it would cover covers nothing: a reverse
    calendar (short far, long near) is margined as a naked short plus a long.
  - Portfolio margin is a TIMS-style proxy: revalue the position at 10 equidistant
    spot points (IV and time held fixed) and take the largest loss, floored at
    0.375 × multiplier per contract. Broker house add-ons are not modelled.
  - ``margin_class`` picks the product rule for a listed underlying from its
    instrument type (the ticker mode of the Position Simulator).
Contracts:
  - PRODUCTS: dict[str, ProductRule]
  - margin_class(symbol, instrument_type) -> str   # a PRODUCTS key
  - regt_bpr(kinds, strikes, qtys, values, spot, multiplier, product, dtes=None) -> (np.ndarray, str)
  - pm_offsets(product) -> np.ndarray   # 11 spot offsets, index 0 is the unshocked point
  - pm_bpr(values_at_offsets, n_contracts, multiplier, all_long) -> np.ndarray
Dependencies UPWARD:
  - numpy
Dependencies DOWNWARD:
  - core.optsim.engine, services.options.optsim_ticker, tests
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProductRule:
    naked_pct: float
    pm_range: tuple[float, float]


# DOMAIN: Cboe strategy-based margin — short uncovered options carry 15% of the underlying
# for broad-based indexes and ETFs tracking them, 20% for equities, with a 10% minimum.
# DOMAIN: customer portfolio margin (Cboe / FINRA) — high-cap broad-based index range
# -8%/+6% (Cboe applies it to SPY too), other broad-based ±10%, equities ±15%.
PRODUCTS: dict[str, ProductRule] = {
    "index": ProductRule(0.15, (-0.08, 0.06)),
    "etf": ProductRule(0.15, (-0.08, 0.06)),
    "index_small": ProductRule(0.15, (-0.10, 0.10)),
    "equity": ProductRule(0.20, (-0.15, 0.15)),
}

# DOMAIN: Reg-T minimum on a naked short: 10% of the underlying (calls) or of the strike (puts).
_NAKED_FLOOR = 0.10

# DOMAIN: portfolio-margin minimum charge per contract, times the contract multiplier.
_PM_MIN_PER_CONTRACT = 0.375


# DOMAIN: high-capitalization broad-based indexes (S&P 500, Mini-SPX, Nasdaq-100 and its micro
# version, the Dow, S&P 100) — the -8%/+6% portfolio-margin range — and the ETFs that track them.
HIGH_CAP_INDEXES = frozenset({"^SPX", "^GSPC", "^XSP", "^NDX", "^XND", "^DJX", "^DJI", "^OEX", "^XEO"})
HIGH_CAP_INDEX_ETFS = frozenset({"SPY", "IVV", "VOO", "SPLG", "QQQ", "QQQM", "DIA", "OEF"})
# DOMAIN: ETFs on other broad-based indexes (Russell 2000, S&P MidCap 400 / SmallCap 600): 15%, ±10%.
OTHER_BROAD_INDEX_ETFS = frozenset({"IWM", "MDY", "IJH", "IJR"})


def margin_class(symbol: str, instrument_type: str | None) -> str:
    """The ``PRODUCTS`` key for a listed underlying, from its symbol and instrument type.

    The named broad-based indexes and ETFs above settle it by symbol, so a failed
    type lookup cannot demote SPY. Otherwise the type decides: any other index
    (``^`` symbols count as indexes) is ``index_small``; any other ETF (sector,
    leveraged, single-country) is ``equity``, because options on narrow-based ETFs
    carry the equity requirement; stocks and unknown types are ``equity``, the most
    conservative class.
    """
    sym = str(symbol or "").strip().upper()
    if sym in HIGH_CAP_INDEXES:
        return "index"
    if sym in HIGH_CAP_INDEX_ETFS:
        return "etf"
    if sym in OTHER_BROAD_INDEX_ETFS:
        return "index_small"
    if instrument_type == "index" or sym.startswith("^"):
        return "index_small"
    return "equity"


def _rule(product: str) -> ProductRule:
    if product not in PRODUCTS:
        raise ValueError(f"product must be one of {sorted(PRODUCTS)}, got {product!r}")
    return PRODUCTS[product]


def _max_intrinsic_loss(is_call: np.ndarray, strikes: np.ndarray, qtys: np.ndarray) -> float:
    """Largest expiry loss (per share × contracts) from netting intrinsic values across strikes."""
    if qtys.size == 0:
        return 0.0
    grid = np.unique(np.concatenate([[0.0], strikes, [2.0 * strikes.max() + 1.0]]))
    intrinsic = np.where(is_call[:, None], grid[None, :] - strikes[:, None], strikes[:, None] - grid[None, :])
    payoff = (qtys[:, None] * np.maximum(intrinsic, 0.0)).sum(axis=0)
    return max(0.0, -float(payoff.min()))


def _naked_base(is_call, strikes, spot, pct):
    """Per-share Reg-T charge beyond the premium for each leg if it were a naked short."""
    otm = np.where(is_call[:, None], np.maximum(strikes[:, None] - spot, 0.0), np.maximum(spot - strikes[:, None], 0.0))
    floor = _NAKED_FLOOR * np.where(is_call[:, None], spot, strikes[:, None])
    return np.maximum(pct * spot - otm, floor)


def _covered(qtys: np.ndarray, dtes: np.ndarray, side: np.ndarray) -> bool:
    """Every short contract on ``side`` has a long on ``side`` expiring no earlier.

    Hall's condition for this ordering: at every short expiry t, the longs expiring
    on or after t must number at least the shorts expiring on or after t.
    """
    shorts, longs = side & (qtys < 0), side & (qtys > 0)
    return all(qtys[longs & (dtes >= t)].sum() >= -qtys[shorts & (dtes >= t)].sum() for t in np.unique(dtes[shorts]))


def regt_bpr(kinds, strikes, qtys, values, spot, multiplier: int, product: str, dtes=None) -> tuple[np.ndarray, str]:
    """Reg-T buying-power reduction in dollars over the cells of ``spot``.

    ``values`` has shape (n_legs, n_cells): current option value per share;
    ``qtys`` are signed contract counts (+long, −short); ``dtes`` are the legs'
    days to expiry, which decide what can cover what (all equal when omitted).
    """
    pct = _rule(product).naked_pct
    is_call = np.array([k == "call" for k in kinds])
    strikes = np.asarray(strikes, dtype=float)
    qtys = np.asarray(qtys, dtype=float)
    dtes = np.zeros(len(qtys)) if dtes is None else np.asarray(dtes, dtype=float)
    spot = np.atleast_1d(np.asarray(spot, dtype=float))
    values = np.asarray(values, dtype=float).reshape(len(qtys), -1)
    short, long_ = qtys < 0, qtys > 0
    n_short = {c: -qtys[(is_call == c) & short].sum() for c in (True, False)}
    n_long = {c: qtys[(is_call == c) & long_].sum() for c in (True, False)}
    covered = {c: _covered(qtys, dtes, is_call == c) for c in (True, False)}

    def defined(mask):
        loss = _max_intrinsic_loss(is_call[mask], strikes[mask], qtys[mask])
        return np.maximum(loss + (qtys[mask, None] * values[mask]).sum(axis=0), 0.0)

    base = _naked_base(is_call, strikes, spot, pct)
    if all(covered.values()):
        bpr, method = defined(np.ones(len(qtys), dtype=bool)), "defined_risk"
    elif n_long[True] + n_long[False] == 0:
        req = {
            c: (-qtys[(is_call == c) & short, None] * (values + base)[(is_call == c) & short]).sum(axis=0)
            for c in (True, False)
        }
        prem = {
            c: (-qtys[(is_call == c) & short, None] * values[(is_call == c) & short]).sum(axis=0) for c in (True, False)
        }
        if n_short[True] > 0 and n_short[False] > 0:
            # DOMAIN: short straddle/strangle — the greater side's requirement plus the other side's premium.
            total = np.where(req[True] >= req[False], req[True] + prem[False], req[False] + prem[True])
        else:
            total = req[True] + req[False]
        bpr, method = total - prem[True] - prem[False], "naked"
    else:
        bpr, method = np.zeros_like(spot), "conservative"
        for c in (True, False):
            side = is_call == c
            if n_short[c] == 0:
                bpr = bpr + (qtys[side, None] * values[side]).sum(axis=0)
            elif covered[c]:
                bpr = bpr + defined(side)
            else:
                shorts, longs = side & short, side & long_
                bpr = (
                    bpr
                    + (-qtys[shorts, None] * base[shorts]).sum(axis=0)
                    + (qtys[longs, None] * values[longs]).sum(axis=0)
                )
    return bpr * multiplier, method


def pm_offsets(product: str) -> np.ndarray:
    """Unshocked point followed by 10 equidistant spot offsets (5 down, 5 up)."""
    lo, hi = _rule(product).pm_range
    return np.concatenate([[0.0], np.linspace(lo, 0.0, 6)[:-1], np.linspace(0.0, hi, 6)[1:]])


def pm_bpr(values_at_offsets, n_contracts: float, multiplier: int, all_long: bool = False) -> np.ndarray:
    """Portfolio-margin requirement from position values (dollars) at ``pm_offsets`` (last axis)."""
    v = np.asarray(values_at_offsets, dtype=float)
    loss = np.maximum(v[..., :1] - v.min(axis=-1, keepdims=True), 0.0)[..., 0]
    minimum = _PM_MIN_PER_CONTRACT * multiplier * n_contracts
    if all_long:
        minimum = np.minimum(minimum, np.maximum(v[..., 0], 0.0))
    return np.maximum(loss, minimum)

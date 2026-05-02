"""Liquidity scoring for single option contracts.

Domain:    Options Analysis — Liquidity
Contracts:
  - liquidity_score(strike, bid, ask, last, oi, volume, spot) -> tuple[str, str]
Dependencies UPWARD:
  - None
Dependencies DOWNWARD:
  - services.options_chain_service
"""

from __future__ import annotations


def liquidity_score(
    strike: float | None,
    bid: float | None,
    ask: float | None,
    last: float | None,
    oi: float | None,
    volume: float | None,
    spot: float | None,
) -> tuple[str, str]:
    """Classify liquidity as GOOD / FAIR / AVOID.

    Returns (label, reason).
    """
    issues: list[str] = []
    bid_ = bid if (bid and bid > 0) else None
    ask_ = ask if (ask and ask > 0) else None
    if bid_ is not None and ask_ is not None:
        mid = (bid_ + ask_) / 2
        spread_pct = (ask_ - bid_) / mid if mid > 0 else 1.0
        if spread_pct > 0.20:
            issues.append(f"spread {spread_pct:.0%}")
    else:
        issues.append("spread N/A")
    oi_ = int(oi) if oi else 0
    if oi_ < 100:
        issues.append(f"OI={oi_}")
    vol_ = int(volume) if volume else 0
    if vol_ < 10:
        issues.append(f"Vol={vol_}")
    if spot and spot > 0 and strike:
        m = strike / spot
        if m < 0.75 or m > 1.35:
            issues.append("strike far from spot")
    if not issues:
        return "GOOD", ""
    if len(issues) == 1:
        return "FAIR", issues[0]
    return "AVOID", " | ".join(issues[:2])

"""Filter and rank candidates.

Domain:    Option Decision — Filter & Rank
Contracts:
  - select_dte_range(vol_timing, time_horizon_days) -> tuple[int, int]
  - filter_and_rank(enriched, min_dte, max_dte, min_ev, min_vt) -> list[dict]
  - get_heuristic_notes(...) -> list[str]
Dependencies UPWARD:
  - None
Dependencies DOWNWARD:
  - services (orchestrator)
"""

from __future__ import annotations

MIN_EV_THRESHOLD: float = 0.0
MIN_VEGA_THETA: float = 2.0


def select_dte_range(vol_timing: str, time_horizon_days: int) -> tuple[int, int]:
    vol_timing = vol_timing.upper()
    if vol_timing == "FAST":
        return (time_horizon_days, time_horizon_days + 14)
    elif vol_timing == "MEDIUM":
        return (time_horizon_days, time_horizon_days + 30)
    else:
        return (time_horizon_days + 14, time_horizon_days + 60)


def filter_and_rank(
    enriched: list[dict],
    min_dte: int,
    max_dte: int,
    min_ev: float = MIN_EV_THRESHOLD,
    min_vt: float = MIN_VEGA_THETA,
) -> list[dict]:
    filtered = []
    for c in enriched:
        if not (min_dte <= c["dte"] <= max_dte):
            continue
        if c.get("ev", -1) < min_ev:
            continue
        if c["derived"]["vega_theta_ratio"] < min_vt:
            continue
        if c["derived"]["contracts_n"] < 1:
            continue
        filtered.append(c)
    filtered.sort(key=lambda c: (-c.get("ev_ratio", 0), -c["derived"]["vega_theta_ratio"]))
    return filtered


def get_heuristic_notes(
    directional_conviction: float, vol_conviction: float, vol_timing: str, iv_rank: float | None
) -> list[str]:
    notes: list[str] = []
    if directional_conviction > vol_conviction:
        notes.append("Directional conviction dominates → prefer higher |delta| (0.50–0.70) and shorter DTE.")
    elif vol_conviction > directional_conviction:
        notes.append("Vol conviction dominates → prefer ATM (delta 0.40–0.50), longer DTE, high vega/theta ratio.")
    if vol_timing.upper() == "FAST" and iv_rank is not None and iv_rank < 30:
        notes.append("Vol is cheap + fast timing → lean OTM / short DTE for cheap convexity.")
    if iv_rank is not None and iv_rank > 70:
        notes.append("IV Rank > 70 — vol is expensive; require higher EV ratio before entering.")
    return notes

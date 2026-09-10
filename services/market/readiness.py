"""Readiness on submit: plan the stored datasets and warm the live snapshots.

Domain:    Market Analysis — Readiness
Context:
  - ADR 0012 / batch B5. ``routes/core.py::index`` calls this right after
    validation: the data_pipeline half plans + kicks the stored datasets, and the
    services half warms ``services.options.preload`` so switching to a live option
    tab is instant instead of a cold ~2 s fetch.
  - WHY the split: ``data_pipeline.orchestrate`` may not import ``services``
    (ADR 0001), and warming an option chain *is* a service concern.
Constraints:
  - CONSTRAINT (docs/constraints.md §6): nothing here blocks on the network. The
    preload warm runs on a daemon thread, so ``POST /`` still returns the
    skeleton in < 1 s and a failed warm is invisible to the user.
Contracts:
  - ``prepare_readiness(tickers, modules, *, start, end) -> list[ReadinessStatus]``
  - ``warm_live_snapshots(tickers) -> None`` — fire-and-forget
Dependencies UPWARD:
  - data_pipeline.orchestrate.readiness (plan + kick), services.options.preload
Dependencies DOWNWARD:
  - routes/core.py
"""

from __future__ import annotations

import datetime as dt
import logging
import threading

from data_pipeline.orchestrate.readiness import (
    KIND_DATASETS,
    ReadinessStatus,
    check_and_kick,
    plan_datasets,
)

logger = logging.getLogger(__name__)

# INVARIANT: modules whose first paint needs a live option-chain snapshot
# (ADR 0004 — never persisted), so the only useful prefetch is the in-process
# preload cache.
LIVE_CHAIN_MODULES = frozenset({"options_chain", "payoff_ratio"})


def prepare_readiness(
    tickers: list[str],
    modules: list[str],
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
) -> list[ReadinessStatus]:
    """Plan + kick the stored datasets, then warm the live snapshots.

    Returns the per-request statuses so the caller can store them on the job and
    ``/render/<kind>`` can tell "covered" from "still downloading".
    """
    plan = plan_datasets(tickers, modules, start=start, end=end)
    if not plan:
        logger.info("readiness: no stored dataset required for modules=%s", modules)
    statuses = check_and_kick(plan)
    if LIVE_CHAIN_MODULES & set(modules):
        warm_live_snapshots(tickers)
    return statuses


def warm_live_snapshots(tickers: list[str]) -> None:
    """Warm the option-chain preload cache for ``tickers`` on daemon threads."""
    for ticker in tickers:
        threading.Thread(target=_warm_one, args=(ticker,), daemon=True).start()


def _warm_one(ticker: str) -> None:
    try:
        from services.options.preload import build_preload_payload, get_cached, set_cached

        if get_cached(ticker) is not None:
            return
        set_cached(ticker, build_preload_payload(ticker))
        logger.info("readiness: warmed option-chain preload for %s", ticker)
    except Exception as exc:  # noqa: BLE001 — a warm is best-effort by definition
        logger.debug("readiness: preload warm failed for %s: %s", ticker, exc)


def modules_needing_live_chain(modules: list[str]) -> bool:
    """True when any requested module needs a live option-chain snapshot."""
    return bool(LIVE_CHAIN_MODULES & set(modules))


__all__ = [
    "KIND_DATASETS",
    "LIVE_CHAIN_MODULES",
    "ReadinessStatus",
    "modules_needing_live_chain",
    "prepare_readiness",
    "warm_live_snapshots",
]

"""Data-readiness planning and prefetch (ADR 0012).

Domain:    Data Pipeline — Orchestrate (readiness)
Context:
  - Before batch B5, ``POST /`` computed nothing and each ``/render/<kind>``
    discovered missing coverage on its own, so whichever tab the user opened
    first paid for the whole backfill. This module turns that implicit per-slice
    decision into an explicit plan: given the ticker(s) and the modules the user
    asked for, work out which datasets they need, probe the DB once, and kick the
    missing ranges immediately.
  - The module → dataset map is static and lives here so the route never has to
    know which slice touches which table.
Constraints:
  - CONSTRAINT (docs/constraints.md §6): no job queue. Coverage probes are
    DB-only — never network on the request thread — and a missing range is kicked
    on a daemon thread. ``check_and_kick`` therefore cannot block for more than a
    probe, so ``POST /`` still returns the skeleton in < 1 s.
  - INVARIANT: one pipeline run (download → clean → process) fills both
    ``clean_bars`` and ``feature_bars``, so a single kick per (ticker, range)
    covers every dataset the plan asked for. The probe (``backfill.needs_backfill``)
    checks *both* families — clean coverage **and** a feature-bars lag — so a DB
    with clean rows but stale features is still healed (plan §10 F4).
Contracts:
  - ``plan_datasets(tickers, modules, *, start, end, today=None)``
  - ``check_and_kick(plan, *, kick=None)``
  - ``dataset_for_module(module)`` / ``status_for(plan, ticker, module)``
  - ``kick_backfill(ticker, start, end)`` / ``join_backfills(timeout=None)``
Dependencies UPWARD:
  - data_pipeline.orchestrate.backfill, data_pipeline.store.db
Dependencies DOWNWARD:
  - routes/core.py (through services/market/readiness.py),
    data_pipeline/read/_query.py
"""

from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# INVARIANT: module token (the same token ``/render/<kind>`` and the sidebar use)
# → the datasets that module reads. A module with no DB dependency maps to ().
KIND_DATASETS: dict[str, tuple[str, ...]] = {
    "market_review": ("clean_bars",),
    "statistical": ("feature_bars",),
    "assessment": ("feature_bars",),
    # The volatility slice renders the HV context next to the live chain, so it
    # needs daily bars as well as the live snapshot.
    "options_chain": ("clean_bars",),
    # Live-only modules: no stored dataset to prefetch (ADR 0004).
    "payoff_ratio": (),
    "regime": (),
    "simulation": (),
    "option_pricing_matrix": (),
}

ALL_MODULES: tuple[str, ...] = tuple(KIND_DATASETS)

# DOMAIN: default lookback when the caller does not pass a horizon. Mirrors the
# direct-URL bootstrap default in services/market/dispatch.py (2 years).
DEFAULT_LOOKBACK_DAYS = 365 * 2

# DOMAIN: how long /render/<kind> will hold a tab in the "data is being
# prepared" state (cold start only) before falling back to computing with
# whatever coverage exists. Bounded so a stuck backfill degrades into the normal
# (graceful) slice error instead of an endless spinner.
HOLD_SECONDS = 30.0


@dataclass(frozen=True)
class DatasetRequest:
    """One (ticker, dataset) the requested modules will need."""

    ticker: str
    dataset: str
    start: dt.date
    end: dt.date
    module: str


@dataclass(frozen=True)
class ReadinessStatus:
    """Outcome of the coverage probe for one request.

    ``kicked_at`` is a ``time.monotonic()`` stamp (0.0 when nothing was kicked);
    it lives on the status so ``hold_seconds_left`` needs no extra bookkeeping.
    ``has_data`` distinguishes a **cold start** (no rows at all — nothing to show
    yet, worth holding the tab for) from a **partial gap** (usable history exists,
    so the tab should render now and let the backfill catch up behind it).
    """

    ticker: str
    dataset: str
    module: str
    state: str  # "covered" | "kicked"
    kicked_at: float = field(default=0.0)
    has_data: bool = True
    # The (ticker, range) that was probed/kicked — used to ask whether the
    # backfill is still running (see should_hold).
    start: dt.date | None = None
    end: dt.date | None = None


def dataset_for_module(module: str) -> str | None:
    """Return the first dataset ``module`` reads, or None when it is live-only."""
    datasets = KIND_DATASETS.get(module) or ()
    return datasets[0] if datasets else None


def plan_datasets(
    tickers: list[str],
    modules: list[str],
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    today: dt.date | None = None,
) -> list[DatasetRequest]:
    """Union over the requested modules, one entry per (ticker, dataset).

    ORDER: preserves the module order the caller passed and, inside a module, the
    ticker order — so the caller can prioritise ``tickers[0]`` downstream.
    """
    today = today or dt.date.today()
    end = end or today
    start = start or (end - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS))
    requests: list[DatasetRequest] = []
    seen: set[tuple[str, str]] = set()
    for module in modules:
        for dataset in KIND_DATASETS.get(module, ()):
            for ticker in tickers:
                key = (ticker, dataset)
                if key in seen:
                    continue
                seen.add(key)
                requests.append(DatasetRequest(ticker=ticker, dataset=dataset, start=start, end=end, module=module))
    return requests


def check_and_kick(plan: list[DatasetRequest], *, kick=None) -> list[ReadinessStatus]:
    """Probe coverage per (ticker, range) and kick the missing ones.

    ``kick`` is injectable so tests can assert the decision without starting
    threads. Returns one status per request, in plan order.
    """
    from data_pipeline.orchestrate import backfill as _bf

    kick = kick or kick_backfill
    statuses: list[ReadinessStatus] = []
    for ticker, group in _by_ticker(plan):
        start = min(req.start for req in group)
        end = max(req.end for req in group)
        try:
            missing = _bf.needs_backfill(ticker, start, end)
        except Exception as exc:  # noqa: BLE001 — a probe must never break the POST
            logger.warning("readiness probe failed for %s: %s", ticker, exc)
            missing = False
        kicked_at = 0.0
        has_data = True
        if missing:
            has_data = _has_any_prices(ticker)
            kicked_at = time.monotonic()
            kick(ticker, start, end)
        state = "kicked" if missing else "covered"
        statuses.extend(
            ReadinessStatus(
                ticker=req.ticker,
                dataset=req.dataset,
                module=req.module,
                state=state,
                kicked_at=kicked_at,
                has_data=has_data,
                start=start,
                end=end,
            )
            for req in group
        )
    if statuses:
        logger.info(
            "readiness: %d request(s) — %d covered, %d kicked",
            len(statuses),
            sum(1 for s in statuses if s.state == "covered"),
            sum(1 for s in statuses if s.state == "kicked"),
        )
    return statuses


def status_for(plan: list[ReadinessStatus] | None, ticker: str, module: str) -> ReadinessStatus | None:
    """Return the plan entry for ``(ticker, module)``, or None when not planned."""
    dataset = dataset_for_module(module)
    if dataset is None or not plan:
        return None
    for status in plan:
        if status.ticker == ticker and status.dataset == dataset:
            return status
    return None


def hold_seconds_left(status: ReadinessStatus | None, *, now: float | None = None) -> float | None:
    """Seconds ``/render/*`` should keep holding this tab, or None to compute now.

    Holds only on a **cold start** (``has_data`` False): with usable history the tab
    should paint immediately while the backfill fills the tail, which is what the
    per-slice grace period already does.

    WHY bounded: an unbounded hold would spin forever if the backfill failed; after
    HOLD_SECONDS the caller computes with whatever coverage exists and the slice's
    own graceful-degradation path takes over.
    """
    if status is None or status.state != "kicked" or status.has_data or not status.kicked_at:
        return None
    remaining = HOLD_SECONDS - ((now if now is not None else time.monotonic()) - status.kicked_at)
    return remaining if remaining > 0 else None


def is_backfill_running(status: ReadinessStatus) -> bool:
    """True when the daemon-thread backfill kicked for this entry is still alive."""
    if status.start is None or status.end is None:
        return False
    key = (status.ticker, str(status.start), str(status.end))
    with _backfill_lock:
        thread = _backfill_threads.get(key)
    return thread is not None and thread.is_alive()


def should_hold(status: ReadinessStatus | None, *, now: float | None = None) -> bool:
    """Should ``/render/<kind>`` wait for data instead of computing now?

    Holds only while (a) this was a cold start, (b) the HOLD_SECONDS window has not
    elapsed, and (c) the backfill thread is **still running**. (c) is what keeps a
    failed download honest: once the thread dies the tab stops claiming to be
    "preparing data" and the slice reports the real outcome (its own error).
    """
    if hold_seconds_left(status, now=now) is None:
        return False
    return is_backfill_running(status)


def _has_any_prices(ticker: str) -> bool:
    """True when the DB already holds at least one priced row for ``ticker``."""
    try:
        from data_pipeline.store.repos import count_clean_rows

        return count_clean_rows(ticker) > 0
    except Exception as exc:  # noqa: BLE001 — a probe must never break the POST
        logger.debug("readiness: existing-data probe failed for %s: %s", ticker, exc)
        return True


def _by_ticker(plan: list[DatasetRequest]) -> list[tuple[str, list[DatasetRequest]]]:
    """Group a plan by ticker, preserving first-appearance order."""
    order: list[str] = []
    groups: dict[str, list[DatasetRequest]] = {}
    for req in plan:
        if req.ticker not in groups:
            groups[req.ticker] = []
            order.append(req.ticker)
        groups[req.ticker].append(req)
    return [(t, groups[t]) for t in order]


# ── Daemon-thread backfill kicker ───────────────────────────────────────────
# WHY it lives here and not in read/: `read` imports `orchestrate` (the read path
# triggers refreshes), so orchestrate may not import read. Both callers now share
# this one kicker instead of read keeping a private copy.
_backfill_lock = threading.Lock()
_backfill_threads: dict[tuple, threading.Thread] = {}


def kick_backfill(ticker: str, start: dt.date, end: dt.date) -> None:
    """Start a daemon-thread backfill for ``[start, end]`` unless one is running.

    The in-flight map is the same de-duplication ``ensure_range`` applies
    internally, hoisted to the thread level so a POST that fans out over N
    tickers cannot start N copies of the same work.
    """
    key = (ticker, str(start), str(end))
    with _backfill_lock:
        existing = _backfill_threads.get(key)
        if existing is not None and existing.is_alive():
            return
        t = threading.Thread(target=_run_backfill, args=(ticker, start, end, key), daemon=True)
        _backfill_threads[key] = t
        t.start()
    logger.info("background backfill kicked for %s [%s .. %s]", ticker, start, end)


def _run_backfill(ticker: str, start: dt.date, end: dt.date, key: tuple) -> None:
    from data_pipeline.orchestrate import backfill as _bf

    try:
        _bf.ensure_range(ticker, start, end)
    except Exception as e:  # noqa: BLE001
        logger.warning("background backfill failed for %s: %s", ticker, e)
    finally:
        # Daemon threads never run dispatch's finally-cleanups; drop this
        # thread's SQLite connection so _all_conns doesn't grow per backfill.
        from data_pipeline.store.db import close_thread_conn

        close_thread_conn()
        with _backfill_lock:
            _backfill_threads.pop(key, None)


def join_backfills(timeout: float | None = None) -> None:
    """Test helper: wait for all in-flight background backfills."""
    with _backfill_lock:
        threads = list(_backfill_threads.values())
    for t in threads:
        t.join(timeout=timeout)

"""Readiness planning + prefetch on submit (ADR 0012, batch B5).

Domain:    Tests — Data Readiness
Context:
  - B5 turned the implicit, per-slice "discover missing coverage when the tab
    loads" flow into an explicit plan computed at POST time. These tests pin the
    plan union, the kick decision, the cold-start hold window, and the fact that a
    kick really does populate the DB.
Contracts:
  - ``plan_datasets`` is the union over the requested modules, one entry per
    (ticker, dataset), with live-only modules contributing nothing.
  - ``check_and_kick`` probes once per (ticker, range) and kicks exactly the
    missing ones.
  - ``hold_seconds_left`` holds only on a cold start and only for HOLD_SECONDS.
  - ``create_job`` stores the plan; ``FormService.extract_modules`` defaults to
    every known module and ignores unknown tokens.
Dependencies UPWARD:
  - (none — stdlib + pytest + the packages under test)
"""

from __future__ import annotations

import datetime as dt
import threading

import pytest

from data_pipeline.orchestrate import backfill as _bf
from data_pipeline.orchestrate import readiness
from data_pipeline.orchestrate.job_cache import _reset as reset_jobs
from data_pipeline.orchestrate.job_cache import create_job, get_job
from data_pipeline.store.db import fetch_df, init_db

TODAY = dt.date(2026, 9, 10)


# ---------------------------------------------------------------------------
# plan_datasets
# ---------------------------------------------------------------------------
def test_plan_datasets_is_the_union_over_modules():
    plan = readiness.plan_datasets(["AAPL"], ["market_review", "assessment"], today=TODAY)
    pairs = {(r.ticker, r.dataset) for r in plan}
    assert pairs == {("AAPL", "clean_bars"), ("AAPL", "feature_bars")}
    assert {r.module for r in plan} == {"market_review", "assessment"}


def test_plan_datasets_dedupes_a_dataset_shared_by_two_modules():
    """market_review and options_chain both read clean_bars → one entry."""
    plan = readiness.plan_datasets(["AAPL"], ["market_review", "options_chain"], today=TODAY)
    assert len(plan) == 1
    assert plan[0].dataset == "clean_bars"
    assert plan[0].module == "market_review"  # first module wins (documented)


def test_plan_datasets_covers_every_ticker():
    plan = readiness.plan_datasets(["AAPL", "MSFT"], ["statistical"], today=TODAY)
    assert {r.ticker for r in plan} == {"AAPL", "MSFT"}
    assert all(r.dataset == "feature_bars" for r in plan)


def test_plan_datasets_is_empty_for_live_only_modules():
    assert readiness.plan_datasets(["AAPL"], ["regime", "payoff_ratio", "simulation"], today=TODAY) == []


def test_plan_datasets_horizon_defaults_and_overrides():
    default = readiness.plan_datasets(["AAPL"], ["statistical"], today=TODAY)[0]
    assert default.end == TODAY
    assert default.start == TODAY - dt.timedelta(days=readiness.DEFAULT_LOOKBACK_DAYS)

    explicit = readiness.plan_datasets(
        ["AAPL"], ["statistical"], start=dt.date(2020, 1, 1), end=dt.date(2021, 1, 1), today=TODAY
    )[0]
    assert (explicit.start, explicit.end) == (dt.date(2020, 1, 1), dt.date(2021, 1, 1))


# ---------------------------------------------------------------------------
# check_and_kick
# ---------------------------------------------------------------------------
def test_check_and_kick_kicks_missing_ranges_once_per_ticker(monkeypatch):
    init_db()
    monkeypatch.setattr(_bf, "needs_backfill", lambda ticker, start, end: True)
    kicked: list[tuple] = []
    plan = readiness.plan_datasets(["AAPL", "MSFT"], ["market_review", "statistical"], today=TODAY)

    statuses = readiness.check_and_kick(plan, kick=lambda t, s, e: kicked.append((t, s, e)))

    expected_start = TODAY - dt.timedelta(days=readiness.DEFAULT_LOOKBACK_DAYS)
    assert sorted(kicked) == [("AAPL", expected_start, TODAY), ("MSFT", expected_start, TODAY)]
    assert len(statuses) == 4
    # One status per (ticker, dataset) — AAPL carries two datasets, MSFT two.
    assert {s.ticker for s in statuses} == {"AAPL", "MSFT"}
    assert all(s.state == "kicked" for s in statuses)
    assert all(s.kicked_at > 0 for s in statuses)


def test_check_and_kick_skips_covered_ranges(monkeypatch):
    init_db()
    monkeypatch.setattr(_bf, "needs_backfill", lambda ticker, start, end: False)
    kicked: list[tuple] = []

    statuses = readiness.check_and_kick(
        readiness.plan_datasets(["AAPL"], ["statistical"], today=TODAY), kick=lambda *a: kicked.append(a)
    )

    assert kicked == []
    assert [s.state for s in statuses] == ["covered"]
    assert statuses[0].kicked_at == 0.0


def test_check_and_kick_survives_a_failing_probe(monkeypatch):
    """A probe must never break POST / — a failure degrades to 'not missing'."""
    init_db()

    def _boom(*_a, **_kw):
        raise RuntimeError("db is unhappy")

    monkeypatch.setattr(_bf, "needs_backfill", _boom)
    statuses = readiness.check_and_kick(
        readiness.plan_datasets(["AAPL"], ["statistical"], today=TODAY), kick=lambda *a: None
    )
    assert [s.state for s in statuses] == ["covered"]


# ---------------------------------------------------------------------------
# Cold-start hold window
# ---------------------------------------------------------------------------
def _status(state: str, *, has_data: bool, kicked_at: float = 100.0) -> readiness.ReadinessStatus:
    return readiness.ReadinessStatus(
        ticker="AAPL", dataset="feature_bars", module="statistical", state=state, kicked_at=kicked_at, has_data=has_data
    )


def test_hold_is_none_when_nothing_was_kicked():
    assert readiness.hold_seconds_left(None) is None
    assert readiness.hold_seconds_left(_status("covered", has_data=False)) is None


def test_hold_is_none_when_the_ticker_already_has_usable_history():
    """A partial gap must paint now — only a cold start is worth holding."""
    assert readiness.hold_seconds_left(_status("kicked", has_data=True)) is None


def test_hold_counts_down_and_expires():
    cold = _status("kicked", has_data=False, kicked_at=100.0)
    assert readiness.hold_seconds_left(cold, now=100.0) == pytest.approx(readiness.HOLD_SECONDS)
    assert readiness.hold_seconds_left(cold, now=100.0 + readiness.HOLD_SECONDS - 1) == pytest.approx(1.0)
    assert readiness.hold_seconds_left(cold, now=100.0 + readiness.HOLD_SECONDS + 1) is None


def test_should_hold_stops_as_soon_as_the_backfill_is_gone():
    """A dead (failed or finished) backfill must not keep the tab in 'preparing'.

    This is the difference between "still downloading" and "download failed": once
    the thread exits, /render/* computes and the slice reports the real outcome.
    """
    cold = _status("kicked", has_data=False, kicked_at=100.0)
    assert readiness.should_hold(cold, now=100.0) is False  # no live thread in this test
    assert readiness.should_hold(None) is False
    # Timer alone (hold_seconds_left) is what the count-down test above pins.
    assert readiness.is_backfill_running(cold) is False


def test_status_for_maps_a_module_to_its_plan_entry():
    plan = [
        readiness.ReadinessStatus("AAPL", "clean_bars", "market_review", "covered"),
        readiness.ReadinessStatus("AAPL", "feature_bars", "statistical", "kicked", kicked_at=5.0),
    ]
    assert readiness.status_for(plan, "AAPL", "statistical").dataset == "feature_bars"
    assert readiness.status_for(plan, "AAPL", "regime") is None  # live-only module
    assert readiness.status_for(plan, "MSFT", "statistical") is None
    assert readiness.status_for(None, "AAPL", "statistical") is None


# ---------------------------------------------------------------------------
# kick_backfill really populates the DB (offline TEST_ fixture)
# ---------------------------------------------------------------------------
def test_kick_backfill_populates_the_db():
    init_db()
    ticker = "TEST_AAPL"
    end = dt.date.today()
    start = end - dt.timedelta(days=45)

    readiness.kick_backfill(ticker, start, end)
    readiness.join_backfills(timeout=60)

    df = fetch_df("SELECT date FROM clean_bars WHERE ticker=?", (ticker,))
    assert len(df.index) > 0, "cold-start kick did not populate clean_bars"


def test_kick_backfill_dedupes_an_in_flight_range(monkeypatch):
    """Two kicks for the same range must collapse into one thread.

    WHY the block-on-Event: `kick_backfill` only dedupes while the first
    thread is still alive (`existing.is_alive()`), and `_run_backfill` pops
    itself from `_backfill_threads` the moment `ensure_range` returns. Against
    the real `TEST_*` fixture path (no network, synchronous, fast) that return
    can beat this test back to its second `kick_backfill` call on a quick CI
    runner, so the first thread is already gone and a second (different)
    thread starts — a real "no longer in flight" case, not a dedup bug, but
    one this test must not race against. Blocking `ensure_range` behind an
    `Event` makes "still in flight" deterministic instead of timing-dependent.
    """
    init_db()
    ticker = "TEST_AAPL"
    end = dt.date.today()
    start = end - dt.timedelta(days=30)

    entered = threading.Event()
    release = threading.Event()

    def _blocking_ensure_range(*_args, **_kwargs):
        entered.set()
        release.wait(timeout=5)
        return True

    monkeypatch.setattr(_bf, "ensure_range", _blocking_ensure_range)

    readiness.kick_backfill(ticker, start, end)
    assert entered.wait(timeout=5), "backfill thread did not start in time"
    with readiness._backfill_lock:
        first = readiness._backfill_threads[(ticker, str(start), str(end))]
    readiness.kick_backfill(ticker, start, end)
    with readiness._backfill_lock:
        second = readiness._backfill_threads.get((ticker, str(start), str(end)))
    assert first is second

    release.set()
    readiness.join_backfills(timeout=60)


# ---------------------------------------------------------------------------
# job_cache carries the plan
# ---------------------------------------------------------------------------
def test_create_job_stores_the_plan():
    reset_jobs()
    plan = [readiness.ReadinessStatus("AAPL", "clean_bars", "market_review", "covered")]
    job_id = create_job({"ticker": "AAPL"}, ["AAPL"], plan)
    assert get_job(job_id).plan == plan


def test_create_job_without_a_plan_defaults_to_empty():
    reset_jobs()
    job_id = create_job({"ticker": "AAPL"}, ["AAPL"])
    assert get_job(job_id).plan == []


# ---------------------------------------------------------------------------
# FormService.extract_modules
# ---------------------------------------------------------------------------
class _FakeRequest:
    def __init__(self, values: list[str] | None):
        self._values = values or []

    class _Form(dict):
        def __init__(self, values):
            super().__init__()
            self._values = values

        def getlist(self, key):
            return self._values if key == "modules" else []

    @property
    def form(self):
        return self._Form(self._values)


def test_extract_modules_defaults_to_every_known_module():
    from services.market.form import FormService

    assert FormService.extract_modules(_FakeRequest(None)) == list(readiness.ALL_MODULES)


def test_extract_modules_accepts_repeated_and_comma_separated_values():
    from services.market.form import FormService

    assert FormService.extract_modules(_FakeRequest(["market_review", "statistical"])) == [
        "market_review",
        "statistical",
    ]
    assert FormService.extract_modules(_FakeRequest(["market_review,statistical"])) == [
        "market_review",
        "statistical",
    ]


def test_extract_modules_drops_unknown_tokens_and_dedupes():
    from services.market.form import FormService

    assert FormService.extract_modules(_FakeRequest(["statistical", "nope", "statistical"])) == ["statistical"]

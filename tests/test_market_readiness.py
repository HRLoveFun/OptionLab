"""Services-layer readiness: benchmark-panel prefetch (batch B10).

``data_pipeline.orchestrate.readiness`` cannot import ``core`` (layer rule), so
the Market Review benchmark symbols are folded into the plan in
``services.market.readiness``. These tests pin that expansion and the fact that
it only fires for the ``market_review`` module.
"""

from __future__ import annotations

import datetime as dt

from core.market_review.constants import BENCHMARKS
from services.market import readiness as mr

TODAY = dt.date(2026, 9, 10)
START = TODAY - dt.timedelta(days=400)


def _tickers(plan):
    return {r.ticker for r in plan}


def test_benchmarks_are_added_when_market_review_is_requested():
    base = mr.plan_datasets(["AAPL"], ["market_review"], start=START, end=TODAY)
    augmented = mr._augment_with_benchmarks(base, ["market_review"], start=START, end=TODAY)

    assert _tickers(augmented) == {"AAPL", *BENCHMARKS.values()}
    # every benchmark entry targets the clean_bars dataset
    assert {r.dataset for r in augmented} == {"clean_bars"}


def test_no_benchmarks_without_market_review():
    base = mr.plan_datasets(["AAPL"], ["statistical", "assessment"], start=START, end=TODAY)
    augmented = mr._augment_with_benchmarks(base, ["statistical", "assessment"], start=START, end=TODAY)

    assert augmented == base
    assert _tickers(augmented) == {"AAPL"}


def test_a_benchmark_typed_as_the_ticker_is_not_duplicated():
    a_benchmark = next(iter(BENCHMARKS.values()))
    base = mr.plan_datasets([a_benchmark], ["market_review"], start=START, end=TODAY)
    augmented = mr._augment_with_benchmarks(base, ["market_review"], start=START, end=TODAY)

    pairs = [(r.ticker, r.dataset) for r in augmented]
    assert pairs.count((a_benchmark, "clean_bars")) == 1
    assert _tickers(augmented) == set(BENCHMARKS.values())


def test_prepare_readiness_kicks_benchmark_backfills(monkeypatch):
    kicked: list[str] = []
    monkeypatch.setattr(mr, "check_and_kick", lambda plan, **k: kicked.extend(r.ticker for r in plan) or [])

    mr.prepare_readiness(["NVDA"], ["market_review"], start=START, end=TODAY)

    assert "NVDA" in kicked
    assert set(BENCHMARKS.values()) <= set(kicked)

"""Tests for the scheduler leader-lock helper."""

import os
import tempfile

from data_pipeline.scheduler import acquire_scheduler_lock


def test_first_acquire_succeeds_second_returns_none(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sched.lock")
        h1 = acquire_scheduler_lock(lock_path=path)
        assert h1 is not None
        try:
            h2 = acquire_scheduler_lock(lock_path=path)
            assert h2 is None
        finally:
            h1.close()


def test_lock_released_on_close_can_be_reacquired():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sched.lock")
        h1 = acquire_scheduler_lock(lock_path=path)
        assert h1 is not None
        h1.close()
        h2 = acquire_scheduler_lock(lock_path=path)
        assert h2 is not None
        h2.close()

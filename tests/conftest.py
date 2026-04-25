"""Shared pytest fixtures."""

import pytest


# Use in-memory or temp DB for tests — avoid touching the real database
@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temporary directory for every test."""
    db_file = str(tmp_path / "test_market_data.sqlite")
    monkeypatch.setenv("MARKET_DB_PATH", db_file)
    # Also patch the module-level DB_PATH that was already evaluated at import time
    import data_pipeline.db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_file)

    # Clear DataService's process-wide query cache — entries from a previous
    # test (which used a different DB file) would otherwise mask freshly
    # seeded data within the 60-second TTL.
    try:
        import data_pipeline.data_service as ds_mod

        with ds_mod._query_cache_lock:
            ds_mod._query_cache.clear()
    except Exception:
        pass

"""Tests for data_pipeline.db — error scenarios and edge cases."""
import os
import sqlite3

import pandas as pd
import pytest

from data_pipeline.db import fetch_df, get_conn, init_db, upsert_many


class TestInitDb:
    def test_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite")
        init_db(db_path)
        with sqlite3.connect(db_path) as conn:
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
        assert "raw_prices" in tables
        assert "clean_prices" in tables
        assert "processed_prices" in tables
        assert "market_review_prices" in tables

    def test_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite")
        init_db(db_path)
        init_db(db_path)  # second call should not raise


class TestGetConn:
    def test_wal_mode(self):
        """Connection should use WAL journal mode."""
        with get_conn() as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"

    def test_busy_timeout(self):
        """Connection should have a busy timeout."""
        with get_conn() as conn:
            timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
            assert timeout >= 5000


class TestUpsertMany:
    def test_basic_insert(self):
        init_db()
        rows = [("TEST", "2024-01-01", 100.0, 105.0, 95.0, 102.0, 102.0, 1000000.0, "yfinance")]
        upsert_many(
            "raw_prices",
            ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"],
            rows,
        )
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker='TEST'", ())
        assert len(df) == 1

    def test_upsert_updates_on_conflict(self):
        init_db()
        cols = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"]
        rows1 = [("UPD", "2024-01-01", 100.0, 105.0, 95.0, 102.0, 102.0, 1000.0, "yfinance")]
        upsert_many("raw_prices", cols, rows1)

        rows2 = [("UPD", "2024-01-01", 100.0, 105.0, 95.0, 110.0, 110.0, 2000.0, "yfinance")]
        upsert_many("raw_prices", cols, rows2)

        df = fetch_df("SELECT date, close, volume FROM raw_prices WHERE ticker='UPD'", ())
        assert len(df) == 1
        assert float(df.iloc[0]["close"]) == 110.0
        assert float(df.iloc[0]["volume"]) == 2000.0

    def test_empty_rows_no_error(self):
        init_db()
        upsert_many("raw_prices", ["ticker", "date"], [])

    def test_rollback_on_bad_data(self):
        """Invalid data should trigger rollback, not leave partial writes."""
        init_db()
        cols = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"]
        good = ("RB", "2024-01-01", 100.0, 105.0, 95.0, 102.0, 102.0, 1000.0, "yfinance")
        bad = ("RB", "2024-01-02", 100.0, 105.0, 95.0, 102.0, 102.0, 1000.0, "yfinance", "EXTRA")  # too many columns
        with pytest.raises(sqlite3.OperationalError):
            upsert_many("raw_prices", cols, [good, bad])
        # Good row should also be rolled back
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker='RB'", ())
        assert len(df) == 0


class TestFetchDf:
    def test_returns_dataframe(self):
        init_db()
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker='NONEXIST'", ())
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_with_data(self):
        init_db()
        rows = [("FD", "2024-06-01", 50.0, 55.0, 45.0, 52.0, 52.0, 500.0, "yfinance")]
        upsert_many(
            "raw_prices",
            ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume", "provider"],
            rows,
        )
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker=?", ("FD",))
        assert len(df) == 1


class TestDbEdgeCases:
    def test_readonly_path_raises(self, tmp_path):
        """Writing to a read-only path should raise an error."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        db_path = str(readonly_dir / "test.sqlite")
        init_db(db_path)
        # Make directory read-only
        os.chmod(str(readonly_dir), 0o444)
        try:
            # Attempting to create a new DB in read-only dir should fail
            bad_path = str(readonly_dir / "sub" / "test2.sqlite")
            with pytest.raises(sqlite3.OperationalError):
                init_db(bad_path)
        finally:
            os.chmod(str(readonly_dir), 0o755)

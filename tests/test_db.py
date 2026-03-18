"""Tests for data_pipeline/db.py — init, get_conn, upsert, fetch."""
import sqlite3
import pytest

from data_pipeline.db import init_db, get_conn, upsert_many, fetch_df


class TestInitDb:
    def test_creates_tables(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with sqlite3.connect(db) as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "raw_prices" in tables
        assert "clean_prices" in tables
        assert "processed_prices" in tables

    def test_idempotent(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        init_db(db)  # no error on second call


class TestGetConn:
    def test_wal_mode(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with get_conn(db) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode.lower() == "wal"

    def test_conn_closes(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with get_conn(db) as conn:
            conn.execute("SELECT 1")
        # After exiting context, connection should be closed
        with pytest.raises(Exception):
            conn.execute("SELECT 1")


class TestUpsertMany:
    def test_insert_and_fetch(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        cols = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
        rows = [("AAPL", "2024-01-02", 100, 105, 99, 103, 103, 1000000)]
        upsert_many("raw_prices", cols, rows, db)
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker=?", ("AAPL",), db)
        assert len(df) == 1
        assert df.iloc[0]["close"] == 103

    def test_upsert_updates(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        cols = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
        rows = [("AAPL", "2024-01-02", 100, 105, 99, 103, 103, 1000000)]
        upsert_many("raw_prices", cols, rows, db)
        # Update close price
        rows2 = [("AAPL", "2024-01-02", 100, 105, 99, 110, 110, 1200000)]
        upsert_many("raw_prices", cols, rows2, db)
        df = fetch_df("SELECT * FROM raw_prices WHERE ticker=?", ("AAPL",), db)
        assert len(df) == 1
        assert df.iloc[0]["close"] == 110

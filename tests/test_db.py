"""Tests for data_pipeline/db.py — init, get_conn, upsert, fetch."""

import sqlite3
import threading

import pytest

from data_pipeline.db import close_thread_conn, fetch_df, get_conn, init_db, upsert_many


class TestInitDb:
    def test_creates_tables(self, tmp_path):
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with sqlite3.connect(db) as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
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
        close_thread_conn(db)

    def test_conn_persists_across_with_blocks(self, tmp_path):
        """get_conn now returns a thread-local persistent connection.

        The same connection object must be reused across multiple `with` blocks
        on the same thread (avoids the cost of reconnecting + re-applying
        PRAGMAs on every query). Closing is explicit via close_thread_conn().
        """
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with get_conn(db) as conn1:
            id1 = id(conn1)
        with get_conn(db) as conn2:
            id2 = id(conn2)
            # Same Python object — cached connection reused.
            assert id1 == id2
            # And it's still open and usable.
            assert conn2.execute("SELECT 1").fetchone()[0] == 1
        close_thread_conn(db)
        # After explicit close the cached entry is gone.
        with pytest.raises(sqlite3.ProgrammingError):
            conn2.execute("SELECT 1")

    def test_per_thread_isolation(self, tmp_path):
        """Different threads must get different connection objects."""
        db = str(tmp_path / "test.sqlite")
        init_db(db)
        with get_conn(db) as main_conn:
            main_id = id(main_conn)
        worker_id: list[int] = []

        def _worker():
            with get_conn(db) as c:
                worker_id.append(id(c))
            close_thread_conn(db)

        t = threading.Thread(target=_worker)
        t.start()
        t.join()
        assert worker_id and worker_id[0] != main_id
        close_thread_conn(db)


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

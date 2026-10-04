"""Tests for Database init and seeding."""

from __future__ import annotations

from pathlib import Path

from app.db import Database
from app.db.seed import DEFAULT_CASH_BALANCE, DEFAULT_WATCHLIST


class TestDatabaseInit:
    """Unit tests for lazy schema creation and seeding."""

    def test_init_creates_file_and_tables(self, tmp_path: Path):
        """init() creates the SQLite file and all tables on a fresh path."""
        db = Database(tmp_path / "test.db")
        db.init()

        assert db.path.exists()
        with db.connect() as conn:
            tables = {
                r["name"]
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        expected = {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        }
        assert expected <= tables

    def test_init_seeds_default_profile(self, tmp_path: Path):
        """A fresh database gets the default user profile."""
        db = Database(tmp_path / "test.db")
        db.init()

        with db.connect() as conn:
            row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()
        assert row["cash_balance"] == DEFAULT_CASH_BALANCE

    def test_init_seeds_default_watchlist(self, tmp_path: Path):
        """A fresh database gets the 10 default watchlist tickers."""
        db = Database(tmp_path / "test.db")
        db.init()

        with db.connect() as conn:
            rows = conn.execute("SELECT ticker FROM watchlist WHERE user_id = 'default'").fetchall()
        tickers = {r["ticker"] for r in rows}
        assert tickers == set(DEFAULT_WATCHLIST)

    def test_init_seeds_initial_snapshot(self, tmp_path: Path):
        """A fresh database gets one initial $10,000 portfolio snapshot."""
        db = Database(tmp_path / "test.db")
        db.init()

        with db.connect() as conn:
            rows = conn.execute("SELECT total_value FROM portfolio_snapshots").fetchall()
        assert len(rows) == 1
        assert rows[0]["total_value"] == DEFAULT_CASH_BALANCE

    def test_init_is_idempotent(self, tmp_path: Path):
        """Calling init() again does not duplicate seed data."""
        db = Database(tmp_path / "test.db")
        db.init()
        db.init()

        with db.connect() as conn:
            profiles = conn.execute("SELECT * FROM users_profile").fetchall()
            watchlist_rows = conn.execute("SELECT * FROM watchlist").fetchall()
        assert len(profiles) == 1
        assert len(watchlist_rows) == len(DEFAULT_WATCHLIST)

    def test_init_creates_parent_directory(self, tmp_path: Path):
        """init() creates missing parent directories for the db file."""
        db = Database(tmp_path / "nested" / "dir" / "test.db")
        db.init()
        assert db.path.exists()

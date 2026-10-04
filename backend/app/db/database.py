"""SQLite connection management and lazy schema/seed initialization."""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .schema import CREATE_TABLE_STATEMENTS
from .seed import seed_default_data

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("db/finally.db")


def get_db_path() -> Path:
    """Resolve the SQLite file path.

    Override with the DB_PATH env var — used by tests to avoid touching the
    real database file.
    """
    override = os.environ.get("DB_PATH", "").strip()
    return Path(override) if override else DEFAULT_DB_PATH


class Database:
    """Owns the SQLite file path and lazy schema/seed initialization.

    Each call to connect() opens a short-lived connection rather than sharing
    one long-lived connection — standard sqlite3 usage for a single-user,
    low-concurrency app (PLAN.md §7).
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or get_db_path()

    def init(self) -> None:
        """Create the schema if missing and seed default data on a fresh database.

        Safe to call on every startup: CREATE TABLE IF NOT EXISTS is
        idempotent, and seeding only runs if the default profile is absent.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            for statement in CREATE_TABLE_STATEMENTS:
                conn.execute(statement)
            conn.commit()

            existing = conn.execute("SELECT 1 FROM users_profile WHERE id = 'default'").fetchone()
            if existing is None:
                seed_default_data(conn)
                conn.commit()
                logger.info("Database seeded with default profile and watchlist")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a connection as a context manager; closes it on exit."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

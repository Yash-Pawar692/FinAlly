"""Database layer: schema, seeding, and lazy initialization for FinAlly.

Public API:
    Database     - Owns the SQLite path; init() creates/seeds, connect() opens a connection
    get_db_path  - Resolve the SQLite file path (DB_PATH env var override)
"""

from .database import Database, get_db_path

__all__ = ["Database", "get_db_path"]

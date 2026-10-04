"""Default seed data for a fresh database (PLAN.md §7)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

DEFAULT_CASH_BALANCE = 10000.0

DEFAULT_WATCHLIST: list[str] = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]


def seed_default_data(conn: sqlite3.Connection) -> None:
    """Insert the default user profile, watchlist, and initial snapshot.

    Called once, the first time `init()` finds no 'default' row in
    users_profile. Does not commit — caller controls the transaction.
    """
    now = datetime.now(UTC).isoformat()

    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        ("default", DEFAULT_CASH_BALANCE, now),
    )

    conn.executemany(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        [(str(uuid.uuid4()), "default", ticker, now) for ticker in DEFAULT_WATCHLIST],
    )

    # Seeds the P&L chart with a starting point instead of an empty chart for
    # up to 30s after a fresh launch (PLAN.md §7).
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), "default", DEFAULT_CASH_BALANCE, now),
    )

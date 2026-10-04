"""Watchlist business logic (PLAN.md §6-7)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from app.market import PriceCache

USER_ID = "default"


def get_watchlist(conn: sqlite3.Connection, price_cache: PriceCache) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
        (USER_ID,),
    ).fetchall()
    result = []
    for row in rows:
        update = price_cache.get(row["ticker"])
        result.append(
            {
                "ticker": row["ticker"],
                "added_at": row["added_at"],
                "price": update.to_dict() if update else None,
            }
        )
    return result


def add_to_watchlist(conn: sqlite3.Connection, ticker: str) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), USER_ID, ticker, now),
    )
    conn.commit()


def remove_from_watchlist(conn: sqlite3.Connection, ticker: str) -> None:
    conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (USER_ID, ticker))
    conn.commit()


def has_open_position(conn: sqlite3.Connection, ticker: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM positions WHERE user_id = ? AND ticker = ?", (USER_ID, ticker)
    ).fetchone()
    return row is not None


def get_active_tickers(conn: sqlite3.Connection) -> set[str]:
    """Union of watchlist tickers and tickers with an open position (PLAN.md §6).

    This is the ticker set passed to the market data source on startup.
    """
    watch = {
        r["ticker"] for r in conn.execute("SELECT ticker FROM watchlist WHERE user_id = ?", (USER_ID,))
    }
    held = {
        r["ticker"] for r in conn.execute("SELECT ticker FROM positions WHERE user_id = ?", (USER_ID,))
    }
    return watch | held

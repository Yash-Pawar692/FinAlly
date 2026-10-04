"""Portfolio business logic: trade execution, valuation, and history (PLAN.md §7-8)."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from app.market import PriceCache

from .errors import TradeError

USER_ID = "default"


def get_cash_balance(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (USER_ID,)).fetchone()
    return row["cash_balance"]


def get_positions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT ticker, quantity, avg_cost, updated_at FROM positions "
        "WHERE user_id = ? ORDER BY ticker",
        (USER_ID,),
    ).fetchall()


def get_portfolio(conn: sqlite3.Connection, price_cache: PriceCache) -> dict:
    """Current cash, positions (with live price and unrealized P&L), and total value."""
    cash = get_cash_balance(conn)
    positions = []
    total_position_value = 0.0

    for row in get_positions(conn):
        ticker = row["ticker"]
        quantity = row["quantity"]
        avg_cost = row["avg_cost"]
        price = price_cache.get_price(ticker)
        cost_basis = quantity * avg_cost

        if price is None:
            # No cached price yet (routine under Massive before a position's
            # ticker is first polled). Value at cost until a price arrives.
            market_value = cost_basis
            unrealized_pnl = 0.0
            unrealized_pnl_percent = 0.0
        else:
            market_value = quantity * price
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis else 0.0

        total_position_value += market_value
        positions.append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": price,
                "market_value": round(market_value, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_percent": round(unrealized_pnl_percent, 4),
            }
        )

    total_value = cash + total_position_value
    return {
        "cash_balance": round(cash, 2),
        "positions": positions,
        "total_value": round(total_value, 2),
    }


def get_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT total_value, recorded_at FROM portfolio_snapshots "
        "WHERE user_id = ? ORDER BY recorded_at",
        (USER_ID,),
    ).fetchall()
    return [{"total_value": r["total_value"], "recorded_at": r["recorded_at"]} for r in rows]


def get_trades(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT ticker, side, quantity, price, executed_at FROM trades "
        "WHERE user_id = ? ORDER BY executed_at DESC",
        (USER_ID,),
    ).fetchall()
    return [
        {
            "ticker": r["ticker"],
            "side": r["side"],
            "quantity": r["quantity"],
            "price": r["price"],
            "executed_at": r["executed_at"],
        }
        for r in rows
    ]


def record_snapshot(conn: sqlite3.Connection, price_cache: PriceCache) -> None:
    """Insert a portfolio_snapshots row for the current total value."""
    total_value = get_portfolio(conn, price_cache)["total_value"]
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), USER_ID, total_value, now),
    )
    conn.commit()


def execute_trade(
    conn: sqlite3.Connection,
    price_cache: PriceCache,
    ticker: str,
    quantity: float,
    side: str,
) -> dict:
    """Validate and execute a market order; raises TradeError on failure.

    On success: updates cash, upserts/deletes the position row, appends a
    trade record, records a portfolio snapshot, and returns the executed
    trade. Shared by the REST trade endpoint and LLM-initiated trades
    (PLAN.md §9) so both go through identical validation.
    """
    ticker = ticker.upper().strip()

    if quantity <= 0:
        raise TradeError("invalid_quantity", "Quantity must be greater than zero.")

    price = price_cache.get_price(ticker)
    if price is None:
        raise TradeError("no_price_available", f"No price is available yet for {ticker}.")

    cash = get_cash_balance(conn)
    position = conn.execute(
        "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (USER_ID, ticker),
    ).fetchone()

    now = datetime.now(UTC).isoformat()
    trade_cost = round(price * quantity, 2)

    if side == "buy":
        if trade_cost > cash:
            raise TradeError(
                "insufficient_cash",
                f"Buying {quantity} {ticker} at ${price:.2f} costs ${trade_cost:.2f}, "
                f"but only ${cash:.2f} cash is available.",
            )

        if position is None:
            new_qty = quantity
            new_avg_cost = price
        else:
            old_qty = position["quantity"]
            old_avg_cost = position["avg_cost"]
            new_qty = old_qty + quantity
            new_avg_cost = (old_qty * old_avg_cost + quantity * price) / new_qty

        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (cash - trade_cost, USER_ID),
        )
        _upsert_position(conn, ticker, new_qty, new_avg_cost, now)

    else:  # sell
        owned_qty = position["quantity"] if position else 0.0
        if quantity > owned_qty:
            raise TradeError(
                "insufficient_shares",
                f"Cannot sell {quantity} shares of {ticker}; only {owned_qty} are held.",
            )

        new_qty = owned_qty - quantity
        conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (cash + trade_cost, USER_ID),
        )
        if new_qty == 0:
            conn.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (USER_ID, ticker))
        else:
            # avg_cost is unchanged by a sell (PLAN.md §7)
            _upsert_position(conn, ticker, new_qty, position["avg_cost"], now)

    trade_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade_id, USER_ID, ticker, side, quantity, price, now),
    )
    conn.commit()

    record_snapshot(conn, price_cache)

    return {
        "id": trade_id,
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": now,
    }


def _upsert_position(
    conn: sqlite3.Connection, ticker: str, quantity: float, avg_cost: float, now: str
) -> None:
    conn.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (user_id, ticker) DO UPDATE SET "
        "quantity = excluded.quantity, avg_cost = excluded.avg_cost, updated_at = excluded.updated_at",
        (str(uuid.uuid4()), USER_ID, ticker, quantity, avg_cost, now),
    )

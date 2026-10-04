"""Chat business logic: portfolio context, LLM call, action execution (PLAN.md §9)."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import uuid
from datetime import UTC, datetime

from app.market import MarketDataSource, PriceCache
from app.portfolio import service as portfolio_service
from app.portfolio.errors import TradeError
from app.watchlist import service as watchlist_service

from .schemas import (
    ChatApiResponse,
    ExecutedTrade,
    ExecutedWatchlistChange,
    LlmChatResponse,
    LlmTradeAction,
    LlmWatchlistChange,
)

logger = logging.getLogger(__name__)

USER_ID = "default"

MODEL = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}

HISTORY_ROW_LIMIT = 10

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant embedded in a simulated \
trading terminal. You help the user understand and manage a virtual portfolio.

Responsibilities:
- Analyze portfolio composition, risk concentration, and P&L when asked.
- Suggest trades with clear reasoning.
- Execute trades when the user asks for one or agrees to one you suggested.
- Manage the watchlist proactively (add tickers worth watching, remove ones that \
no longer matter to the conversation).
- Be concise and data-driven — prefer numbers from the portfolio context over \
vague language.
- Trade quantities are always share counts, never dollar amounts. If the user \
gives a dollar amount, convert it to a share count yourself using the live price \
already given to you in the portfolio context below.

Always respond with valid JSON matching the required schema. Never fabricate \
prices, balances, or positions — use only what's in the portfolio context."""


def build_portfolio_context(conn: sqlite3.Connection, price_cache: PriceCache) -> str:
    """Render cash, positions, watchlist, and total value as text for the prompt."""
    portfolio = portfolio_service.get_portfolio(conn, price_cache)
    watchlist = watchlist_service.get_watchlist(conn, price_cache)

    lines = [
        "Current portfolio:",
        f"- Cash balance: ${portfolio['cash_balance']:.2f}",
        f"- Total portfolio value: ${portfolio['total_value']:.2f}",
    ]

    if portfolio["positions"]:
        lines.append("- Open positions:")
        for position in portfolio["positions"]:
            price_str = f"${position['current_price']:.2f}" if position["current_price"] is not None else "N/A"
            lines.append(
                f"  - {position['ticker']}: {position['quantity']} shares, "
                f"avg cost ${position['avg_cost']:.2f}, current price {price_str}, "
                f"unrealized P&L ${position['unrealized_pnl']:.2f} "
                f"({position['unrealized_pnl_percent']:.2f}%)"
            )
    else:
        lines.append("- Open positions: none")

    watched = [w for w in watchlist if w["price"] is not None]
    if watched:
        lines.append("- Watchlist (ticker: live price):")
        for entry in watched:
            lines.append(f"  - {entry['ticker']}: ${entry['price']['price']:.2f}")
    else:
        lines.append("- Watchlist: no live prices yet")

    return "\n".join(lines)


def load_recent_history(conn: sqlite3.Connection) -> list[dict]:
    """Last 10 chat_messages rows (up to 5 user + 5 assistant turns), oldest first."""
    rows = conn.execute(
        "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (USER_ID, HISTORY_ROW_LIMIT),
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


_TRADE_PATTERN = re.compile(r"\b(buy|sell)\s+(\d+(?:\.\d+)?)\s+(?:shares?\s+of\s+)?([a-zA-Z]{1,6})\b", re.IGNORECASE)
_WATCHLIST_PATTERN = re.compile(
    r"\b(add|remove)\s+([a-zA-Z]{1,6})\s+(?:to|from)\s+(?:the\s+)?watchlist\b", re.IGNORECASE
)


def _generate_mock_response(user_message: str, portfolio_context: str) -> LlmChatResponse:
    """Deterministic response for LLM_MOCK=true (PLAN.md §9), used by E2E tests."""
    trades = []
    for side, quantity, ticker in _TRADE_PATTERN.findall(user_message):
        trades.append(LlmTradeAction(ticker=ticker.upper(), side=side.lower(), quantity=float(quantity)))

    watchlist_changes = []
    for action, ticker in _WATCHLIST_PATTERN.findall(user_message):
        watchlist_changes.append(LlmWatchlistChange(ticker=ticker.upper(), action=action.lower()))

    if trades:
        summary = ", ".join(f"{t.side} {t.quantity} {t.ticker}" for t in trades)
        message = f"[mock] Executing: {summary}."
    elif watchlist_changes:
        summary = ", ".join(f"{w.action} {w.ticker}" for w in watchlist_changes)
        message = f"[mock] Updating watchlist: {summary}."
    else:
        message = f"[mock] Received your message. {portfolio_context.splitlines()[1]}"

    return LlmChatResponse(message=message, trades=trades, watchlist_changes=watchlist_changes)


def _call_llm(messages: list[dict]) -> LlmChatResponse:
    from litellm import completion

    response = completion(
        model=MODEL,
        messages=messages,
        response_format=LlmChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    result = response.choices[0].message.content
    return LlmChatResponse.model_validate_json(result)


async def handle_chat_message(
    conn: sqlite3.Connection,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    user_message: str,
) -> ChatApiResponse:
    """Full chat turn: build context, call the LLM, auto-execute actions, persist, respond."""
    portfolio_context = build_portfolio_context(conn, price_cache)
    history = load_recent_history(conn)

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{portfolio_context}"},
        *history,
        {"role": "user", "content": user_message},
    ]

    if _is_mock_mode():
        llm_response = _generate_mock_response(user_message, portfolio_context)
    else:
        try:
            llm_response = _call_llm(messages)
        except Exception:
            logger.exception("LLM call failed")
            llm_response = LlmChatResponse(
                message="Sorry, I couldn't reach the AI model just now. Please try again."
            )

    executed_trades, executed_watchlist_changes = await _execute_actions(
        conn, price_cache, market_source, llm_response
    )

    _persist_turn(conn, user_message, llm_response.message, executed_trades, executed_watchlist_changes)

    return ChatApiResponse(
        message=llm_response.message,
        trades=executed_trades,
        watchlist_changes=executed_watchlist_changes,
    )


async def _execute_actions(
    conn: sqlite3.Connection,
    price_cache: PriceCache,
    market_source: MarketDataSource,
    llm_response: LlmChatResponse,
) -> tuple[list[ExecutedTrade], list[ExecutedWatchlistChange]]:
    executed_trades: list[ExecutedTrade] = []
    for trade in llm_response.trades:
        try:
            portfolio_service.execute_trade(conn, price_cache, trade.ticker, trade.quantity, trade.side)
            executed_trades.append(ExecutedTrade(ticker=trade.ticker, side=trade.side, quantity=trade.quantity))
        except TradeError as e:
            executed_trades.append(
                ExecutedTrade(ticker=trade.ticker, side=trade.side, quantity=trade.quantity, error=e.message)
            )

    executed_watchlist_changes: list[ExecutedWatchlistChange] = []
    for change in llm_response.watchlist_changes:
        ticker = change.ticker.upper().strip()
        if change.action == "add":
            watchlist_service.add_to_watchlist(conn, ticker)
            await market_source.add_ticker(ticker)
        else:
            watchlist_service.remove_from_watchlist(conn, ticker)
            if not watchlist_service.has_open_position(conn, ticker):
                await market_source.remove_ticker(ticker)
        executed_watchlist_changes.append(ExecutedWatchlistChange(ticker=ticker, action=change.action))

    return executed_trades, executed_watchlist_changes


def _persist_turn(
    conn: sqlite3.Connection,
    user_message: str,
    assistant_message: str,
    executed_trades: list[ExecutedTrade],
    executed_watchlist_changes: list[ExecutedWatchlistChange],
) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), USER_ID, "user", user_message, None, now),
    )

    actions = {
        "trades": [t.model_dump() for t in executed_trades],
        "watchlist_changes": [w.model_dump() for w in executed_watchlist_changes],
    }
    has_actions = bool(executed_trades or executed_watchlist_changes)
    conn.execute(
        "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            USER_ID,
            "assistant",
            assistant_message,
            json.dumps(actions) if has_actions else None,
            now,
        ),
    )
    conn.commit()

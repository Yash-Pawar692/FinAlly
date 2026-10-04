"""Tests for chat.service (mock LLM mode only — no real API calls)."""

from __future__ import annotations

import json

from app.chat import service as chat_service
from app.chat.schemas import LlmTradeAction, LlmWatchlistChange
from app.db import Database
from app.market import PriceCache
from app.portfolio import service as portfolio_service


class FakeMarketSource:
    """Records add_ticker/remove_ticker calls without touching a real simulator."""

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)


class TestBuildPortfolioContext:
    def test_includes_cash_and_total_value(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            context = chat_service.build_portfolio_context(conn, price_cache)
        assert "Cash balance: $10000.00" in context
        assert "Total portfolio value: $10000.00" in context

    def test_no_positions_says_none(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            context = chat_service.build_portfolio_context(conn, price_cache)
        assert "Open positions: none" in context

    def test_includes_watched_prices(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            context = chat_service.build_portfolio_context(conn, price_cache)
        assert "AAPL: $200.00" in context


class TestLoadRecentHistory:
    def test_empty_history(self, db: Database):
        with db.connect() as conn:
            assert chat_service.load_recent_history(conn) == []

    def test_history_is_chronological_and_capped(self, db: Database):
        with db.connect() as conn:
            for i in range(15):
                conn.execute(
                    "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
                    "VALUES (?, 'default', 'user', ?, NULL, ?)",
                    (f"id-{i}", f"message {i}", f"2026-01-01T00:00:{i:02d}+00:00"),
                )
            conn.commit()
            history = chat_service.load_recent_history(conn)

        assert len(history) == 10
        assert history[0]["content"] == "message 5"
        assert history[-1]["content"] == "message 14"


class TestGenerateMockResponse:
    def test_buy_command_produces_trade(self):
        response = chat_service._generate_mock_response("buy 5 AAPL please", "Current portfolio:\n- x")
        assert response.trades == [LlmTradeAction(ticker="AAPL", side="buy", quantity=5.0)]

    def test_sell_command_produces_trade(self):
        response = chat_service._generate_mock_response("sell 2 TSLA", "Current portfolio:\n- x")
        assert response.trades == [LlmTradeAction(ticker="TSLA", side="sell", quantity=2.0)]

    def test_add_to_watchlist_command(self):
        response = chat_service._generate_mock_response(
            "add PYPL to the watchlist", "Current portfolio:\n- x"
        )
        assert response.watchlist_changes == [LlmWatchlistChange(ticker="PYPL", action="add")]

    def test_remove_from_watchlist_command(self):
        response = chat_service._generate_mock_response(
            "remove TSLA from the watchlist", "Current portfolio:\n- x"
        )
        assert response.watchlist_changes == [LlmWatchlistChange(ticker="TSLA", action="remove")]

    def test_generic_message_has_no_actions(self):
        response = chat_service._generate_mock_response("how am I doing?", "Current portfolio:\n- x")
        assert response.trades == []
        assert response.watchlist_changes == []
        assert response.message.startswith("[mock]")


class TestHandleChatMessage:
    async def test_buy_trade_executes_and_updates_portfolio(self, db: Database, price_cache: PriceCache):
        market_source = FakeMarketSource()
        with db.connect() as conn:
            response = await chat_service.handle_chat_message(
                conn, price_cache, market_source, "buy 5 AAPL"
            )
            portfolio = portfolio_service.get_portfolio(conn, price_cache)

        assert response.trades[0].error is None
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["quantity"] == 5

    async def test_failing_trade_reports_error_without_executing(self, db: Database, price_cache: PriceCache):
        market_source = FakeMarketSource()
        with db.connect() as conn:
            response = await chat_service.handle_chat_message(
                conn, price_cache, market_source, "buy 1 ZZZZ"
            )
            portfolio = portfolio_service.get_portfolio(conn, price_cache)

        assert response.trades[0].error is not None
        assert portfolio["positions"] == []

    async def test_watchlist_add_calls_market_source(self, db: Database, price_cache: PriceCache):
        market_source = FakeMarketSource()
        with db.connect() as conn:
            await chat_service.handle_chat_message(
                conn, price_cache, market_source, "add PYPL to the watchlist"
            )
        assert market_source.added == ["PYPL"]

    async def test_persists_user_and_assistant_messages(self, db: Database, price_cache: PriceCache):
        market_source = FakeMarketSource()
        with db.connect() as conn:
            await chat_service.handle_chat_message(conn, price_cache, market_source, "buy 5 AAPL")
            rows = conn.execute(
                "SELECT role, content, actions FROM chat_messages ORDER BY created_at"
            ).fetchall()

        assert len(rows) == 2
        assert rows[0]["role"] == "user"
        assert rows[0]["content"] == "buy 5 AAPL"
        assert rows[1]["role"] == "assistant"
        actions = json.loads(rows[1]["actions"])
        assert actions["trades"][0]["ticker"] == "AAPL"

    async def test_no_actions_leaves_actions_column_null(self, db: Database, price_cache: PriceCache):
        market_source = FakeMarketSource()
        with db.connect() as conn:
            await chat_service.handle_chat_message(conn, price_cache, market_source, "how am I doing?")
            row = conn.execute(
                "SELECT actions FROM chat_messages WHERE role = 'assistant'"
            ).fetchone()
        assert row["actions"] is None

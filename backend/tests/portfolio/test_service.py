"""Tests for portfolio.service: trade execution, valuation, history."""

from __future__ import annotations

import pytest

from app.db import Database
from app.market import PriceCache
from app.portfolio import TradeError
from app.portfolio import service as portfolio_service


class TestGetPortfolio:
    """Unit tests for get_portfolio()."""

    def test_fresh_portfolio_has_default_cash_and_no_positions(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            result = portfolio_service.get_portfolio(conn, price_cache)
        assert result["cash_balance"] == 10000.0
        assert result["positions"] == []
        assert result["total_value"] == 10000.0


class TestExecuteTradeBuy:
    """Unit tests for a buy order."""

    def test_buy_deducts_cash_and_creates_position(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            trade = portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "buy")
            portfolio = portfolio_service.get_portfolio(conn, price_cache)

        assert trade["ticker"] == "AAPL"
        assert trade["price"] == 200.0
        assert portfolio["cash_balance"] == 10000.0 - 2000.0
        assert len(portfolio["positions"]) == 1
        position = portfolio["positions"][0]
        assert position["quantity"] == 10
        assert position["avg_cost"] == 200.0
        assert position["unrealized_pnl"] == 0.0

    def test_buy_recalculates_weighted_average_cost(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "buy")
            price_cache.update("AAPL", 220.0)
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "buy")
            portfolio = portfolio_service.get_portfolio(conn, price_cache)

        position = portfolio["positions"][0]
        assert position["quantity"] == 20
        assert position["avg_cost"] == pytest.approx(210.0)

    def test_buy_with_insufficient_cash_raises(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "AAPL", 1000, "buy")
        assert exc_info.value.code == "insufficient_cash"

    def test_buy_records_trade_history(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 5, "buy")
            trades = portfolio_service.get_trades(conn)
        assert len(trades) == 1
        assert trades[0]["side"] == "buy"
        assert trades[0]["quantity"] == 5

    def test_buy_records_portfolio_snapshot(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            before = portfolio_service.get_history(conn)
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 5, "buy")
            after = portfolio_service.get_history(conn)
        assert len(after) == len(before) + 1


class TestExecuteTradeSell:
    """Unit tests for a sell order."""

    def test_sell_increases_cash_and_reduces_position(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "buy")
            cash_after_buy = portfolio_service.get_cash_balance(conn)
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 4, "sell")
            portfolio = portfolio_service.get_portfolio(conn, price_cache)

        assert portfolio["cash_balance"] == cash_after_buy + 4 * 200.0
        position = portfolio["positions"][0]
        assert position["quantity"] == 6
        assert position["avg_cost"] == 200.0  # unchanged by a sell

    def test_sell_closing_position_deletes_row(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "buy")
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "sell")
            portfolio = portfolio_service.get_portfolio(conn, price_cache)
        assert portfolio["positions"] == []

    def test_sell_more_than_owned_raises(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, price_cache, "AAPL", 5, "buy")
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "AAPL", 10, "sell")
        assert exc_info.value.code == "insufficient_shares"

    def test_sell_with_no_position_raises(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "AAPL", 1, "sell")
        assert exc_info.value.code == "insufficient_shares"


class TestExecuteTradeValidation:
    """Unit tests for trade validation independent of side."""

    def test_non_positive_quantity_raises_invalid_quantity(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "AAPL", 0, "buy")
        assert exc_info.value.code == "invalid_quantity"

    def test_negative_quantity_raises_invalid_quantity(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "AAPL", -5, "buy")
        assert exc_info.value.code == "invalid_quantity"

    def test_ticker_with_no_cached_price_raises_no_price_available(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            with pytest.raises(TradeError) as exc_info:
                portfolio_service.execute_trade(conn, price_cache, "ZZZZ", 1, "buy")
        assert exc_info.value.code == "no_price_available"


class TestPortfolioValuationWithoutPrice:
    """A held position whose ticker has no cached price values at cost, not crash."""

    def test_position_without_price_values_at_cost(self, db: Database):
        cache = PriceCache()
        cache.update("AAPL", 200.0)
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, cache, "AAPL", 10, "buy")

        # Simulate the ticker's price disappearing from the cache (e.g. an
        # un-watched, never-held-elsewhere ticker under Massive).
        empty_cache = PriceCache()
        with db.connect() as conn:
            portfolio = portfolio_service.get_portfolio(conn, empty_cache)

        position = portfolio["positions"][0]
        assert position["current_price"] is None
        assert position["market_value"] == 2000.0
        assert position["unrealized_pnl"] == 0.0

"""Tests for watchlist.service."""

from __future__ import annotations

from app.db import Database
from app.market import PriceCache
from app.portfolio import service as portfolio_service
from app.watchlist import service as watchlist_service


class TestGetWatchlist:
    """Unit tests for get_watchlist()."""

    def test_default_watchlist_has_ten_tickers(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            result = watchlist_service.get_watchlist(conn, price_cache)
        assert len(result) == 10

    def test_entries_without_cached_price_report_none(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            result = watchlist_service.get_watchlist(conn, price_cache)
        assert all(entry["price"] is None for entry in result)

    def test_entries_with_cached_price_report_it(self, db: Database, price_cache: PriceCache):
        price_cache.update("AAPL", 190.0)
        with db.connect() as conn:
            result = watchlist_service.get_watchlist(conn, price_cache)
        aapl = next(e for e in result if e["ticker"] == "AAPL")
        assert aapl["price"]["price"] == 190.0


class TestAddRemove:
    """Unit tests for add_to_watchlist() / remove_from_watchlist()."""

    def test_add_new_ticker(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            watchlist_service.add_to_watchlist(conn, "PYPL")
            result = watchlist_service.get_watchlist(conn, price_cache)
        assert any(e["ticker"] == "PYPL" for e in result)

    def test_add_duplicate_ticker_is_idempotent(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            watchlist_service.add_to_watchlist(conn, "AAPL")
            result = watchlist_service.get_watchlist(conn, price_cache)
        assert sum(1 for e in result if e["ticker"] == "AAPL") == 1

    def test_remove_ticker(self, db: Database, price_cache: PriceCache):
        with db.connect() as conn:
            watchlist_service.remove_from_watchlist(conn, "AAPL")
            result = watchlist_service.get_watchlist(conn, price_cache)
        assert all(e["ticker"] != "AAPL" for e in result)


class TestActiveTickers:
    """Unit tests for get_active_tickers() — watchlist ∪ open positions."""

    def test_active_tickers_is_watchlist_when_no_positions(self, db: Database):
        with db.connect() as conn:
            active = watchlist_service.get_active_tickers(conn)
        assert len(active) == 10

    def test_held_position_outside_watchlist_stays_active(self, db: Database):
        cache = PriceCache()
        cache.update("ZZZZ", 50.0)
        with db.connect() as conn:
            portfolio_service.execute_trade(conn, cache, "ZZZZ", 1, "buy")
            watchlist_service.remove_from_watchlist(conn, "ZZZZ")
            active = watchlist_service.get_active_tickers(conn)
        assert "ZZZZ" in active

    def test_removing_watchlist_entry_with_no_position_drops_it(self, db: Database):
        with db.connect() as conn:
            watchlist_service.remove_from_watchlist(conn, "AAPL")
            active = watchlist_service.get_active_tickers(conn)
        assert "AAPL" not in active

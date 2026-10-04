"""Integration tests for the wired-together FastAPI app in app.main."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Build a fresh app against an isolated DB and run it through its lifespan.

    app.main builds `app` at import time, so DB_PATH must be set before the
    module is (re)imported — reload forces create_app() to run again against
    the patched path instead of reusing a cached module-level `app`.
    """
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LLM_MOCK", "true")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    import app.main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client


class TestHealth:
    def test_health_check(self, client: TestClient):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPortfolioRoutes:
    def test_fresh_portfolio(self, client: TestClient):
        response = client.get("/api/portfolio")
        assert response.status_code == 200
        body = response.json()
        assert body["cash_balance"] == 10000.0
        assert body["positions"] == []

    def test_trade_insufficient_cash_returns_400(self, client: TestClient):
        response = client.post(
            "/api/portfolio/trade", json={"ticker": "NVDA", "quantity": 1_000_000, "side": "buy"}
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "insufficient_cash"

    def test_buy_then_portfolio_reflects_position(self, client: TestClient):
        buy = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        assert buy.status_code == 200

        portfolio = client.get("/api/portfolio").json()
        assert len(portfolio["positions"]) == 1
        assert portfolio["positions"][0]["ticker"] == "AAPL"

    def test_trades_history_lists_executed_trade(self, client: TestClient):
        client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
        trades = client.get("/api/portfolio/trades").json()
        assert len(trades) == 1
        assert trades[0]["ticker"] == "AAPL"

    def test_history_has_seed_snapshot(self, client: TestClient):
        history = client.get("/api/portfolio/history").json()
        assert len(history) >= 1


class TestWatchlistRoutes:
    def test_default_watchlist_has_ten_tickers_with_prices(self, client: TestClient):
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 10
        # Simulator seeds the cache synchronously on start (PLAN.md §6).
        assert all(entry["price"] is not None for entry in body)

    def test_add_ticker_appears_with_price(self, client: TestClient):
        response = client.post("/api/watchlist", json={"ticker": "PYPL"})
        assert response.status_code == 200
        body = response.json()
        pypl = next(e for e in body if e["ticker"] == "PYPL")
        assert pypl["price"] is not None

    def test_remove_ticker(self, client: TestClient):
        client.post("/api/watchlist", json={"ticker": "PYPL"})
        response = client.delete("/api/watchlist/PYPL")
        assert response.status_code == 200
        body = response.json()
        assert all(e["ticker"] != "PYPL" for e in body)

    def test_remove_watchlist_ticker_with_open_position_keeps_streaming(self, client: TestClient):
        client.post("/api/watchlist", json={"ticker": "PYPL"})
        client.post("/api/portfolio/trade", json={"ticker": "PYPL", "quantity": 1, "side": "buy"})
        client.delete("/api/watchlist/PYPL")

        portfolio = client.get("/api/portfolio").json()
        position = next(p for p in portfolio["positions"] if p["ticker"] == "PYPL")
        # Still priced because the position is still open (PLAN.md §6).
        assert position["current_price"] is not None


class TestChatRoute:
    def test_chat_buy_trade_executes_and_updates_portfolio(self, client: TestClient):
        response = client.post("/api/chat", json={"message": "buy 2 AAPL"})
        assert response.status_code == 200
        body = response.json()
        assert body["trades"][0]["ticker"] == "AAPL"
        assert body["trades"][0]["error"] is None

        portfolio = client.get("/api/portfolio").json()
        assert any(p["ticker"] == "AAPL" and p["quantity"] == 2 for p in portfolio["positions"])

    def test_chat_generic_message_has_no_actions(self, client: TestClient):
        response = client.post("/api/chat", json={"message": "how is my portfolio doing?"})
        assert response.status_code == 200
        body = response.json()
        assert body["trades"] == []
        assert body["watchlist_changes"] == []
        assert body["message"]

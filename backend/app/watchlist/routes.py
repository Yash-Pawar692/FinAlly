"""Watchlist API routes (PLAN.md §8)."""

from __future__ import annotations

from fastapi import APIRouter

from app.db import Database
from app.market import MarketDataSource, PriceCache

from . import service
from .schemas import WatchlistAddRequest


def create_watchlist_router(
    db: Database, price_cache: PriceCache, market_source: MarketDataSource
) -> APIRouter:
    """Router factory — injects the Database, PriceCache, and active MarketDataSource."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    async def list_watchlist() -> list[dict]:
        with db.connect() as conn:
            return service.get_watchlist(conn, price_cache)

    @router.post("")
    async def add_ticker(body: WatchlistAddRequest) -> list[dict]:
        ticker = body.ticker.upper().strip()
        with db.connect() as conn:
            service.add_to_watchlist(conn, ticker)
        # Synchronous under the simulator, so the ticker has a price by the
        # time this responds; under Massive it appears on the next poll.
        await market_source.add_ticker(ticker)
        with db.connect() as conn:
            return service.get_watchlist(conn, price_cache)

    @router.delete("/{ticker}")
    async def remove_ticker(ticker: str) -> list[dict]:
        ticker = ticker.upper().strip()
        with db.connect() as conn:
            service.remove_from_watchlist(conn, ticker)
            still_held = service.has_open_position(conn, ticker)
        if not still_held:
            # An open position keeps its price streaming until closed (PLAN.md §6).
            await market_source.remove_ticker(ticker)
        with db.connect() as conn:
            return service.get_watchlist(conn, price_cache)

    return router

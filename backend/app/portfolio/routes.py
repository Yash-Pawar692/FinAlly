"""Portfolio API routes (PLAN.md §8)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import Database
from app.market import PriceCache

from . import service
from .errors import TradeError
from .schemas import TradeRequest


def create_portfolio_router(db: Database, price_cache: PriceCache) -> APIRouter:
    """Router factory — injects the Database and PriceCache without globals."""
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    async def get_portfolio() -> dict:
        with db.connect() as conn:
            return service.get_portfolio(conn, price_cache)

    @router.post("/trade")
    async def post_trade(trade: TradeRequest):
        with db.connect() as conn:
            try:
                return service.execute_trade(conn, price_cache, trade.ticker, trade.quantity, trade.side)
            except TradeError as e:
                return JSONResponse(status_code=400, content={"error": e.code, "message": e.message})

    @router.get("/history")
    async def get_history() -> list[dict]:
        with db.connect() as conn:
            return service.get_history(conn)

    @router.get("/trades")
    async def get_trades() -> list[dict]:
        with db.connect() as conn:
            return service.get_trades(conn)

    return router

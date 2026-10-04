"""Chat API routes (PLAN.md §8-9)."""

from __future__ import annotations

from fastapi import APIRouter

from app.db import Database
from app.market import MarketDataSource, PriceCache

from . import service
from .schemas import ChatApiResponse, ChatRequest


def create_chat_router(db: Database, price_cache: PriceCache, market_source: MarketDataSource) -> APIRouter:
    """Router factory — injects the Database, PriceCache, and active MarketDataSource."""
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("")
    async def post_chat(body: ChatRequest) -> ChatApiResponse:
        with db.connect() as conn:
            return await service.handle_chat_message(conn, price_cache, market_source, body.message)

    return router

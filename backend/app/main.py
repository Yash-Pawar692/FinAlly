"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.chat import create_chat_router
from app.db import Database
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.portfolio import create_portfolio_router
from app.portfolio.service import record_snapshot
from app.watchlist import create_watchlist_router
from app.watchlist import service as watchlist_service

# Loads OPENROUTER_API_KEY / MASSIVE_API_KEY / LLM_MOCK from the project-root
# .env for local dev (PLAN.md §5). In Docker these are already set via
# --env-file, so the root .env isn't present in the image and this is a no-op.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30


async def _snapshot_loop(db: Database, price_cache: PriceCache) -> None:
    """Background task: record a portfolio_snapshots row every 30s (PLAN.md §7)."""
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        try:
            with db.connect() as conn:
                record_snapshot(conn, price_cache)
        except Exception:
            logger.exception("Portfolio snapshot failed")


def create_app() -> FastAPI:
    db = Database()
    price_cache = PriceCache()
    market_source = create_market_data_source(price_cache)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # DB must be ready before the market data source starts, since the
        # active ticker set (watchlist ∪ open positions) comes from it
        # (PLAN.md §7).
        db.init()
        with db.connect() as conn:
            tickers = watchlist_service.get_active_tickers(conn)
        await market_source.start(list(tickers))

        snapshot_task = asyncio.create_task(_snapshot_loop(db, price_cache), name="snapshot-loop")

        yield

        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await market_source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(create_stream_router(price_cache))
    app.include_router(create_portfolio_router(db, price_cache))
    app.include_router(create_watchlist_router(db, price_cache, market_source))
    app.include_router(create_chat_router(db, price_cache, market_source))

    # Static Next.js export, placed here by the Docker build (PLAN.md §11).
    # Absent in local dev until the frontend is built — mounted only if present.
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


app = create_app()

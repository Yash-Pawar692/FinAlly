"""Watchlist: tickers the user is watching, with live prices.

Public API:
    create_watchlist_router - FastAPI router factory
"""

from .routes import create_watchlist_router

__all__ = ["create_watchlist_router"]

"""Chat: LLM-driven portfolio assistant with auto-executed trades and watchlist changes.

Public API:
    create_chat_router - FastAPI router factory
"""

from .routes import create_chat_router

__all__ = ["create_chat_router"]

"""Pydantic models for the chat API and the LLM's structured output (PLAN.md §9)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str


class LlmTradeAction(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class LlmWatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class LlmChatResponse(BaseModel):
    """The exact structured-output schema the LLM is asked to produce (PLAN.md §9)."""

    message: str
    trades: list[LlmTradeAction] = Field(default_factory=list)
    watchlist_changes: list[LlmWatchlistChange] = Field(default_factory=list)


class ExecutedTrade(BaseModel):
    """A trade the LLM requested, annotated with its outcome."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    error: str | None = None


class ExecutedWatchlistChange(BaseModel):
    ticker: str
    action: Literal["add", "remove"]


class ChatApiResponse(BaseModel):
    """What POST /api/chat returns to the frontend."""

    message: str
    trades: list[ExecutedTrade] = Field(default_factory=list)
    watchlist_changes: list[ExecutedWatchlistChange] = Field(default_factory=list)

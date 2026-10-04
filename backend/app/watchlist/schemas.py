"""Pydantic request models for the watchlist API."""

from __future__ import annotations

from pydantic import BaseModel


class WatchlistAddRequest(BaseModel):
    ticker: str

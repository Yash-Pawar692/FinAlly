"""Pydantic request models for the portfolio API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TradeRequest(BaseModel):
    """Body for POST /api/portfolio/trade.

    Quantity is intentionally unconstrained here (no gt=0) so that a
    non-positive quantity reaches service.execute_trade and comes back as
    the invalid_quantity error contract, not a generic 422.
    """

    ticker: str
    quantity: float
    side: Literal["buy", "sell"]

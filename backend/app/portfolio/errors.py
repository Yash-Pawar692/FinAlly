"""Trade validation errors (PLAN.md §8 error contract)."""

from __future__ import annotations


class TradeError(Exception):
    """Raised when a trade fails validation.

    `code` is one of: insufficient_cash, insufficient_shares,
    no_price_available, invalid_quantity — matching the REST error body
    `{"error": code, "message": message}`.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

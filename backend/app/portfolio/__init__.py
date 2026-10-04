"""Portfolio: trade execution, positions, P&L, and history.

Public API:
    create_portfolio_router - FastAPI router factory
    TradeError              - Raised by service.execute_trade on validation failure
"""

from .errors import TradeError
from .routes import create_portfolio_router

__all__ = ["TradeError", "create_portfolio_router"]

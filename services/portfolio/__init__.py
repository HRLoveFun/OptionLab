"""Portfolio domain services — tracked positions and their risk analytics.

Package map:

- ``facade.py``  — CRUD over ``tracked_strategies`` + the live portfolio snapshot
- ``analysis.py``— :class:`PortfolioAnalysisService` (Greeks, P&L, theta decay, VaR)
"""

from .analysis import PortfolioAnalysisService
from .facade import (
    close_position,
    create_position,
    list_positions,
    portfolio_snapshot,
)

__all__ = [
    "PortfolioAnalysisService",
    "create_position",
    "list_positions",
    "close_position",
    "portfolio_snapshot",
]

"""Portfolio Analysis Service — BACKWARD-COMPAT ADAPTER.

All logic has moved to ``services.portfolio_analysis``.  New code should
import from there directly; this module exists only to satisfy existing
callers in ``app.py`` during the transition.
"""

from services.portfolio_analysis import PortfolioAnalysisService

__all__ = ["PortfolioAnalysisService"]

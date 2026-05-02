"""Analysis Service — BACKWARD-COMPAT ADAPTER.

All logic has moved to ``services.market_analysis``.  New code should
import from there directly; this module exists only to satisfy existing
callers in ``app.py`` and ``tests/`` during the transition.
"""

from services.market_analysis import AnalysisService

__all__ = ["AnalysisService"]

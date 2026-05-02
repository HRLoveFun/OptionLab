"""Portfolio analysis sub-package.

New code should import directly from here; the legacy module
``services.portfolio_analysis_service`` is a thin backward-compat adapter.
"""

from ._service import PortfolioAnalysisService

__all__ = ["PortfolioAnalysisService"]

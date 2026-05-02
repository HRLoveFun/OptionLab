"""Market analysis sub-package.

New code should import directly from here; the legacy module
``services.analysis_service`` is a thin backward-compat adapter.
"""

from ._service import AnalysisService

__all__ = ["AnalysisService"]

"""Market projection models.

Domain:    Market Analysis — Projections
Context:
  - Walk-forward projection computation (no rendering).
Contracts:
  - compute_oscillation_projection(data, percentile, target_bias) -> ProjectionResult
  - build_projection_dataframe(...) -> pd.DataFrame
Dependencies UPWARD:
  - core.market.features, core._shared.types
Dependencies DOWNWARD:
  - core.market.charts.projection
"""

from core.market.projections.oscillation import compute_oscillation_projection

__all__ = [
    "compute_oscillation_projection",
]

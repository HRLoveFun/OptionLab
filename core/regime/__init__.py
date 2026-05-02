"""Market regime labeling.

Dependency graph:
    models.py      # RegimeLabel, VolRegime, DirRegime
    classify.py    # Threshold-based classification
    series.py      # Series-level labeling + transitions
"""

from core.regime.classify import classify_direction, classify_vol
from core.regime.models import DirRegime, RegimeLabel, VolRegime
from core.regime.series import (
    SMA_WINDOW,
    SLOPE_LOOKBACK,
    coverage_report,
    label_regime,
    label_series,
    regime_transitions,
)

__all__ = [
    "VolRegime", "DirRegime", "RegimeLabel",
    "classify_vol", "classify_direction", "label_regime",
    "label_series", "regime_transitions", "coverage_report",
    "SMA_WINDOW", "SLOPE_LOOKBACK",
]

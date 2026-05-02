"""Market regime labeling — BACKWARD-COMPATIBILITY SHIM.

NEW CODE SHOULD IMPORT FROM: core.regime
  from core.regime import classify_vol, classify_direction, label_regime, RegimeLabel

This module re-exports the canonical implementation from core.regime.*
to preserve existing import paths.
"""

from core.regime.classify import classify_direction, classify_vol
from core.regime.models import DirRegime, RegimeLabel, VolRegime
from core.regime.series import coverage_report, label_regime, label_series, regime_transitions

__all__ = [
    "VolRegime",
    "DirRegime",
    "RegimeLabel",
    "classify_vol",
    "classify_direction",
    "label_regime",
    "label_series",
    "regime_transitions",
    "coverage_report",
]

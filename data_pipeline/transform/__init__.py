"""TRANSFORM — raw → clean → features.

Domain:    Data Pipeline — Transform
Context:
  - ADR 0011: the processing stage is provider-agnostic — it reads canonical
    ``raw_bars`` / ``clean_bars`` frames and never imports ``providers/``.
  - Domain rules live here: business-day alignment with **no interpolation**
    (invented prices are worse than missing ones — docs/constraints.md §4),
    anomaly flagging, then per-frequency feature engineering.
Contracts:
  - ``cleaning.clean_range`` — raw_bars → clean_bars.
  - ``processing.process_frequencies`` — clean_bars → feature_bars (D/W/ME/QE).
Dependencies UPWARD:
  - store (canonical tables), data_pipeline (PipelineResult)
Dependencies DOWNWARD:
  - orchestrate
"""

from __future__ import annotations

"""Global type aliases and lightweight data contracts.

Domain:    Cross-cutting types
Context:
  - Used by every core sub-package to avoid circular imports.
  - No pandas/numpy here — keep imports minimal.
Contracts:
  - Ticker = str
  - DateRange = tuple[date, date | None]
  - Frequency = Literal["D", "W", "ME", "QE"]
Dependencies UPWARD:
  - typing, datetime
Dependencies DOWNWARD:
  - All core sub-packages
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

Ticker = str
Frequency = Literal["D", "W", "ME", "QE"]
DateRange = tuple[dt.date, dt.date | None]

FREQUENCY_LABELS: dict[Frequency, str] = {
    "D": "Daily",
    "W": "Weekly",
    "ME": "Monthly",
    "QE": "Quarterly",
}

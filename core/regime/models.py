"""Regime data contracts.

Domain:    Market Regime
Contracts:
  - VolRegime, DirRegime (Enum)
  - RegimeLabel (dataclass)
Dependencies UPWARD:
  - enum, dataclasses, datetime
Dependencies DOWNWARD:
  - core.regime.classify, core.regime.series
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import asdict, dataclass
from enum import Enum


class VolRegime(str, Enum):
    LOW = "LOW_VOL"
    MID = "MID_VOL"
    HIGH = "HIGH_VOL"
    STRESS = "STRESS_VOL"
    UNKNOWN = "UNKNOWN_VOL"


class DirRegime(str, Enum):
    UP = "UP_TREND"
    DOWN = "DOWN_TREND"
    CHOP = "CHOP"
    UNKNOWN = "UNKNOWN_DIR"


@dataclass
class RegimeLabel:
    date: dt.date
    vol_regime: VolRegime
    dir_regime: DirRegime
    vix_value: float | None
    sma_20: float | None
    sma_slope_5d: float | None
    close_vs_sma_pct: float | None
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        d["vol_regime"] = self.vol_regime.value
        d["dir_regime"] = self.dir_regime.value
        for k in ("vix_value", "sma_20", "sma_slope_5d", "close_vs_sma_pct"):
            v = d.get(k)
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                d[k] = None
        return d

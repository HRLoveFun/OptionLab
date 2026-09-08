"""Small date helpers shared across core modules.

Domain:    Shared — Date Utilities
Context:
  - ``dte`` was previously duplicated verbatim in four modules
    (``core/decision/candidate.py``, ``core/decision/market_data.py``,
    ``core/options/chain/analyzer.py``, ``core/options/chain/html_tables.py``);
    consolidated here so DTE semantics have a single definition.

Contracts:
  - dte(expiry_str) -> int  (calendar days, floored at 0)

Dependencies UPWARD:
  - core.options.chain.*, core.decision.*, services.options.preload
Dependencies DOWNWARD:
  - None (leaf module)
"""

from __future__ import annotations

import datetime as dt

_DTE_FORMAT = "%Y-%m-%d"


def dte(expiry_str: str) -> int:
    """Calendar days from today until *expiry_str* (``YYYY-MM-DD``), floored at 0."""
    today = dt.date.today()
    exp = dt.datetime.strptime(expiry_str, _DTE_FORMAT).date()
    return max(0, (exp - today).days)

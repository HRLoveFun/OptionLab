"""Market domain services — OHLCV analysis, charts, signals and the analysis form.

Package map:

- ``facade.py``     — :class:`MarketService` (ticker validation, spot, market review)
- ``analysis/``     — :class:`AnalysisService` and the streaming slice builders
- ``charts.py``     — :class:`ChartService` + the matplotlib base64 LRU cache
- ``signals.py``    — HV/RSI/Bollinger signal bundle
- ``form.py``       — raw form payload → typed params
- ``validation.py`` — validation rules applied before any computation
- ``health.py``     — market-data cache quality (freshness / NaN / row counts)
- ``dispatch.py``   — the shared ``/render/<kind>`` handler (imported directly;
  it pulls in Flask and the options domain, so it is not re-exported here)
"""

from .charts import ChartService
from .facade import MarketService
from .form import FormService
from .signals import get_signals
from .validation import ValidationService

__all__ = [
    "ChartService",
    "MarketService",
    "FormService",
    "ValidationService",
    "get_signals",
]

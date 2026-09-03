"""Options domain services — chain analytics, expiry simulation and strategies.

Package map:

- ``chain.py``      — :class:`OptionsChainService` (single network boundary for chains)
- ``preload.py``    — short-lived chain cache feeding the position dropdowns
- ``simulation.py`` — ``run_simulation`` for ``POST /api/simulate_expiry``
- ``strategies.py`` — template registry + JSON-safe strategy analysis
- ``builder.py``    — instantiates templates against real chain strikes
"""

from .builder import build_from_chain
from .chain import OptionsChainService
from .simulation import run_simulation
from .strategies import analyze, list_strategies

__all__ = [
    "OptionsChainService",
    "run_simulation",
    "analyze",
    "list_strategies",
    "build_from_chain",
]

"""Multi-leg option strategies.

Domain:    Strategy Analysis
Dependency graph:
    models.py      # Leg dataclass
    factories.py   # Strategy constructors
    payoff.py      # Expiration P&L
    greeks.py      # Net Greeks
    prob_profit.py # PoP under BS
"""

from core.strategies.analyze import analyze_strategy
from core.strategies.factories import *
from core.strategies.greeks import net_greeks
from core.strategies.payoff import payoff_at_expiration
from core.strategies.prob_profit import prob_profit

__all__ = [
    "Leg",
    "long_call", "long_put", "short_call", "short_put",
    "bull_call_spread", "bear_put_spread",
    "bear_call_spread", "bull_put_spread",
    "long_straddle", "long_strangle",
    "short_straddle", "short_strangle",
    "iron_condor", "long_butterfly", "calendar_spread",
    "payoff_at_expiration",
    "net_greeks",
    "prob_profit",
    "analyze_strategy",
]

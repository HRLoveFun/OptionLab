"""Flask Blueprints for OptionLab HTTP routes.

Thin routing layer — each blueprint delegates to services/core modules.
App.py registers these blueprints and remains the single import point
for test fixtures.
"""

from routes.core import bp as core_bp
from routes.data import bp as data_bp
from routes.market import bp as market_bp
from routes.options import bp as options_bp
from routes.portfolio import bp as portfolio_bp
from routes.regime import bp as regime_bp
from routes.strategies import bp as strategies_bp

__all__ = [
    "core_bp",
    "data_bp",
    "market_bp",
    "options_bp",
    "portfolio_bp",
    "regime_bp",
    "strategies_bp",
]

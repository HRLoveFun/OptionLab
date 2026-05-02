"""Generic input validators.

Domain:    Cross-cutting validation
Context:
  - Reusable validators for numeric ranges, probabilities, etc.
Contracts:
  - validate_positive(x, name) -> float
  - validate_probability(x, name) -> float
Dependencies UPWARD:
  - None
Dependencies DOWNWARD:
  - core.market, core.options, core.strategies
"""

from __future__ import annotations


def validate_positive(value: float, name: str = "value") -> float:
    """Ensure *value* is a positive finite number."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got {value}")
    return float(value)


def validate_probability(value: float, name: str = "value") -> float:
    """Ensure *value* is in [0, 1]."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric, got {type(value).__name__}")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return float(value)

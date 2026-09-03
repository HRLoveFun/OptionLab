"""Domain-wide constants for market analysis application."""

# CONSTRAINT: domain-wide defaults surfaced in the UI form; mirrors the
# assessment thresholds documented in docs/glossary.md / docs/constraints.md §5.
DEFAULT_RISK_THRESHOLD = 90
DEFAULT_ROLLING_WINDOW = 120
DEFAULT_FREQUENCY = "ME"
DEFAULT_TICKER = "^SPX"
DEFAULT_SIDE_BIAS = "Neutral"
DEFAULT_PERIODS = [12, 36, 60, "ALL"]

FREQUENCY_DISPLAY = {"D": "Daily", "W": "Weekly", "ME": "Monthly", "QE": "Quarterly"}

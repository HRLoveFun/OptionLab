"""Application constants and configuration"""

# Market analysis constants
DEFAULT_RISK_THRESHOLD = 90
DEFAULT_FREQUENCY = 'W'
DEFAULT_PERIODS = [12, 36, 60, "ALL"]

# Market tickers for review
MARKET_REVIEW_TICKERS = [
    'DX-Y.NYB',  # US Dollar Index
    '^TNX',      # 10-Year Treasury
    '^GSPC',     # S&P 500
    'GC=F',      # Gold
    '000300.SS', # CSI 300
    '^STOXX',    # STOXX Europe 600
    '^HSI',      # Hang Seng
    '^N225'      # Nikkei 225
]

# Frequency mappings
FREQUENCY_DISPLAY = {
    'D': 'Daily',
    'W': 'Weekly',
    'ME': 'Monthly',
    'QE': 'Quarterly'
}

# Time period mappings for calculations
TIME_PERIODS = {
    '1M': 22,    # ~1 month in trading days
    '1Q': 66,    # ~1 quarter in trading days
    'YTD': None, # Year to date
    'ETD': None  # Entire time period
}

# Chart configuration
CHART_CONFIG = {
    'dpi': 300,
    'format': 'png',
    'bbox_inches': 'tight',
    'correlation_matrix_size': (16, 12),
    'default_figsize': (12, 8)
}

# Table styling classes
TABLE_CLASSES = 'table table-striped'

# Option types
OPTION_TYPES = {
    'SC': 'Short Call',
    'SP': 'Short Put',
    'LC': 'Long Call',
    'LP': 'Long Put'
}
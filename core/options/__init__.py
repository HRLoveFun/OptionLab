"""Options Analysis Domain.

Dependency graph (flows downward):
    models.py             # Data contracts (Greeks, OptionLeg)
    greeks/               # Pure Black-Scholes computation
    ├── black_scholes.py
    └── portfolio.py
    chain/                # Option-chain metrics (no charts)
    ├── metrics.py
    ├── liquidity.py
    └── term_structure.py
    charts/               # Matplotlib rendering only
    ├── iv_smile.py
    ├── iv_term.py
    ├── iv_surface.py
    ├── skew.py
    ├── oi_volume.py
    └── pcr.py
"""

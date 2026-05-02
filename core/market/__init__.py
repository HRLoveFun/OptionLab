"""Market Analysis Domain.

Dependency graph (flows downward):
    data_context          # PriceDynamic — data fetching & resampling
    features/             # Pure numeric feature computation
    ├── osc.py
    ├── returns.py
    ├── volatility.py
    └── regime_segments.py
    projections/          # Depends on features/
    └── oscillation.py
    charts/               # Depends on features/ + projections/
    ├── scatter_osc.py
    ├── dynamics.py
    ├── volatility.py
    ├── projection.py
    └── correlation.py
"""

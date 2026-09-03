"""Services layer — Flask-aware orchestration between ``routes/`` and ``core/``.

WHY the domain packaging: ``services/`` used to be a flat bag of
``*_service.py`` modules where every file shared one namespace and the layer
boundaries were only visible from the module names. Grouping by business
domain makes the ownership explicit and keeps each package's surface small
enough to reason about. The rule is unchanged — a service may reach down into
``core`` / ``data_pipeline`` / ``utils`` and sideways inside ``services``, but
never up into ``routes`` or ``app`` (ADR 0001).

Domain packages (``facade.py`` is the entry point of each):

- ``services.market``    — OHLCV analysis, matplotlib charting, signals, the
  analysis form, and the streaming ``/render/<kind>`` dispatch.
- ``services.options``   — option chain, chain preload, expiry simulation,
  strategy templates and chain-driven strategy building.
- ``services.portfolio`` — tracked positions plus their Greeks/P&L analytics.
- ``services.regime``    — market-regime labelling (VIX/SPY) and the
  ``regime_log`` persistence helpers under ``services.regime.ops``.
"""

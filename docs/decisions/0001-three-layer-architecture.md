# 0001. Three-Layer Architecture

- **Status**: Accepted
- **Date**: 2025-01-15 (retroactive)
- **Deciders**: project author

## Context

The codebase mixes data fetching, computation, and HTTP handling. Without discipline,
Flask request objects leak into computation modules, computation modules import from each
other circularly, and a small change in one place ripples unpredictably.

## Options Considered

1. **Single-layer (everything in `app.py`)** — fast initially, unmaintainable beyond ~1000 LOC.
2. **Two-layer (app + helpers)** — no clear home for compute vs. I/O, still tangles.
3. **Three-layer (app → services → core → data_pipeline)** — clear direction, easy to test.
4. **Hexagonal / Clean Architecture (full ports & adapters)** — overkill for a personal project.

## Decision

Three-layer architecture with strict downward-only imports:

```
app.py            (Flask routing, request/response)
   ↓
services/         (orchestration, formatting for routes)
   ↓
core/             (pure computation, no Flask, no I/O)
   ↓
data_pipeline/    (download, clean, persist, query)
```

Enforced by:
- The architecture-guard instructions in `.github/instructions/architecture-guard.instructions.md`.
- The import-guard hook in `.github/data/import_violations.log`.

## Consequences

- **Positive**: every module has one clear responsibility; tests can target a layer.
- **Positive**: AI code reviewers can be told "this module belongs to layer X" and infer the rules.
- **Trade-off**: one extra hop for trivial endpoints (e.g. `/health` still goes through `services/health_service.py`). Acceptable.
- **Trade-off**: enforcing direction by convention, not by package private/public. We rely on hooks + reviews.

## References

- `.github/copilot-instructions.md` — Architecture Rules section
- `.github/instructions/architecture-guard.instructions.md`

---
description: "Use when adding imports, moving code between layers, refactoring module boundaries, or creating new modules in the OptionView project."
---

# Architecture Guard

## Import Direction (Strict)

```
app.py → services/ → core/ → data_pipeline/
```

**Allowed imports (downstream only):**
| Module | Can import from |
|--------|----------------|
| `app.py` | `services/*`, `utils/*` |
| `services/*` | `core/*`, `data_pipeline/*`, `utils/*` |
| `core/*` | `data_pipeline/*`, `utils/*` |
| `data_pipeline/*` | `utils/*` (and standard library) |
| `utils/*` | standard library only |

**Forbidden imports:**
- `data_pipeline/` must **never** import from `services/` or `core/`
- `core/` must **never** import from `services/` or `app.py`
- `core/` must **never** import `flask` or handle HTTP requests
- `services/` must **never** import from `app.py`

## Layer Responsibilities
- **`data_pipeline/`**: Download, clean, process, DB access — pure data I/O
- **`core/`**: Computation logic (analyzers, Greeks, price dynamics) — no Flask, no HTTP
- **`services/`**: Orchestrate core modules, format results for routes — no direct DB writes
- **`app.py`**: Flask routes, request/response handling — delegates to services

## New Module Placement
- Data fetching/storage → `data_pipeline/`
- Math/analysis/computation → `core/`
- Combining multiple core results → `services/`
- HTTP endpoint → `app.py`
- Shared constants/helpers → `utils/`

## Circular Import Prevention
- If module A needs module B and B needs A → extract shared logic to `utils/` or a new sub-module
- Use late imports (`import inside function`) only as last resort — prefer restructuring

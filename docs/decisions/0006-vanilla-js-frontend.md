# 0006. Vanilla JS Frontend, No Build Step

- **Status**: Accepted
- **Date**: 2025-01-15 (retroactive)
- **Deciders**: project author

## Context

The frontend has ~10 panels (charts, option-chain table, position editor, regime view).
State is mostly per-panel; cross-panel coordination is light (an event bus + a few stores).

## Options Considered

1. **React (CRA / Vite)** — industry standard, but adds a build step, node_modules, lockfile, and a ~150KB runtime for what is essentially a dashboard.
2. **Svelte / Solid** — smaller runtime, still a build step.
3. **Vue** — middle ground, still a build step.
4. **Vanilla JS + ES modules + Web Components** — zero deps, browser-native, no build.
5. **HTMX** — server-driven; awkward for the chart-heavy interactions we have.

## Decision

**Vanilla JS, ES modules, native `customElements`** where panel state is non-trivial.
- `static/main.js` is the entry point loaded by `templates/index.html`.
- `static/components/` for custom elements.
- `static/state/` for shared stores; `static/eventBus.js` for pub/sub.
- Charts rendered server-side as base64 PNGs to avoid a charting library.

## Consequences

- **Positive**: zero install for frontend; `python app.py` is the only dev command.
- **Positive**: forced minimalism keeps the UI fast.
- **Trade-off**: no JSX / SFC ergonomics. Hand-written DOM manipulation in places.
- **Trade-off**: no off-the-shelf component libraries. Custom CSS in `static/styles.css`.
- Tests: Vitest for the few JS modules with logic worth testing (see `vitest.config.js`).

## References

- `templates/index.html`
- `static/main.js`, `static/components/`
- `services/chart_service.py` (server-side chart rendering)

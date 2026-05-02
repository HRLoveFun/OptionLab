# Frontend Architecture Convergence Plan

The frontend currently mixes three styles inherited from incremental
refactors:

1. **Vanilla module scripts** (`static/main.js`, `position.js`, `regime.js`,
   `option-chain.js`, `market_review.js`) — direct DOM
   manipulation with `document.querySelector` and ad-hoc fetches.
2. **Hand-rolled state machines** under `static/state/` — pub/sub via
   `eventBus.js`, panel/tab/cache state encapsulated in modules.
3. **Component scaffolding** under `static/components/` and
   `static/features/` — partially extracted UI fragments.

This file documents the **target** structure so future work converges
toward a single style without a Big Rewrite.

## Target

```
static/
  api.js          ← thin fetch wrapper, error normalisation
  cache.js        ← request-level memoisation
  eventBus.js     ← pub/sub primitive
  utils.js        ← shared helpers (no DOM)
  state/          ← canonical, single source of truth
    store.js              (root store, Redux-lite)
    panelState.js         (open/closed panels)
    optionChainState.js   (selected ticker / expiry / strike)
    chainCacheState.js    (cached chain payloads)
    abortRegistry.js      (cancel-token store)
  components/    ← reusable UI blocks (charts, tables, buttons)
  features/      ← page-level feature shells that wire state→components
  *.js (root)    ← entry points only; no business logic
```

## Migration Rules (apply opportunistically)

* **New features** must read/write through `state/` modules — do not
  introduce module-local mutable state in feature shells.
* **Existing root scripts** (`option-chain.js`, `position.js`, etc.) stay
  as-is until they need a substantial change; then migrate the touched
  flow to `state/` + `components/`.
* **Charts**: use Chart.js for line/scatter (loaded as a CDN script tag in
  `index.html`). The new JSON endpoints
  `/api/strategy/analyze`, `/api/options_chart/iv_smile`, and
  `/api/options_chart/oi_profile` return data only — no base64 PNGs — so
  rendering belongs entirely on the client.
* **No new HTMX/Alpine surfaces** unless an existing partial already uses
  them. The convergence direction is: server returns JSON, client renders.

## What This Pass Did NOT Do

* Did not migrate `position.js` or `regime.js` — they work
  and rewriting risks regression.
* Did not consolidate the dozen of `*State.js` files — they are already
  internally consistent; consolidate when their consumers are migrated.
* Did not introduce a build step. Plain ES modules served as static files
  remain the deployment unit.

## Next Concrete Steps (when time permits)

1. Delete `static/eventBus.js` if `state/store.js` covers all listeners.
2. Move `option-chain.js` rendering into `components/optionChainTable.js`
   driven by `state/optionChainState.js`.
3. Replace remaining server-side matplotlib options charts with
   Chart.js components using the new JSON endpoints.

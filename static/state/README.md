# static/state/

Centralized client-side state, replacing ad-hoc globals like
`window._chainCache`, `window._mrLoaded`, `let _ocChainData`, etc.

Each module is a classic-script IIFE that attaches itself onto a single
namespace `window.appState`. State changes emit events on the shared bus
(`window.bus` from eventBus.js) so subscribers can react instead of
polling globals.

## Modules

| Module                | Namespace              | Replaces                                   |
| --------------------- | ---------------------- | ------------------------------------------ |
| `store.js`            | `appState`             | namespace bootstrap                        |
| `chainCacheState.js`  | `appState.chainCache`  | `window._chainCache`, `_chainCacheGet/Set` |
| `optionChainState.js` | `appState.optionChain` | `_ocChainData`, `_ocActivExp`, `_ocAbort`  |
| `oddsChainState.js`   | `appState.oddsChain`   | `_oddsChainData`, `_oddsAbort`             |
| `abortRegistry.js`    | `appState.aborts`      | `_gameAbort`, `_portfolioAbort`            |
| `tabFlagsState.js`    | `appState.tabFlags`    | `_mrLoaded`, `_ocAutoLoaded`, ...          |

## Load order

In `templates/index.html`:

```html
<script src="eventBus.js"></script>
<script src="api.js"></script>
<script src="state/store.js"></script>
<script src="state/chainCacheState.js"></script>
<script src="state/optionChainState.js"></script>
<script src="state/oddsChainState.js"></script>
<script src="state/abortRegistry.js"></script>
<script src="state/tabFlagsState.js"></script>
<!-- feature scripts: utils.js, position.js, option-chain.js, ... -->
```

## Migration policy

Migrate one variable at a time. Until all callers are migrated, keep a
thin shim referencing the new state module so partially-migrated callers
keep working. Mark any unmigrated callers with `// TODO(state): ...`.

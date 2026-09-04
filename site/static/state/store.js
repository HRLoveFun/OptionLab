/* state/store.js — central state namespace bootstrap.
 *
 * Replaces ad-hoc globals (window._chainCache, window._mrLoaded, file-scoped
 * `let _ocChainData`, etc.) with a single `window.appState` namespace.
 *
 * Design:
 *   - Each sub-module (chainCache, optionChain, oddsChain, tabFlags, aborts)
 *     attaches itself onto `window.appState.<name>` after this file loads.
 *   - State changes emit `state:<key>` events on the shared bus so components
 *     can react instead of polling globals.
 *
 * Load order (in templates/index.html):
 *   eventBus.js -> api.js -> state/store.js -> state/<modules> -> features
 */
(function (root) {
    'use strict';

    if (root.appState) return;   // idempotent

    const bus = root.bus || root.eventBus;
    if (!bus) {
        // Fail loud — state modules require the bus.
        throw new Error('[state/store] eventBus.js must load before state/store.js');
    }

    root.appState = {
        _bus: bus,
        // Sub-modules register themselves here. Documented for discoverability:
        //   chainCache  -> state/chainCacheState.js
        //   optionChain -> state/optionChainState.js
        //   oddsChain   -> state/oddsChainState.js
        //   tabFlags    -> state/tabFlagsState.js
        //   aborts      -> state/abortRegistry.js
    };
})(window);

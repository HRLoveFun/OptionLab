/* state/tabFlagsState.js — first-load flags for lazy tabs.
 *
 * Replaces `window._mrLoaded`, `window._ocAutoLoaded`, `window._oddsAutoLoaded`,
 * `window._regimeLoaded` flags scattered in templates/index.html.
 *
 * API:
 *   appState.tabFlags.isLoaded(tab)   -> bool
 *   appState.tabFlags.markLoaded(tab)
 *   appState.tabFlags.reset(tab)      -> reset a single flag (for ticker change)
 *   appState.tabFlags.resetAll()
 *
 * Known tabs: 'market_review', 'option_chain', 'odds', 'regime'
 */
(function (root) {
    'use strict';

    const _flags = new Set();

    function isLoaded(tab) { return _flags.has(tab); }
    function markLoaded(tab) {
        _flags.add(tab);
        root.bus.emit('tab_flags:changed', { tab, loaded: true });
    }
    function reset(tab) {
        if (_flags.delete(tab)) {
            root.bus.emit('tab_flags:changed', { tab, loaded: false });
        }
    }
    function resetAll() {
        _flags.clear();
        root.bus.emit('tab_flags:reset_all');
    }

    if (!root.appState) throw new Error('[state/tabFlagsState] state/store.js must load first');
    root.appState.tabFlags = { isLoaded, markLoaded, reset, resetAll };
})(window);

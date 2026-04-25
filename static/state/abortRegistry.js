/* state/abortRegistry.js — keyed AbortController registry.
 *
 * Replaces ad-hoc `let _gameAbort = null`, `let _portfolioAbort = null`
 * patterns. Calling `begin(key)` aborts any prior request bound to the
 * same key and returns a fresh AbortSignal.
 *
 * Note: `api.abort(key)` exists in api.js for requests routed through that
 * wrapper. This registry is for raw `fetch()` callsites that have not yet
 * been migrated to api.js.
 *
 * API:
 *   appState.aborts.begin(key) -> AbortSignal
 *   appState.aborts.abort(key)
 *   appState.aborts.abortAll()
 */
(function (root) {
    'use strict';

    const _controllers = new Map();   // key -> AbortController

    function begin(key) {
        if (!key) return new AbortController().signal;
        const prev = _controllers.get(key);
        if (prev) { try { prev.abort(); } catch (_) { /* ignore */ } }
        const ctrl = new AbortController();
        _controllers.set(key, ctrl);
        return ctrl.signal;
    }

    function abort(key) {
        const ctrl = _controllers.get(key);
        if (!ctrl) return;
        try { ctrl.abort(); } catch (_) { /* ignore */ }
        _controllers.delete(key);
    }

    function abortAll() {
        for (const ctrl of _controllers.values()) {
            try { ctrl.abort(); } catch (_) { /* ignore */ }
        }
        _controllers.clear();
    }

    if (!root.appState) throw new Error('[state/abortRegistry] state/store.js must load first');
    root.appState.aborts = { begin, abort, abortAll };
})(window);

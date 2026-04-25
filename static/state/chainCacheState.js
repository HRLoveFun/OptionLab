/* state/chainCacheState.js — preloaded option-chain cache per ticker.
 *
 * Replaces `window._chainCache` and the legacy `_chainCacheGet/_chainCacheSet`
 * helpers that lived in static/utils.js.
 *
 * API:
 *   appState.chainCache.get(ticker)   -> cached entry or null (TTL-aware)
 *   appState.chainCache.set(ticker, data)
 *   appState.chainCache.has(ticker)
 *   appState.chainCache.clear()
 *
 * Events:
 *   'chain_cache:set'    payload = { ticker, data }
 *   'chain_cache:cleared'
 */
(function (root) {
    'use strict';

    const TTL_MS = 5 * 60 * 1000;
    const _store = new Map();   // ticker -> { ...data, _ts }

    function get(ticker) {
        if (!ticker) return null;
        const entry = _store.get(ticker);
        if (!entry) return null;
        if (Date.now() - entry._ts > TTL_MS) {
            _store.delete(ticker);
            return null;
        }
        return entry;
    }

    function set(ticker, data) {
        if (!ticker || !data) return;
        const entry = { ...data, _ts: Date.now() };
        _store.set(ticker, entry);
        root.bus.emit('chain_cache:set', { ticker, data: entry });
    }

    function has(ticker) {
        return get(ticker) !== null;
    }

    function clear() {
        _store.clear();
        root.bus.emit('chain_cache:cleared');
    }

    if (!root.appState) throw new Error('[state/chainCacheState] state/store.js must load first');
    root.appState.chainCache = { get, set, has, clear, TTL_MS };
})(window);

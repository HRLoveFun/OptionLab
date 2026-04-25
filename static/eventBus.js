/* eventBus.js — tiny pub/sub + shared state container.
 *
 * Replaces scattered globals like window._ocChainData, window._gameAbort,
 * window._chainCache, etc. Keep state inside `bus.state` and emit events
 * when it changes; subscribers react instead of reaching into globals.
 *
 * Usage:
 *   bus.on('option_chain:loaded', (data) => { ... });
 *   bus.emit('option_chain:loaded', data);
 *   bus.state.set('optionChain', data);
 *   const cached = bus.state.get('optionChain');
 *
 * Events used in this codebase (canonical names):
 *   'option_chain:loaded'      payload = { ticker, expirations, chain, spot }
 *   'option_chain:cleared'     payload = { ticker }
 *   'odds_chain:loaded'        payload = { ticker, ... }
 *   'game:started' / 'game:finished' / 'game:error'
 *   'market_review:loaded'     payload = { ticker }
 *   'ticker:changed'           payload = { ticker }
 */
(function (root) {
    'use strict';

    const _listeners = new Map();   // event -> Set<fn>
    const _state = new Map();       // key -> any

    function on(event, fn) {
        if (!_listeners.has(event)) _listeners.set(event, new Set());
        _listeners.get(event).add(fn);
        return () => off(event, fn);
    }

    function once(event, fn) {
        const wrapper = (payload) => {
            off(event, wrapper);
            fn(payload);
        };
        return on(event, wrapper);
    }

    function off(event, fn) {
        const set = _listeners.get(event);
        if (!set) return;
        set.delete(fn);
        if (set.size === 0) _listeners.delete(event);
    }

    function emit(event, payload) {
        const set = _listeners.get(event);
        if (!set) return;
        // copy to avoid mutation during iteration
        for (const fn of Array.from(set)) {
            try { fn(payload); }
            catch (err) {
                // swallow so one bad listener doesn't break the rest
                if (window.console) console.error(`[eventBus] listener for "${event}" threw:`, err);
            }
        }
    }

    const state = {
        get(key, fallback) { return _state.has(key) ? _state.get(key) : fallback; },
        set(key, value) {
            _state.set(key, value);
            emit(`state:${key}`, value);
            return value;
        },
        has(key) { return _state.has(key); },
        delete(key) {
            const had = _state.delete(key);
            if (had) emit(`state:${key}`, undefined);
            return had;
        },
        clear() { _state.clear(); },
    };

    const bus = { on, once, off, emit, state };

    root.bus = bus;
    root.eventBus = bus;   // alias
})(window);

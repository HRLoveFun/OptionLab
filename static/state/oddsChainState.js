/* state/oddsChainState.js — Odds tab state.
 *
 * Replaces `_oddsChainData`, `_oddsAbort` globals in static/option-chain.js.
 * Mirrors optionChainState API.
 *
 * Events:
 *   'odds_chain:loaded'  payload = data
 *   'odds_chain:cleared'
 */
(function (root) {
    'use strict';

    let _data = null;
    let _abort = null;

    function getData() { return _data; }
    function setData(d) {
        _data = d;
        root.bus.emit('odds_chain:loaded', d);
    }
    function beginRequest() {
        if (_abort) { try { _abort.abort(); } catch (_) { /* ignore */ } }
        _abort = new AbortController();
        return _abort.signal;
    }
    function abort() {
        if (_abort) {
            try { _abort.abort(); } catch (_) { /* ignore */ }
            _abort = null;
        }
    }
    function reset() {
        _data = null;
        abort();
        root.bus.emit('odds_chain:cleared');
    }

    if (!root.appState) throw new Error('[state/oddsChainState] state/store.js must load first');
    root.appState.oddsChain = { getData, setData, beginRequest, abort, reset };
})(window);

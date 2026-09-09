/* state/payoffRatioState.js — Payoff Ratio tab state.
 *
 * Replaces `_oddsChainData`, `_oddsAbort` globals in static/option-chain.js.
 * Mirrors optionChainState API.
 *
 * Events:
 *   'payoff_ratio:loaded'  payload = data
 *   'payoff_ratio:cleared'
 */
(function (root) {
    'use strict';

    let _data = null;
    let _abort = null;

    function getData() { return _data; }
    function setData(d) {
        _data = d;
        root.bus.emit('payoff_ratio:loaded', d);
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
        root.bus.emit('payoff_ratio:cleared');
    }

    if (!root.appState) throw new Error('[state/payoffRatioState] state/store.js must load first');
    root.appState.payoffRatio = { getData, setData, beginRequest, abort, reset };
})(window);

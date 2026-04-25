/* state/optionChainState.js — Option Chain tab state.
 *
 * Replaces file-scoped `_ocChainData`, `_ocActivExp`, `_ocAbort` globals
 * in static/option-chain.js with explicit accessors.
 *
 * API:
 *   appState.optionChain.getData()   -> { expirations, chain, spot } | null
 *   appState.optionChain.setData(d)
 *   appState.optionChain.getActiveExp() / setActiveExp(exp)
 *   appState.optionChain.beginRequest() -> AbortSignal (auto-aborts prior)
 *   appState.optionChain.abort()
 *   appState.optionChain.reset()
 *
 * Events:
 *   'option_chain:loaded'  payload = data
 *   'option_chain:cleared'
 *   'option_chain:exp_changed' payload = exp
 */
(function (root) {
    'use strict';

    let _data = null;
    let _activeExp = null;
    let _abort = null;

    function getData() { return _data; }
    function setData(d) {
        _data = d;
        root.bus.emit('option_chain:loaded', d);
    }
    function getActiveExp() { return _activeExp; }
    function setActiveExp(exp) {
        _activeExp = exp;
        root.bus.emit('option_chain:exp_changed', exp);
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
        _activeExp = null;
        abort();
        root.bus.emit('option_chain:cleared');
    }

    if (!root.appState) throw new Error('[state/optionChainState] state/store.js must load first');
    root.appState.optionChain = {
        getData, setData,
        getActiveExp, setActiveExp,
        beginRequest, abort, reset,
    };
})(window);

/* state/panelState.js — four-state machine for async panels.
 *
 * Phases (canonical, exhaustive — no implicit "hidden" phase):
 *   'idle'    — initial state, before any action; show empty/help text
 *   'loading' — request in flight; show skeleton/spinner
 *   'loaded'  — request succeeded with data; show content
 *   'error'   — request failed; show error banner
 *   'empty'   — request succeeded but returned nothing meaningful
 *
 * Two surfaces:
 *
 * 1. Imperative (feature scripts):
 *      appState.panels.set('option_chain', 'loading');
 *      appState.panels.set('option_chain', 'loaded', { data });
 *      appState.panels.set('option_chain', 'error',  { message: 'Network error' });
 *
 *    Each call emits `panel:<id>` on the bus with payload
 *    `{ phase, message, data }`. The previous phase is stored so reads via
 *    `appState.panels.get(id)` are cheap.
 *
 * 2. Declarative (Alpine, in templates):
 *      <div x-data="panelState('option_chain')">
 *        <div x-show="phase === 'loading'"> ... skeleton ... </div>
 *        <div x-show="phase === 'error'"   x-text="message"></div>
 *        <div x-show="phase === 'loaded'"> ... content ... </div>
 *        <div x-show="phase === 'idle' || phase === 'empty'"> ... empty ... </div>
 *      </div>
 *
 *    The Alpine factory subscribes to `panel:<id>` and updates `phase`,
 *    `message`. There is NO sixth state — `x-show` only ever evaluates the
 *    five canonical phases above; one block must always be visible.
 *
 * Initial phase defaults to 'idle'. Pass an override:
 *      <div x-data="panelState('option_chain', 'loading')">
 */
(function (root) {
    'use strict';

    const VALID_PHASES = new Set(['idle', 'loading', 'loaded', 'error', 'empty']);
    const _state = new Map();   // id -> { phase, message, data }

    function set(id, phase, opts) {
        if (!id) throw new Error('[panels.set] id is required');
        if (!VALID_PHASES.has(phase)) {
            throw new Error(`[panels.set] invalid phase "${phase}" for "${id}"; must be one of ${[...VALID_PHASES].join(', ')}`);
        }
        const payload = {
            phase,
            message: (opts && opts.message) || '',
            data: opts && opts.data,
        };
        _state.set(id, payload);
        root.bus.emit(`panel:${id}`, payload);
        return payload;
    }

    function get(id) {
        return _state.get(id) || { phase: 'idle', message: '', data: undefined };
    }

    if (!root.appState) throw new Error('[state/panelState] state/store.js must load first');
    root.appState.panels = { set, get, PHASES: [...VALID_PHASES] };

    /* Alpine factory.
     * Used in templates as `x-data="panelState('option_chain', 'idle')"`.
     * The returned object exposes:
     *   phase        — current phase ('idle'|'loading'|'loaded'|'error'|'empty')
     *   message      — last status/error message
     *   is(name)     — convenience for `phase === name`
     *
     * Auto-subscribes on `init()` so feature scripts can drive UI by calling
     * `appState.panels.set(id, ...)` without touching the DOM.
     */
    root.panelState = function panelState(id, initialPhase) {
        const initial = initialPhase || 'idle';
        if (!VALID_PHASES.has(initial)) {
            throw new Error(`[panelState] invalid initial phase "${initial}" for "${id}"`);
        }
        return {
            phase: initial,
            message: '',
            init() {
                // hydrate from any state already set before Alpine boots
                const existing = _state.get(id);
                if (existing) {
                    this.phase = existing.phase;
                    this.message = existing.message;
                }
                root.bus.on(`panel:${id}`, (payload) => {
                    this.phase = payload.phase;
                    this.message = payload.message || '';
                });
            },
            is(name) { return this.phase === name; },
        };
    };
})(window);

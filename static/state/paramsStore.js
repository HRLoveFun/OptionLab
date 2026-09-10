/* state/paramsStore.js — factory for module-scoped parameter groups (batch B7).
 *
 * One store per parameter group, each with its OWN localStorage key:
 *   marketParams      -> state/marketParamsState.js      (horizon + frequency)
 *   assessmentParams  -> state/assessmentParamsState.js  (Assessment knobs)
 *   optionFilter      -> state/optionFilterState.js      (chain filters + refresh)
 *
 * Contract (docs/frontend_architecture.md, ADR 0012):
 *   - HARD REQUIREMENT: `hydrate()` runs at *parse time*. The scripts sit at the
 *     end of <body>, so the toolbars already exist; hydrating on DOMContentLoaded
 *     would be too late, because HTMX processes its `hx-trigger="load"`
 *     placeholders (and serialises `hx-include`) on that same event.
 *   - a change persists the whole group and emits `module:params-changed` with
 *     `{ group, modules }` on the bus; static/moduleParams.js re-issues exactly
 *     those modules' /render calls, so changing one module's controls re-runs
 *     only that module.
 *   - CONSTRAINT: every localStorage access is guarded — a browser with storage
 *     denied must degrade to "not persisted", never throw (ADR 0006: no build
 *     step, no polyfills).
 */
(function (root) {
    'use strict';

    const bus = root.bus || root.eventBus;
    if (!bus) throw new Error('[state/paramsStore] eventBus.js must load before the params stores');

    function _read(storageKey, defaults) {
        const out = Object.assign({}, defaults);
        try {
            const raw = root.localStorage.getItem(storageKey);
            if (!raw) return out;
            const parsed = JSON.parse(raw);
            if (!parsed || typeof parsed !== 'object') return out;
            Object.keys(defaults).forEach((key) => {
                if (parsed[key] !== undefined && parsed[key] !== null) out[key] = String(parsed[key]);
            });
        } catch (_) {
            /* unreadable / denied storage: fall back to defaults */
        }
        return out;
    }

    function _write(storageKey, state) {
        try {
            root.localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (_) {
            /* not fatal: the group just will not be remembered */
        }
    }

    /**
     * @param {{name:string, storageKey:string, defaults:object, inputIds:object, modules:string[]}} options
     *   `inputIds` maps DOM id -> field key. The same field may appear in several
     *   toolbars (the three market tabs share the horizon), so hydration writes
     *   every id bound to a field and a change in any of them updates them all.
     */
    function create(options) {
        const { name, storageKey, defaults, inputIds, modules } = options;
        let state = _read(storageKey, defaults);

        function hydrate() {
            Object.keys(inputIds).forEach((id) => {
                const el = root.document.getElementById(id);
                if (el && el.value !== state[inputIds[id]]) el.value = state[inputIds[id]];
            });
            _mirrorIntoForm();
        }

        // WHY the mirror: `POST /` still validates the horizon and uses it to size
        // the readiness prefetch. The *visible* control lives in the module
        // toolbars (this store is the single source of truth); these hidden inputs
        // only carry the value on submit.
        function _mirrorIntoForm() {
            if (!Array.isArray(options.formMirror) || !options.formMirror.length) return;
            options.formMirror.forEach(([fieldKey, inputId]) => {
                const el = root.document.getElementById(inputId);
                if (el) el.value = state[fieldKey];
            });
        }

        function set(key, value) {
            if (state[key] === value) return;
            state[key] = value;
            hydrate();
            _write(storageKey, state);
            _mirrorIntoForm();
            bus.emit('module:params-changed', { group: name, modules: modules.slice() });
        }

        function commitFromDom(changedId) {
            // WHY only the event target's field: a field may be bound to several
            // toolbar inputs (the horizon appears in three of them), and the ones
            // the user did *not* touch still hold the previous value. Reading the
            // whole map here would let a stale input clobber the fresh change —
            // `hydrate()` below is what propagates the new value to the others.
            const field = changedId ? inputIds[changedId] : null;
            if (field) {
                const el = root.document.getElementById(changedId);
                if (el) state[field] = el.value;
            }
            hydrate();
            _write(storageKey, state);
            _mirrorIntoForm();
            bus.emit('module:params-changed', { group: name, modules: modules.slice() });
        }

        function get() {
            return Object.assign({}, state);
        }

        /** Query-string fragment for this group's params (used by the URL builder). */
        function query(keys) {
            const names = keys || Object.keys(defaults);
            return names
                .filter((key) => state[key] !== undefined && state[key] !== '')
                .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(state[key])}`)
                .join('&');
        }

        function bind() {
            Object.keys(inputIds).forEach((id) => {
                const el = root.document.getElementById(id);
                if (!el || el.dataset.paramsBound === '1') return;
                el.dataset.paramsBound = '1';
                // A <select> fires `input` *and* `change` for one edit; listening
                // to both would emit the same change twice (and race the reruns).
                if (el.tagName === 'SELECT') {
                    el.addEventListener('change', () => commitFromDom(id));
                } else {
                    el.addEventListener('input', () => commitFromDom(id));
                    el.addEventListener('change', () => commitFromDom(id));
                }
            });
        }

        const store = {
            name,
            STORAGE_KEY: storageKey,
            DEFAULTS: Object.assign({}, defaults),
            MODULES: modules.slice(),
            get,
            set,
            query,
            hydrate,
            bind,
            /** hydrate + bind. RETURNS the store: the callers chain `.init()`
             *  onto the factory call, so returning nothing would clobber the
             *  global the factory just published. */
            init() {
                hydrate();
                bind();
                return store;
            },
        };

        if (root.appState) root.appState[options.namespace || name] = store;
        return store;
    }

    root.createParamsStore = create;
})(window);

/* state/marketParamsState.js — the three market tabs' shared parameters (B7).
 *
 * Group: horizon (`from`/`to`) + `frequency`. One localStorage key, because the
 * three streaming market tabs (Market Review / Statistical / Assessment) share
 * exactly this set — changing a value re-runs all three, which is the plan's
 * "marketParams" group (`docs/plans/business_line_reorg.md` §5.1).
 *
 * The same field appears in three toolbars, so it is bound to three input ids;
 * hydration keeps them in sync and any change updates the whole group.
 */
(function (root) {
    'use strict';

    const DEFAULTS = {
        // DOMAIN: default horizon is the same 5 years the old Parameter tab
        // pre-filled, expressed as `<input type="month">` values.
        from: (function () {
            const now = new Date();
            return `${now.getFullYear() - 5}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        })(),
        to: '',
        frequency: 'ME',
    };

    root.appState.marketParams = root.createParamsStore({
        name: 'marketParams',
        namespace: 'marketParams',
        storageKey: 'marketParams',
        defaults: DEFAULTS,
        // id -> field. Three toolbars share the horizon; two share frequency.
        inputIds: {
            'mr-from': 'from',
            'mr-to': 'to',
            'stat-from': 'from',
            'stat-to': 'to',
            'stat-frequency': 'frequency',
            'assess-from': 'from',
            'assess-to': 'to',
            'assess-frequency': 'frequency',
        },
        // `POST /` still needs the horizon (validation + readiness prefetch depth).
        formMirror: [
            ['from', 'start_time'],
            ['to', 'end_time'],
        ],
        modules: ['market_review', 'statistical', 'assessment'],
    }).init();
})(window);

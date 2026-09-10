/* state/optionFilterState.js — live option-chain filters (batch B7).
 *
 * Group: `max_dte`, `moneyness_low`, `moneyness_high`, `max_contracts` and the
 * auto-refresh `refresh_interval`. Consumers: the Option Chain tab, the Payoff
 * Ratio tab (same filters) and `static/option-chain.js` — all client-fired, so
 * `modules` is empty (there is no `/render/*` call to re-issue) and
 * `option-chain.js` listens for `module:params-changed` with this group instead.
 */
(function (root) {
    'use strict';

    root.appState.optionFilter = root.createParamsStore({
        name: 'optionFilter',
        namespace: 'optionFilter',
        storageKey: 'optionFilter',
        defaults: {
            max_dte: '45',
            moneyness_low: '0.70',
            moneyness_high: '1.30',
            max_contracts: '1000',
            refresh_interval: '60',
        },
        inputIds: {
            'oc-max-dte': 'max_dte',
            'oc-moneyness-low': 'moneyness_low',
            'oc-moneyness-high': 'moneyness_high',
            'oc-max-contracts': 'max_contracts',
            'oc-refresh-interval': 'refresh_interval',
        },
        modules: [],
    }).init();
})(window);

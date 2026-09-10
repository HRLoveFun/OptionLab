/* state/assessmentParamsState.js — Assessment & Projections knobs (batch B7).
 *
 * Group: `side_bias`, `risk_threshold`, `rolling_window`, `account_size`,
 * `max_risk_pct` — Assessment is their only consumer, so they live with the
 * module (previously the "global" Config tab, bridged through hidden inputs).
 */
(function (root) {
    'use strict';

    root.appState.assessmentParams = root.createParamsStore({
        name: 'assessmentParams',
        namespace: 'assessmentParams',
        storageKey: 'assessmentParams',
        defaults: {
            side_bias: 'Natural',
            risk_threshold: '90',
            rolling_window: '120',
            // Optional sizing inputs: blank means "not set" (the server sends null).
            account_size: '',
            max_risk_pct: '',
        },
        inputIds: {
            'assess-side-bias': 'side_bias',
            'assess-risk-threshold': 'risk_threshold',
            'assess-rolling-window': 'rolling_window',
            'assess-account-size': 'account_size',
            'assess-max-risk-pct': 'max_risk_pct',
        },
        modules: ['assessment'],
    }).init();
})(window);

/* moduleParams.js — re-issue a module's /render call when its params change (B7).
 *
 * WHY this exists as well as `hx-include`:
 *   - `hx-include="#<module>-toolbar"` covers the *first* fan-out: the stores
 *     hydrate their inputs at parse time, so the initial `hx-trigger="load"`
 *     request already carries the stored parameters.
 *   - afterwards the placeholder has been replaced by the rendered fragment,
 *     which carries no `hx-get`; so a re-run has to be issued explicitly. This
 *     module builds the URL from the job id + ticker + the owning stores and
 *     calls `htmx.ajax` for exactly the affected modules — nothing else re-runs.
 *
 * The module → (tab element, toolbar, param groups) map is the single place that
 * knows which parameters a module accepts; it mirrors
 * `FormService.MODULE_PARAM_KEYS` on the backend.
 */
(function (root) {
    'use strict';

    // kind -> { elementId, query }
    // `query` returns the extra query params that module accepts.
    const MODULES = {
        market_review: {
            elementId: 'tab-market-review-content',
            query: () => root.appState.marketParams.query(['from', 'to']),
        },
        statistical: {
            elementId: 'tab-statistical-analysis-content',
            query: () => root.appState.marketParams.query(['from', 'to', 'frequency']),
        },
        assessment: {
            elementId: 'tab-market-assessment-content',
            query: () =>
                [
                    root.appState.marketParams.query(['from', 'to', 'frequency']),
                    root.appState.assessmentParams.query([
                        'side_bias',
                        'risk_threshold',
                        'rolling_window',
                        'account_size',
                        'max_risk_pct',
                    ]),
                ]
                    .filter(Boolean)
                    .join('&'),
        },
    };

    function _jobId() {
        const bar = document.querySelector('.parameters-bar');
        return (bar && bar.dataset.jobId) || '';
    }

    function _ticker() {
        const input = root.document.getElementById('ticker');
        return input ? input.value.trim().toUpperCase() : '';
    }

    function url(kind) {
        const module = MODULES[kind];
        const job = encodeURIComponent(_jobId());
        const ticker = encodeURIComponent(_ticker());
        const extra = module.query();
        return `/render/${kind}?job=${job}&ticker=${ticker}${extra ? '&' + extra : ''}`;
    }

    function rerun(kind) {
        const module = MODULES[kind];
        const old = root.document.getElementById(module.elementId);
        if (!old || !old.parentNode || !root.htmx) return;
        const nextUrl = url(kind);
        // WHY skip an identical in-flight skeleton: a single toolbar edit fires
        // `input` *and* `change`, so two reruns race — the second would replace
        // the element the first request is still swapping into, and htmx throws
        // `htmx:swapError` (null parent). One skeleton per URL is enough.
        if (old.classList.contains('loading-skeleton') && old.getAttribute('hx-get') === nextUrl) {
            return;
        }
        // WHY a fresh skeleton + htmx.process (and not htmx.ajax): this is the
        // idiom the streaming re-fire already uses in
        // static/market_review_chart.js — it also puts the loading state back,
        // instead of leaving a stale fragment on screen while refetching.
        const skeleton = root.document.createElement('div');
        skeleton.id = module.elementId;
        skeleton.className = 'loading-skeleton';
        skeleton.setAttribute('hx-get', nextUrl);
        skeleton.setAttribute('hx-trigger', 'load');
        skeleton.setAttribute('hx-swap', 'outerHTML');
        skeleton.innerHTML = '<div class="empty-state"><p>Updating…</p></div>';
        old.parentNode.replaceChild(skeleton, old);
        root.htmx.process(skeleton);
    }

    function init() {
        const bus = root.bus || root.eventBus;
        if (!bus) return;
        bus.on('module:params-changed', (payload) => {
            const modules = (payload && payload.modules) || [];
            modules.forEach((kind) => {
                if (MODULES[kind]) rerun(kind);
            });
        });
    }

    root.moduleParams = { MODULES, url, rerun, init };
    init();
})(window);

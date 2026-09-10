/* parametersBar.js — persistent Parameters bar: collapse state + summary.
 *
 * Contract (docs/frontend_architecture.md, batch B6):
 *   - the bar owns the shared `ticker` input and the Run button; it is NOT a tab,
 *     so it stays visible while the user switches tabs;
 *   - collapsing is a per-viewer convenience persisted in localStorage, and the
 *     collapsed bar shows the current ticker as `▸ ^SPX`;
 *   - CONSTRAINT: every localStorage access is guarded — private mode / disabled
 *     storage must degrade to "not persisted", never throw (no build step, no
 *     polyfills; see ADR 0006).
 */
(function (root) {
    'use strict';

    var STORAGE_KEY = 'parametersBarCollapsed';
    var BAR_SELECTOR = '.parameters-bar';

    function _read() {
        try {
            return root.localStorage.getItem(STORAGE_KEY);
        } catch (_) {
            return null;
        }
    }

    function _write(value) {
        try {
            root.localStorage.setItem(STORAGE_KEY, value);
        } catch (_) {
            /* not fatal: the bar just will not remember its state */
        }
    }

    function setCollapsed(bar, collapsed) {
        bar.dataset.collapsed = collapsed ? 'true' : 'false';
        var toggle = document.getElementById('parameters-bar-toggle');
        if (!toggle) return;
        toggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        var icon = toggle.querySelector('i');
        if (icon) icon.className = collapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-down';
    }

    function updateSummary(bar) {
        var summary = document.getElementById('parameters-bar-summary');
        var input = document.getElementById('ticker');
        if (!summary || !input) return;
        var value = (input.value || '').trim();
        summary.textContent = value ? '▸ ' + value : '';
    }

    function init() {
        var bar = document.querySelector(BAR_SELECTOR);
        if (!bar) return;

        setCollapsed(bar, _read() === 'true');

        var toggle = document.getElementById('parameters-bar-toggle');
        if (toggle) {
            toggle.addEventListener('click', function () {
                var next = bar.dataset.collapsed !== 'true';
                setCollapsed(bar, next);
                _write(next ? 'true' : 'false');
            });
        }

        var input = document.getElementById('ticker');
        if (input) input.addEventListener('input', function () { updateSummary(bar); });
        updateSummary(bar);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Exposed for the jsdom unit tests (no bundler; plain global, like theme.js).
    root.parametersBar = {
        init: init,
        setCollapsed: setCollapsed,
        updateSummary: updateSummary,
        STORAGE_KEY: STORAGE_KEY,
    };
})(typeof window !== 'undefined' ? window : this);

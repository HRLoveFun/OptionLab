// sidebar.js — collapsible navigation panel.
//
// Two states, driven by a single data attribute on <aside class="sidebar">:
//   data-collapsed="false" → full nav + rail (rail is a subtle accent line)
//   data-collapsed="true"  → nav hidden, only the rail remains: one vertical
//                            line in the theme accent (gold under Onyx)
// The rail button is the toggle in both states, so a collapsed nav needs no
// separate "expand" affordance. See .sidebar-rail in static/styles.css.

(function () {
    const STORAGE_KEY = 'sidebarCollapsed';

    function readStored() {
        try {
            return localStorage.getItem(STORAGE_KEY) === '1';
        } catch (e) {
            return false;
        }
    }

    function writeStored(collapsed) {
        try {
            localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
        } catch (e) {
            /* storage unavailable (private mode) — state just won't persist */
        }
    }

    function init() {
        const sidebar = document.getElementById('sidebar');
        const rail = document.getElementById('sidebar-rail');
        const label = document.getElementById('sidebar-rail-label');
        if (!sidebar || !rail) return;

        let collapsed = readStored();

        function apply() {
            sidebar.dataset.collapsed = collapsed ? 'true' : 'false';
            rail.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
            const text = collapsed ? 'Expand navigation' : 'Collapse navigation';
            rail.title = text;
            if (label) label.textContent = text;
        }

        rail.addEventListener('click', function () {
            collapsed = !collapsed;
            apply();
            writeStored(collapsed);
        });

        apply();
    }

    // The tag sits directly after the <aside>, so the document is already
    // parsed far enough for getElementById; running synchronously here is what
    // keeps a persisted collapsed nav from flashing open on load.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

// sidebar.js — peek navigation.
//
// At rest the sidebar is only .sidebar-rail: one vertical line in the theme
// accent (gold under Onyx). Hovering or focusing the sidebar reveals
// .sidebar-body, which is absolutely positioned so it overlays the main panel
// instead of reflowing it; leaving hides it again.
//
// CSS owns visibility (:hover / :focus-within) so the peek still works with
// JS disabled. This module only mirrors the state onto ARIA, plus one thing
// CSS cannot do: a tap-to-pin fallback for devices with no hover.

(function () {
    function init() {
        const sidebar = document.getElementById('sidebar');
        const rail = document.getElementById('sidebar-rail');
        const label = document.getElementById('sidebar-rail-label');
        if (!sidebar || !rail) return;

        // Pinned state is a touch-only affordance (see the (hover: none) block
        // in styles.css), so it is ignored wherever hover is available.
        const canHover = window.matchMedia('(hover: hover)').matches;

        function isOpen() {
            // Mirrors the CSS triggers exactly: hover, keyboard focus
            // (:focus-visible — a mouse click on a tab must not count), or the
            // pinned flag on devices that have no hover at all.
            return sidebar.matches(':hover')
                || sidebar.querySelector(':focus-visible') !== null
                || (!canHover && sidebar.dataset.pinned === 'true');
        }

        function sync() {
            const open = isOpen();
            rail.setAttribute('aria-expanded', open ? 'true' : 'false');
            const text = open ? 'Hide navigation' : 'Show navigation';
            rail.title = text;
            if (label) label.textContent = text;
        }

        // focusout fires before focus has settled on the next element, so the
        // :focus-within check has to run after the move completes.
        function syncSoon() {
            setTimeout(sync, 0);
        }

        sidebar.addEventListener('mouseenter', sync);
        sidebar.addEventListener('mouseleave', sync);
        sidebar.addEventListener('focusin', sync);
        sidebar.addEventListener('focusout', syncSoon);

        rail.addEventListener('click', function () {
            if (canHover) return;
            sidebar.dataset.pinned = sidebar.dataset.pinned === 'true' ? 'false' : 'true';
            sync();
        });

        sync();
    }

    // The tag sits directly after the <aside>, so the document is already
    // parsed far enough for getElementById.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

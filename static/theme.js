/* theme.js — Light/Dark theme toggle (header button).
 *
 * Theme model (see the Onyx override layer at the bottom of styles.css):
 *   - Dark ("Onyx") is the DEFAULT and applies whenever <html> does NOT
 *     carry data-theme="light".
 *   - Light Mode is opt-in: <html data-theme="light"> resolves the plain
 *     token base at the top of styles.css.
 * The pre-init inline script in index.html applies the persisted choice
 * before the stylesheet loads to avoid a flash of the wrong theme; this
 * module owns the runtime toggle and persistence.
 *
 * Loaded via <script> tag at the bottom of index.html (after the DOM).
 * Exposes window.themeManager for tests and programmatic control.
 */
(function (root) {
    'use strict';

    var STORAGE_KEY = 'theme';
    var LIGHT = 'light';
    var DARK = 'dark';

    // Sticky-header chrome color per theme, mirrored to
    // <meta name="theme-color"> so the mobile address bar follows.
    var THEME_COLOR = { light: '#0f172a', dark: '#050505' };

    function getTheme() {
        try {
            return root.document.documentElement.getAttribute('data-theme') === LIGHT ? LIGHT : DARK;
        } catch (e) {
            return DARK;
        }
    }

    /* Apply a theme: set <html data-theme>, persist the choice, and sync
       the button label + browser chrome color. Never throws. */
    function apply(theme) {
        var value = theme === LIGHT ? LIGHT : DARK;
        try {
            root.document.documentElement.setAttribute('data-theme', value);
            root.localStorage.setItem(STORAGE_KEY, value);
        } catch (e) { /* storage unavailable — theme still applies for this page */ }

        try {
            var meta = root.document.querySelector('meta[name="theme-color"]');
            if (meta) meta.setAttribute('content', THEME_COLOR[value]);
            var btn = root.document.getElementById('theme-toggle');
            if (btn) {
                var label = value === LIGHT ? 'Switch to dark mode' : 'Switch to light mode';
                btn.setAttribute('aria-label', label);
                btn.setAttribute('title', label);
            }
        } catch (e) { /* DOM not ready — init() re-syncs after DOMContentLoaded */ }
        return value;
    }

    function setTheme(theme) {
        return apply(theme);
    }

    function toggleTheme() {
        return apply(getTheme() === LIGHT ? DARK : LIGHT);
    }

    function init() {
        var btn = root.document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
        // Re-sync button label + meta color with whatever the pre-init
        // script already applied (they are skipped if the DOM wasn't ready).
        apply(getTheme());
    }

    root.themeManager = { get: getTheme, set: setTheme, toggle: toggleTheme };

    if (root.document.readyState === 'loading') {
        root.document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})(window);

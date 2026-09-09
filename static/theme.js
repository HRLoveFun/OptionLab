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
 * Loaded via <script> tag near the bottom of index.html but AFTER the
 * header markup, so #theme-toggle already exists and init() wires it
 * synchronously (no DOMContentLoaded wait).
 * Exposes window.themeManager for tests and programmatic control, and
 * emits 'theme:changed' on window.bus so token-caching consumers
 * (e.g. static/regime.js) can re-read theme-dependent CSS variables.
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

    /* Reflect a theme in the page: set <html data-theme>, sync the button
       label, and sync the browser chrome color. Does NOT persist and does
       NOT emit — that is reserved for an explicit choice (see apply()).
       Never throws. */
    function reflect(theme) {
        var value = theme === LIGHT ? LIGHT : DARK;
        try {
            root.document.documentElement.setAttribute('data-theme', value);
        } catch (e) { /* pre-init script already set it — nothing else to do */ }

        try {
            var meta = root.document.querySelector('meta[name="theme-color"]');
            if (meta) meta.setAttribute('content', THEME_COLOR[value]);
            var btn = root.document.getElementById('theme-toggle');
            if (btn) {
                var label = value === LIGHT ? 'Switch to dark mode' : 'Switch to light mode';
                btn.setAttribute('aria-label', label);
                btn.setAttribute('title', label);
            }
        } catch (e) { /* DOM not ready — init() re-syncs */ }
        return value;
    }

    /* Apply a theme AS AN EXPLICIT CHOICE: reflect it, persist it, and
       notify consumers over the event bus. Never throws. */
    function apply(theme) {
        var value = reflect(theme);
        try {
            root.localStorage.setItem(STORAGE_KEY, value);
        } catch (e) { /* storage unavailable — theme still applies for this page */ }
        try {
            if (root.bus && root.bus.emit) root.bus.emit('theme:changed', value);
        } catch (e) { /* event bus not loaded (e.g. isolated unit test) */ }
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
        // Sync the button label + meta color with whatever the pre-init
        // script already applied. This is the default, not a user choice,
        // so it must not persist or emit.
        reflect(getTheme());
    }

    root.themeManager = { get: getTheme, set: setTheme, toggle: toggleTheme };

    // #theme-toggle and <meta name="theme-color"> both sit above this
    // script in index.html, so the DOM we touch is already parsed — wire
    // the toggle now instead of deferring to DOMContentLoaded (8 feature
    // scripts still follow). Mirrors the inline load of static/sidebar.js.
    init();
})(window);

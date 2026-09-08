// Unit tests for static/theme.js — Light/Dark theme toggle.
//
// Theme contract (see the Onyx layer at the bottom of styles.css and the
// pre-init script in templates/index.html):
//   - Dark is the default: <html> without data-theme="light".
//   - Light Mode is opt-in: <html data-theme="light">, persisted under
//     localStorage key "theme".
import { describe, it, expect, beforeEach } from 'vitest';
import { loadScript } from './_loadScript.js';

// theme.js defers init() to DOMContentLoaded when the document is still
// parsing; jsdom under vitest may report readyState 'loading'.
function ensureInit() {
    if (document.readyState === 'loading') {
        document.dispatchEvent(new Event('DOMContentLoaded'));
    }
}

describe('theme.js — Light/Dark toggle', () => {
    beforeEach(() => {
        delete window.themeManager;
        document.body.innerHTML = '';
        document.documentElement.removeAttribute('data-theme');
    });

    it('exposes themeManager and defaults to dark', () => {
        loadScript('static/theme.js');
        ensureInit();
        expect(window.themeManager).toBeDefined();
        expect(window.themeManager.get()).toBe('dark');
    });

    it('set("light") applies the attribute and persists the choice', () => {
        loadScript('static/theme.js');
        ensureInit();
        expect(window.themeManager.set('light')).toBe('light');
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        expect(window.localStorage.getItem('theme')).toBe('light');
    });

    it('unknown theme values fall back to dark', () => {
        loadScript('static/theme.js');
        ensureInit();
        expect(window.themeManager.set('sepia')).toBe('dark');
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        expect(window.localStorage.getItem('theme')).toBe('dark');
    });

    it('toggle flips light → dark → light', () => {
        loadScript('static/theme.js');
        ensureInit();
        window.themeManager.set('light');
        expect(window.themeManager.toggle()).toBe('dark');
        expect(window.localStorage.getItem('theme')).toBe('dark');
        expect(window.themeManager.toggle()).toBe('light');
        expect(window.localStorage.getItem('theme')).toBe('light');
    });

    it('header button click toggles the theme and updates its aria-label', () => {
        document.body.innerHTML = '<button type="button" id="theme-toggle" class="theme-toggle"></button>';
        loadScript('static/theme.js');
        ensureInit();

        const btn = document.getElementById('theme-toggle');
        btn.click();
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        expect(btn.getAttribute('aria-label')).toBe('Switch to dark mode');

        btn.click();
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        expect(btn.getAttribute('aria-label')).toBe('Switch to light mode');
    });

    it('survives a "reload": pre-set light attribute is kept, button label synced', () => {
        // Simulate the pre-init script in index.html + a stored light choice.
        document.documentElement.setAttribute('data-theme', 'light');
        window.localStorage.setItem('theme', 'light');
        document.body.innerHTML = '<button type="button" id="theme-toggle" class="theme-toggle"></button>';

        loadScript('static/theme.js');
        ensureInit();

        expect(window.themeManager.get()).toBe('light');
        expect(document.getElementById('theme-toggle').getAttribute('aria-label')).toBe('Switch to dark mode');
        expect(window.localStorage.getItem('theme')).toBe('light');
    });

    it('works when localStorage is unavailable (theme applies for the page only)', () => {
        const original = window.localStorage;
        Object.defineProperty(window, 'localStorage', {
            configurable: true,
            get() {
                throw new Error('storage blocked');
            },
        });
        try {
            loadScript('static/theme.js');
            ensureInit();
            expect(window.themeManager.toggle()).toBe('light');
            expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        } finally {
            Object.defineProperty(window, 'localStorage', {
                configurable: true,
                value: original,
            });
        }
    });
});

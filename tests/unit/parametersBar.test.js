/**
 * Tests for static/parametersBar.js — the persistent Parameters bar (batch B6).
 *
 * Contract under test:
 *   - expands by default, collapses on the toggle, and remembers the choice;
 *   - the collapsed bar shows the current ticker as `▸ AAPL`;
 *   - a browser with storage denied must degrade to "not persisted", never throw.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript } from './_loadScript.js';

const BAR_HTML = `
<form id="analysis-form" class="parameters-bar" data-collapsed="false">
  <button type="button" id="parameters-bar-toggle" aria-expanded="true">
    <i class="fas fa-chevron-down"></i>
  </button>
  <input id="ticker" value="">
  <span id="parameters-bar-summary"></span>
  <div class="parameters-bar-body" id="parameters-bar-body"></div>
</form>`;

function bar() {
    return document.querySelector('.parameters-bar');
}

/** Mount the markup, then load the script — its auto-init runs on 'complete'. */
function mount() {
    document.body.innerHTML = BAR_HTML;
    delete window.parametersBar;
    loadScript('static/parametersBar.js');
}

beforeEach(() => {
    window.localStorage.clear();
});

describe('parametersBar — collapse persistence', () => {
    it('expands by default when nothing is stored', () => {
        mount();
        expect(bar().dataset.collapsed).toBe('false');
        expect(document.getElementById('parameters-bar-toggle').getAttribute('aria-expanded')).toBe('true');
    });

    it('collapses on toggle and persists the choice', () => {
        mount();
        document.getElementById('parameters-bar-toggle').click();

        expect(bar().dataset.collapsed).toBe('true');
        expect(window.localStorage.getItem('parametersBarCollapsed')).toBe('true');
        expect(document.getElementById('parameters-bar-toggle').getAttribute('aria-expanded')).toBe('false');
        expect(document.querySelector('#parameters-bar-toggle i').className).toBe('fas fa-chevron-right');
    });

    it('restores the collapsed state on the next page load', () => {
        window.localStorage.setItem('parametersBarCollapsed', 'true');
        mount();
        expect(bar().dataset.collapsed).toBe('true');
    });

    it('expands again when toggled twice', () => {
        mount();
        const toggle = document.getElementById('parameters-bar-toggle');
        toggle.click();
        toggle.click();

        expect(bar().dataset.collapsed).toBe('false');
        expect(window.localStorage.getItem('parametersBarCollapsed')).toBe('false');
    });
});

describe('parametersBar — collapsed summary', () => {
    it('mirrors the ticker input into the one-line summary', () => {
        mount();
        const input = document.getElementById('ticker');
        input.value = '^SPX';
        input.dispatchEvent(new Event('input'));

        expect(document.getElementById('parameters-bar-summary').textContent).toBe('▸ ^SPX');
    });

    it('is empty when the ticker is blank', () => {
        mount();
        const input = document.getElementById('ticker');
        input.value = '   ';
        input.dispatchEvent(new Event('input'));

        expect(document.getElementById('parameters-bar-summary').textContent).toBe('');
    });
});

describe('parametersBar — degraded storage', () => {
    it('does not throw when localStorage is denied', () => {
        const getItem = vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
            throw new Error('storage denied');
        });
        const setItem = vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
            throw new Error('storage denied');
        });

        expect(() => mount()).not.toThrow();
        // Toggling must still work — it only loses persistence.
        expect(() => document.getElementById('parameters-bar-toggle').click()).not.toThrow();
        expect(bar().dataset.collapsed).toBe('true');

        getItem.mockRestore();
        setItem.mockRestore();
    });

    it('is inert when the bar is absent from the page', () => {
        document.body.innerHTML = '';
        expect(() => mount()).not.toThrow();
    });
});

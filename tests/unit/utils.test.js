/**
 * Tests for static/utils.js — escapeHtml, parseTickers, getValidTickers.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { loadScript } from './_loadScript.js';

beforeEach(() => {
    // utils.js touches window.appState shims; ensure state is loaded too.
    loadScript('static/eventBus.js');
    loadScript('static/state/store.js');
    loadScript('static/state/chainCacheState.js');
    loadScript('static/utils.js');
});

describe('escapeHtml', () => {
    it('escapes <, >, & and quotes', () => {
        expect(window.escapeHtml('<script>alert("x")</script>'))
            .toBe('&lt;script&gt;alert("x")&lt;/script&gt;');
    });

    it('returns empty string for null/undefined', () => {
        expect(window.escapeHtml(null)).toBe('');
        expect(window.escapeHtml(undefined)).toBe('');
    });

    it('coerces non-string input', () => {
        expect(window.escapeHtml(42)).toBe('42');
        expect(window.escapeHtml(0)).toBe('0');
        expect(window.escapeHtml(false)).toBe('false');
    });

    it('passes through plain text unchanged', () => {
        expect(window.escapeHtml('AAPL')).toBe('AAPL');
    });
});

describe('parseTickers', () => {
    it('splits on comma and newline', () => {
        expect(window.parseTickers('aapl, msft\nspy')).toEqual(['AAPL', 'MSFT', 'SPY']);
    });

    it('uppercases and trims', () => {
        expect(window.parseTickers('  aapl  ,msft ')).toEqual(['AAPL', 'MSFT']);
    });

    it('removes duplicates preserving order', () => {
        expect(window.parseTickers('aapl,aapl,msft,AAPL')).toEqual(['AAPL', 'MSFT']);
    });

    it('returns empty array for empty/whitespace input', () => {
        expect(window.parseTickers('')).toEqual([]);
        expect(window.parseTickers('   ')).toEqual([]);
        expect(window.parseTickers(',,\n,')).toEqual([]);
    });

    it('handles single ticker without separators', () => {
        expect(window.parseTickers('aapl')).toEqual(['AAPL']);
    });
});

describe('getValidTickers', () => {
    it('returns [] when ticker input is missing from DOM', () => {
        expect(window.getValidTickers()).toEqual([]);
    });

    it('parses the value of #ticker', () => {
        const input = document.createElement('input');
        input.id = 'ticker';
        input.value = 'aapl, msft';
        document.body.appendChild(input);
        expect(window.getValidTickers()).toEqual(['AAPL', 'MSFT']);
    });
});

describe('chainCache shims', () => {
    it('return null when state not initialized for that ticker', () => {
        expect(window._chainCacheGet('AAPL')).toBeNull();
    });

    it('roundtrip through the appState.chainCache backend', () => {
        window._chainCacheSet('AAPL', { spot: 100, expiries: ['2026-05-15'] });
        const got = window._chainCacheGet('AAPL');
        expect(got).not.toBeNull();
        expect(got.spot).toBe(100);
    });
});

describe('initializeOptionsTable', () => {
    it('is a no-op when #positions-tbody is absent', () => {
        expect(() => window.initializeOptionsTable()).not.toThrow();
    });
});

/**
 * Coverage instrumentation pass.
 *
 * The other unit tests use `eval`-based loading (so they can run an IIFE
 * multiple times across `beforeEach` calls). V8 coverage cannot attribute
 * those executions back to the source files. This file imports every
 * covered module statically — Vite/Vitest transform and instrument them,
 * and the IIFE side effects record one full execution per file.
 *
 * Behavior is exercised by the dedicated test files; here we only confirm
 * each module published its expected `window` surface (the global setup
 * `beforeEach` wipes those globals, so we re-publish from cached refs).
 */
import { beforeAll, beforeEach, describe, expect, it } from 'vitest';

import '../../static/eventBus.js';
import '../../static/api.js';
import '../../static/state/store.js';
import '../../static/state/abortRegistry.js';
import '../../static/state/chainCacheState.js';
import '../../static/state/optionChainState.js';
import '../../static/state/payoffRatioState.js';
import '../../static/state/tabFlagsState.js';
import '../../static/state/panelState.js';
import '../../static/utils.js';
import '../../static/cache.js';
import '../../static/simulation.js';
import '../../static/theme.js';
import '../../static/parametersBar.js';
import '../../static/state/paramsStore.js';
import '../../static/state/marketParamsState.js';
import '../../static/state/assessmentParamsState.js';
import '../../static/state/optionFilterState.js';
import '../../static/moduleParams.js';

// Capture the post-import surface BEFORE the setup `beforeEach` runs and
// wipes globals. We re-attach them in a local `beforeEach` so each `it`
// sees a fresh snapshot.
const _snapshot = {
    bus: window.bus,
    eventBus: window.eventBus,
    api: window.api,
    ApiError: window.ApiError,
    appState: window.appState,
    panelState: window.panelState,
    escapeHtml: window.escapeHtml,
    parseTickers: window.parseTickers,
    getValidTickers: window.getValidTickers,
    initializeOptionsTable: window.initializeOptionsTable,
    toggleOptionsSection: window.toggleOptionsSection,
    toggleSizingSection: window.toggleSizingSection,
    loadSimulationTab: window.loadSimulationTab,
    runSimulation: window.runSimulation,
    themeManager: window.themeManager,
    parametersBar: window.parametersBar,
    marketParams: window.appState.marketParams,
    assessmentParams: window.appState.assessmentParams,
    optionFilter: window.appState.optionFilter,
    moduleParams: window.moduleParams,
};

beforeEach(() => {
    Object.assign(window, _snapshot);
});

describe('coverage smoke — every module publishes its surface', () => {
    beforeAll(() => {
        // Sanity: imports actually executed.
        expect(_snapshot.bus).toBeDefined();
    });

    it('eventBus is on window.bus / window.eventBus', () => {
        expect(window.bus).toBeDefined();
        expect(window.eventBus).toBe(window.bus);
    });

    it('api is on window.api', () => {
        expect(window.api).toBeDefined();
        expect(typeof window.api.get).toBe('function');
    });

    it('appState namespace is registered', () => {
        expect(window.appState).toBeDefined();
        expect(window.appState.aborts).toBeDefined();
        expect(window.appState.chainCache).toBeDefined();
        expect(window.appState.optionChain).toBeDefined();
        expect(window.appState.payoffRatio).toBeDefined();
        expect(window.appState.tabFlags).toBeDefined();
        expect(window.appState.panels).toBeDefined();
    });

    it('utils functions are global', () => {
        expect(typeof window.escapeHtml).toBe('function');
        expect(typeof window.parseTickers).toBe('function');
    });

    it('parameters bar published its window surface', () => {
        expect(window.parametersBar).toBeDefined();
        expect(typeof window.parametersBar.init).toBe('function');
        expect(window.parametersBar.STORAGE_KEY).toBe('parametersBarCollapsed');
    });

    it('module parameter groups published their window surface', () => {
        for (const key of ['marketParams', 'assessmentParams', 'optionFilter']) {
            expect(typeof window.appState[key].get).toBe('function');
            expect(typeof window.appState[key].query).toBe('function');
        }
        expect(typeof window.moduleParams.rerun).toBe('function');
    });

    it('simulation tab published its window surface', () => {
        expect(typeof window.loadSimulationTab).toBe('function');
        expect(typeof window.runSimulation).toBe('function');
    });

    it('theme manager published its window surface', () => {
        expect(window.themeManager).toBeDefined();
        expect(typeof window.themeManager.get).toBe('function');
        expect(typeof window.themeManager.set).toBe('function');
        expect(typeof window.themeManager.toggle).toBe('function');
    });
});

/* ------------------------------------------------------------
   Exercise every public branch of every module against the
   instrumented (statically-imported) sources so the V8 coverage
   report reflects the real test coverage. The dedicated test
   files duplicate these scenarios but run against `eval`'d
   sources that V8 can't attribute back.
   ------------------------------------------------------------ */
describe('coverage drill — exercise instrumented sources', () => {
    it('eventBus on/once/off/emit/state', () => {
        const fn = (() => { });
        const off = window.bus.on('e', fn);
        window.bus.emit('e', 1);
        off();
        window.bus.once('o', () => { });
        window.bus.emit('o');
        window.bus.emit('o');
        window.bus.off('missing', fn);
        const consoleSpy = (msg) => msg;
        window.bus.on('boom', () => { throw new Error('x'); });
        const origErr = console.error;
        console.error = () => { };
        window.bus.emit('boom');
        console.error = origErr;
        window.bus.state.set('k', 1);
        window.bus.state.get('k');
        window.bus.state.has('k');
        window.bus.state.get('missing', 0);
        window.bus.state.delete('k');
        window.bus.state.delete('k');
        window.bus.state.clear();
    });

    it('api request paths', async () => {
        const ok = new Response(JSON.stringify({ ok: true }), {
            status: 200, headers: { 'content-type': 'application/json' },
        });
        const fail = new Response(JSON.stringify({ error: 'bad' }), {
            status: 400, headers: { 'content-type': 'application/json' },
        });
        const text = new Response('hello', {
            status: 200, headers: { 'content-type': 'text/plain' },
        });
        const calls = [ok.clone(), fail.clone(), text.clone(), ok.clone(), ok.clone()];
        let i = 0;
        window.fetch = async () => calls[i++] || ok.clone();

        await window.api.get('/x');
        await window.api.get('/x', { parse: 'json' }).catch(() => { });
        await window.api.get('/x', { parse: 'text' }).catch(() => { });
        await window.api.post('/x', { body: { a: 1 }, key: 'k' });
        window.api.abort('k');
        await window.api.put('/x');

        // network error path
        window.fetch = async () => { throw new TypeError('netz'); };
        await window.api.get('/x').catch(() => { });

        // abort path
        window.fetch = async () => { const e = new Error('a'); e.name = 'AbortError'; throw e; };
        await window.api.get('/x', { key: 'a' }).catch(() => { });
    });

    it('utils functions exercised', () => {
        expect(window.escapeHtml('<b>')).toBe('&lt;b&gt;');
        expect(window.escapeHtml(null)).toBe('');
        expect(window.escapeHtml(undefined)).toBe('');
        expect(window.escapeHtml(0)).toBe('0');
        expect(window.parseTickers('a,b,a')).toEqual(['A', 'B']);
        expect(window.parseTickers('')).toEqual([]);
        expect(window.getValidTickers()).toEqual([]);
        const inp = document.createElement('input');
        inp.id = 'ticker';
        inp.value = 'aapl';
        document.body.appendChild(inp);
        expect(window.getValidTickers()).toEqual(['AAPL']);
        document.body.innerHTML = '';
        window.initializeOptionsTable();
        window.toggleOptionsSection();
        window.toggleSizingSection();
        window.appState.chainCache.get('AAPL');
        window.appState.chainCache.set('AAPL', { spot: 1 });
        window.appState.chainCache.get('AAPL');
        window.appState.chainCache.set('AAPL', { spot: 2 });
    });

    it('theme manager get / set / toggle + label sync', () => {
        document.documentElement.removeAttribute('data-theme');
        const btn = document.createElement('button');
        btn.id = 'theme-toggle';
        document.body.appendChild(btn);

        expect(window.themeManager.get()).toBe('dark');
        window.themeManager.set('light');
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');
        expect(btn.getAttribute('aria-label')).toBe('Switch to dark mode');
        window.themeManager.set('sepia');        // invalid -> dark
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
        window.themeManager.toggle();            // dark -> light
        expect(document.documentElement.getAttribute('data-theme')).toBe('light');

        document.body.innerHTML = '';
        document.documentElement.removeAttribute('data-theme');
    });

    it('state modules exercised', () => {
        // abortRegistry
        const s1 = window.appState.aborts.begin('k1');
        window.appState.aborts.begin('k1');     // aborts s1
        expect(s1.aborted).toBe(true);
        window.appState.aborts.abort('k1');
        window.appState.aborts.abort('unknown');
        window.appState.aborts.begin('k2');
        window.appState.aborts.abortAll();
        window.appState.aborts.begin('');

        // chainCache
        window.appState.chainCache.set('', null);
        window.appState.chainCache.set('AAPL', { spot: 1 });
        window.appState.chainCache.has('AAPL');
        window.appState.chainCache.get('AAPL');
        window.appState.chainCache.get('');
        window.appState.chainCache.clear();

        // optionChain
        window.appState.optionChain.setData({ x: 1 });
        window.appState.optionChain.getData();
        window.appState.optionChain.setActiveExp('2026-05-15');
        window.appState.optionChain.getActiveExp();
        window.appState.optionChain.beginRequest();
        window.appState.optionChain.beginRequest();
        window.appState.optionChain.abort();
        window.appState.optionChain.reset();

        // payoffRatio
        window.appState.payoffRatio.setData({ rows: [] });
        window.appState.payoffRatio.getData();
        window.appState.payoffRatio.beginRequest();
        window.appState.payoffRatio.beginRequest();
        window.appState.payoffRatio.abort();
        window.appState.payoffRatio.reset();

        // tabFlags
        window.appState.tabFlags.markLoaded('a');
        window.appState.tabFlags.isLoaded('a');
        window.appState.tabFlags.reset('a');
        window.appState.tabFlags.reset('never');
        window.appState.tabFlags.markLoaded('b');
        window.appState.tabFlags.resetAll();

        // panels
        window.appState.panels.set('p', 'idle');
        window.appState.panels.set('p', 'loading');
        window.appState.panels.set('p', 'loaded', { data: 1 });
        window.appState.panels.set('p', 'error', { message: 'm' });
        window.appState.panels.set('p', 'empty');
        window.appState.panels.get('p');
        window.appState.panels.get('missing');
        expect(() => window.appState.panels.set('p', 'bogus')).toThrow();
        expect(() => window.appState.panels.set('', 'idle')).toThrow();

        // panelState Alpine factory
        const inst = window.panelState('p');
        inst.init();
        window.appState.panels.set('p', 'loaded', { data: { a: 1 } });
        inst.is('loaded');
        expect(() => window.panelState('p', 'bogus')).toThrow();
    });
});


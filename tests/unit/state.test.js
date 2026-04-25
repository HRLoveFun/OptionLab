/**
 * Tests for state modules under static/state/.
 *
 * These cover the canonical accessors that replace ad-hoc window globals:
 *   abortRegistry, chainCacheState, optionChainState, oddsChainState,
 *   tabFlagsState, panelState.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript, loadStateBundle } from './_loadScript.js';

beforeEach(() => {
    loadStateBundle();
});

describe('abortRegistry', () => {
    it('begin(key) returns an AbortSignal', () => {
        const sig = window.appState.aborts.begin('k');
        expect(sig).toBeInstanceOf(AbortSignal);
        expect(sig.aborted).toBe(false);
    });

    it('begin(key) twice aborts the first signal', () => {
        const a = window.appState.aborts.begin('shared');
        const b = window.appState.aborts.begin('shared');
        expect(a.aborted).toBe(true);
        expect(b.aborted).toBe(false);
    });

    it('abort(key) aborts the bound signal and clears the slot', () => {
        const sig = window.appState.aborts.begin('foo');
        window.appState.aborts.abort('foo');
        expect(sig.aborted).toBe(true);
        // After clear, a new begin returns a fresh signal.
        const next = window.appState.aborts.begin('foo');
        expect(next.aborted).toBe(false);
    });

    it('abort(unknown) is a no-op', () => {
        expect(() => window.appState.aborts.abort('nope')).not.toThrow();
    });

    it('abortAll cancels every registered controller', () => {
        const a = window.appState.aborts.begin('a');
        const b = window.appState.aborts.begin('b');
        window.appState.aborts.abortAll();
        expect(a.aborted).toBe(true);
        expect(b.aborted).toBe(true);
    });

    it('begin without key returns a one-shot detached signal', () => {
        const sig = window.appState.aborts.begin('');
        expect(sig).toBeInstanceOf(AbortSignal);
    });
});

describe('chainCacheState', () => {
    it('get/set roundtrip preserves data and stamps _ts', () => {
        window.appState.chainCache.set('AAPL', { spot: 100 });
        const got = window.appState.chainCache.get('AAPL');
        expect(got.spot).toBe(100);
        expect(typeof got._ts).toBe('number');
    });

    it('expires entries beyond TTL', () => {
        window.appState.chainCache.set('AAPL', { spot: 100 });
        const now = Date.now();
        const ttl = window.appState.chainCache.TTL_MS;
        const spy = vi.spyOn(Date, 'now').mockReturnValue(now + ttl + 1);
        expect(window.appState.chainCache.get('AAPL')).toBeNull();
        expect(window.appState.chainCache.has('AAPL')).toBe(false);
        spy.mockRestore();
    });

    it('get(missing) returns null', () => {
        expect(window.appState.chainCache.get('UNKNOWN')).toBeNull();
        expect(window.appState.chainCache.get('')).toBeNull();
    });

    it('set with falsy ticker or data is a no-op', () => {
        window.appState.chainCache.set('', { x: 1 });
        window.appState.chainCache.set('AAPL', null);
        expect(window.appState.chainCache.get('AAPL')).toBeNull();
    });

    it('emits chain_cache:set on set and chain_cache:cleared on clear', () => {
        const setHandler = vi.fn();
        const clearHandler = vi.fn();
        window.bus.on('chain_cache:set', setHandler);
        window.bus.on('chain_cache:cleared', clearHandler);
        window.appState.chainCache.set('AAPL', { spot: 1 });
        window.appState.chainCache.clear();
        expect(setHandler).toHaveBeenCalledWith(expect.objectContaining({ ticker: 'AAPL' }));
        expect(clearHandler).toHaveBeenCalled();
    });
});

describe('optionChainState', () => {
    it('setData emits option_chain:loaded and updates getData', () => {
        const handler = vi.fn();
        window.bus.on('option_chain:loaded', handler);
        const data = { expirations: ['2026-05-15'], chain: {}, spot: 100 };
        window.appState.optionChain.setData(data);
        expect(handler).toHaveBeenCalledWith(data);
        expect(window.appState.optionChain.getData()).toBe(data);
    });

    it('setActiveExp updates and emits exp_changed', () => {
        const handler = vi.fn();
        window.bus.on('option_chain:exp_changed', handler);
        window.appState.optionChain.setActiveExp('2026-06-19');
        expect(handler).toHaveBeenCalledWith('2026-06-19');
        expect(window.appState.optionChain.getActiveExp()).toBe('2026-06-19');
    });

    it('beginRequest aborts any prior controller', () => {
        const s1 = window.appState.optionChain.beginRequest();
        const s2 = window.appState.optionChain.beginRequest();
        expect(s1.aborted).toBe(true);
        expect(s2.aborted).toBe(false);
    });

    it('reset clears data, active expiration, and emits cleared', () => {
        const handler = vi.fn();
        window.bus.on('option_chain:cleared', handler);
        window.appState.optionChain.setData({ chain: {} });
        window.appState.optionChain.setActiveExp('2026-05-15');
        window.appState.optionChain.reset();
        expect(window.appState.optionChain.getData()).toBeNull();
        expect(window.appState.optionChain.getActiveExp()).toBeNull();
        expect(handler).toHaveBeenCalled();
    });
});

describe('oddsChainState', () => {
    it('setData/getData and reset emit the right events', () => {
        const loaded = vi.fn();
        const cleared = vi.fn();
        window.bus.on('odds_chain:loaded', loaded);
        window.bus.on('odds_chain:cleared', cleared);
        window.appState.oddsChain.setData({ rows: [1, 2] });
        expect(loaded).toHaveBeenCalledWith({ rows: [1, 2] });
        window.appState.oddsChain.reset();
        expect(window.appState.oddsChain.getData()).toBeNull();
        expect(cleared).toHaveBeenCalled();
    });

    it('beginRequest aborts the prior signal', () => {
        const s1 = window.appState.oddsChain.beginRequest();
        const s2 = window.appState.oddsChain.beginRequest();
        expect(s1.aborted).toBe(true);
        expect(s2.aborted).toBe(false);
    });
});

describe('tabFlagsState', () => {
    it('isLoaded/markLoaded/reset roundtrip', () => {
        expect(window.appState.tabFlags.isLoaded('market_review')).toBe(false);
        window.appState.tabFlags.markLoaded('market_review');
        expect(window.appState.tabFlags.isLoaded('market_review')).toBe(true);
        window.appState.tabFlags.reset('market_review');
        expect(window.appState.tabFlags.isLoaded('market_review')).toBe(false);
    });

    it('resetAll clears all flags and emits the bulk event', () => {
        window.appState.tabFlags.markLoaded('a');
        window.appState.tabFlags.markLoaded('b');
        const handler = vi.fn();
        window.bus.on('tab_flags:reset_all', handler);
        window.appState.tabFlags.resetAll();
        expect(window.appState.tabFlags.isLoaded('a')).toBe(false);
        expect(window.appState.tabFlags.isLoaded('b')).toBe(false);
        expect(handler).toHaveBeenCalled();
    });

    it('reset on an unloaded tab does not emit', () => {
        const handler = vi.fn();
        window.bus.on('tab_flags:changed', handler);
        window.appState.tabFlags.reset('never_loaded');
        expect(handler).not.toHaveBeenCalled();
    });
});

describe('panelState', () => {
    it('rejects invalid phase', () => {
        expect(() => window.appState.panels.set('p', 'unknown')).toThrow(/invalid phase/);
    });

    it('rejects missing id', () => {
        expect(() => window.appState.panels.set('', 'idle')).toThrow(/id is required/);
    });

    it('emits panel:<id> with phase/message/data', () => {
        const handler = vi.fn();
        window.bus.on('panel:option_chain', handler);
        window.appState.panels.set('option_chain', 'loading');
        window.appState.panels.set('option_chain', 'error', { message: 'oops' });
        window.appState.panels.set('option_chain', 'loaded', { data: { rows: [] } });
        expect(handler).toHaveBeenCalledTimes(3);
        expect(handler).toHaveBeenLastCalledWith({
            phase: 'loaded', message: '', data: { rows: [] },
        });
    });

    it('get returns idle default when never set', () => {
        expect(window.appState.panels.get('never')).toEqual({
            phase: 'idle', message: '', data: undefined,
        });
    });

    it('Alpine factory hydrates from existing state and updates on emit', () => {
        window.appState.panels.set('chart', 'loading');
        const inst = window.panelState('chart');
        inst.init();
        expect(inst.phase).toBe('loading');
        window.appState.panels.set('chart', 'error', { message: 'nope' });
        expect(inst.phase).toBe('error');
        expect(inst.message).toBe('nope');
        expect(inst.is('error')).toBe(true);
    });

    it('panelState factory rejects invalid initial phase', () => {
        expect(() => window.panelState('p', 'bogus')).toThrow(/invalid initial phase/);
    });
});

describe('store.js bootstrap', () => {
    it('throws if eventBus is missing', () => {
        delete window.appState;
        delete window.bus;
        delete window.eventBus;
        expect(() => loadScript('static/state/store.js')).toThrow(/eventBus.js must load before/);
    });

    it('is idempotent — second load does not overwrite', () => {
        const original = window.appState;
        loadStateBundle();
        expect(window.appState).toBe(original);
    });
});

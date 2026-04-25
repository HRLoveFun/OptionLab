/**
 * Tests for static/eventBus.js — pub/sub bus and state container.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript } from './_loadScript.js';

describe('eventBus', () => {
    beforeEach(() => {
        loadScript('static/eventBus.js');
    });

    it('exposes both window.bus and window.eventBus aliases', () => {
        expect(window.bus).toBeDefined();
        expect(window.eventBus).toBe(window.bus);
    });

    it('emits to subscribers', () => {
        const handler = vi.fn();
        window.bus.on('foo', handler);
        window.bus.emit('foo', { x: 1 });
        expect(handler).toHaveBeenCalledWith({ x: 1 });
    });

    it('emit without subscribers is a no-op', () => {
        expect(() => window.bus.emit('nobody', 'data')).not.toThrow();
    });

    it('on() returns an unsubscribe function', () => {
        const handler = vi.fn();
        const off = window.bus.on('evt', handler);
        off();
        window.bus.emit('evt', 1);
        expect(handler).not.toHaveBeenCalled();
    });

    it('once() fires exactly once', () => {
        const handler = vi.fn();
        window.bus.once('evt', handler);
        window.bus.emit('evt', 1);
        window.bus.emit('evt', 2);
        expect(handler).toHaveBeenCalledTimes(1);
        expect(handler).toHaveBeenCalledWith(1);
    });

    it('off() removes a specific listener without affecting others', () => {
        const a = vi.fn();
        const b = vi.fn();
        window.bus.on('evt', a);
        window.bus.on('evt', b);
        window.bus.off('evt', a);
        window.bus.emit('evt', 'x');
        expect(a).not.toHaveBeenCalled();
        expect(b).toHaveBeenCalledWith('x');
    });

    it('listener errors are swallowed and do not break siblings', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => { });
        const bad = vi.fn(() => { throw new Error('boom'); });
        const good = vi.fn();
        window.bus.on('evt', bad);
        window.bus.on('evt', good);
        window.bus.emit('evt', 1);
        expect(bad).toHaveBeenCalled();
        expect(good).toHaveBeenCalledWith(1);
        consoleSpy.mockRestore();
    });

    it('emit during iteration does not skip / re-enter listeners', () => {
        const calls = [];
        window.bus.on('evt', () => {
            calls.push('first');
            // Add a new listener mid-iteration; should not be invoked this round.
            window.bus.on('evt', () => calls.push('late'));
        });
        window.bus.on('evt', () => calls.push('second'));
        window.bus.emit('evt');
        expect(calls).toEqual(['first', 'second']);
    });

    describe('state container', () => {
        it('get/set/has/delete/clear roundtrip', () => {
            const s = window.bus.state;
            expect(s.has('k')).toBe(false);
            expect(s.get('k', 42)).toBe(42);
            s.set('k', 'v');
            expect(s.has('k')).toBe(true);
            expect(s.get('k')).toBe('v');
            expect(s.delete('k')).toBe(true);
            expect(s.delete('k')).toBe(false);
            s.set('a', 1); s.set('b', 2);
            s.clear();
            expect(s.has('a')).toBe(false);
        });

        it('set emits state:<key>', () => {
            const handler = vi.fn();
            window.bus.on('state:hello', handler);
            window.bus.state.set('hello', 'world');
            expect(handler).toHaveBeenCalledWith('world');
        });

        it('delete emits state:<key> with undefined when key existed', () => {
            const handler = vi.fn();
            window.bus.state.set('k', 1);
            window.bus.on('state:k', handler);
            window.bus.state.delete('k');
            expect(handler).toHaveBeenCalledWith(undefined);
        });
    });
});

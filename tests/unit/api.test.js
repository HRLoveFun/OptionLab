/**
 * Tests for static/api.js — fetch wrapper with abort + error normalization.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript } from './_loadScript.js';

function _mockFetch(impl) {
    window.fetch = vi.fn(impl);
}

function _jsonResponse(body, { status = 200, headers = {} } = {}) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { 'content-type': 'application/json', ...headers },
    });
}

describe('api wrapper', () => {
    beforeEach(() => {
        loadScript('static/api.js');
    });

    it('GET returns parsed JSON', async () => {
        _mockFetch(async () => _jsonResponse({ ok: true, value: 1 }));
        const data = await window.api.get('/foo');
        expect(data).toEqual({ ok: true, value: 1 });
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });

    it('POST with object body sets JSON content-type and stringifies', async () => {
        _mockFetch(async (url, opts) => {
            expect(opts.method).toBe('POST');
            expect(opts.headers['Content-Type']).toBe('application/json');
            expect(opts.body).toBe(JSON.stringify({ a: 1 }));
            return _jsonResponse({ ok: true });
        });
        await window.api.post('/foo', { body: { a: 1 } });
    });

    it('POST with FormData does not stringify or set Content-Type', async () => {
        const fd = new FormData();
        fd.append('k', 'v');
        _mockFetch(async (url, opts) => {
            expect(opts.body).toBe(fd);
            expect(opts.headers['Content-Type']).toBeUndefined();
            return _jsonResponse({ ok: true });
        });
        await window.api.post('/foo', { body: fd });
    });

    it('non-2xx with JSON body throws ApiError with normalized fields', async () => {
        _mockFetch(async () =>
            _jsonResponse({ error: 'bad input', code: 'invalid' }, { status: 400 })
        );
        try {
            await window.api.get('/foo');
            throw new Error('expected ApiError');
        } catch (err) {
            expect(err).toBeInstanceOf(window.ApiError);
            expect(err.ok).toBe(false);
            expect(err.status).toBe(400);
            expect(err.code).toBe('invalid');
            expect(err.message).toBe('bad input');
            expect(err.detail).toEqual({ error: 'bad input', code: 'invalid' });
        }
    });

    it('non-2xx with text body falls back to http_<status> code', async () => {
        _mockFetch(async () =>
            new Response('Server exploded', {
                status: 500,
                headers: { 'content-type': 'text/plain' },
                statusText: 'Internal Server Error',
            })
        );
        try {
            await window.api.get('/foo');
            throw new Error('expected ApiError');
        } catch (err) {
            expect(err.status).toBe(500);
            expect(err.code).toBe('http_500');
            expect(err.detail).toBe('Server exploded');
        }
    });

    it('network failure throws ApiError with code=network_error', async () => {
        _mockFetch(async () => { throw new TypeError('Failed to fetch'); });
        await expect(window.api.get('/foo')).rejects.toMatchObject({
            name: 'ApiError',
            status: 0,
            code: 'network_error',
        });
    });

    it('AbortError is preserved (not wrapped)', async () => {
        _mockFetch(async () => {
            const e = new Error('aborted');
            e.name = 'AbortError';
            throw e;
        });
        await expect(window.api.get('/foo', { key: 'k' })).rejects.toMatchObject({
            name: 'AbortError',
        });
    });

    it('keyed requests cancel the prior in-flight one', async () => {
        let firstSignal = null;
        let resolveFirst;
        _mockFetch((url, opts) => {
            if (!firstSignal) {
                firstSignal = opts.signal;
                return new Promise((_resolve, reject) => {
                    opts.signal.addEventListener('abort', () => {
                        const e = new Error('aborted');
                        e.name = 'AbortError';
                        reject(e);
                    });
                    resolveFirst = _resolve;
                });
            }
            return Promise.resolve(_jsonResponse({ second: true }));
        });

        const first = window.api.get('/foo', { key: 'shared' });
        const second = window.api.get('/foo', { key: 'shared' });

        await expect(first).rejects.toMatchObject({ name: 'AbortError' });
        expect(firstSignal.aborted).toBe(true);
        await expect(second).resolves.toEqual({ second: true });
    });

    it('api.abort(key) cancels the bound request', async () => {
        let captured;
        _mockFetch((url, opts) => {
            captured = opts.signal;
            return new Promise((_, reject) => {
                opts.signal.addEventListener('abort', () => {
                    const e = new Error('aborted');
                    e.name = 'AbortError';
                    reject(e);
                });
            });
        });
        const p = window.api.get('/foo', { key: 'cancellable' });
        window.api.abort('cancellable');
        await expect(p).rejects.toMatchObject({ name: 'AbortError' });
        expect(captured.aborted).toBe(true);
    });

    it('parse: text returns raw text', async () => {
        _mockFetch(async () => new Response('hello', {
            status: 200, headers: { 'content-type': 'text/plain' },
        }));
        const out = await window.api.get('/foo', { parse: 'text' });
        expect(out).toBe('hello');
    });

    it('parse: response returns the Response object', async () => {
        _mockFetch(async () => _jsonResponse({ ok: true }));
        const resp = await window.api.get('/foo', { parse: 'response' });
        expect(resp).toBeInstanceOf(Response);
    });

    it('auto parse handles non-JSON text content', async () => {
        _mockFetch(async () => new Response('plain', {
            status: 200, headers: { 'content-type': 'text/plain' },
        }));
        const out = await window.api.get('/foo');
        expect(out).toBe('plain');
    });

    it('timeoutMs aborts a slow request', async () => {
        _mockFetch((url, opts) => new Promise((_, reject) => {
            opts.signal.addEventListener('abort', () => {
                const e = new Error('aborted');
                e.name = 'AbortError';
                reject(e);
            });
        }));
        await expect(
            window.api.get('/foo', { key: 't', timeoutMs: 10 })
        ).rejects.toMatchObject({ name: 'AbortError' });
    });

    it('passing an external signal short-circuits internal controller', async () => {
        const ctrl = new AbortController();
        let received;
        _mockFetch((url, opts) => {
            received = opts.signal;
            return _jsonResponse({ ok: true });
        });
        await window.api.get('/foo', { signal: ctrl.signal });
        expect(received).toBe(ctrl.signal);
    });
});

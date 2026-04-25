/* api.js — unified fetch wrapper with AbortController & error normalization.
 *
 * Goals:
 *   - one place to set headers, parse JSON, handle non-2xx, and surface
 *     a normalized error shape: { ok:false, status, code, message, detail }
 *   - per-key AbortController registry so callers can cancel previous
 *     in-flight requests (e.g. typing into ticker input) without leaking
 *     globals like window._gameAbort / _ocAbort.
 *
 * Usage:
 *   const data = await api.get('/api/regime/current?ticker=AAPL');
 *   const data = await api.post('/api/game', { body: payload, key: 'game' });
 *   api.abort('game');           // cancel the previous 'game' request
 *
 * All thrown errors are ApiError instances (extending Error) with the
 * normalized fields above. AbortError is preserved (err.name === 'AbortError')
 * so callers can distinguish user-cancellation from real failures.
 */
(function (root) {
    'use strict';

    const _controllers = new Map();   // key -> AbortController

    class ApiError extends Error {
        constructor({ status, code, message, detail }) {
            super(message || 'Request failed');
            this.name = 'ApiError';
            this.ok = false;
            this.status = status ?? 0;
            this.code = code || 'unknown_error';
            this.detail = detail ?? null;
        }
    }

    function _registerController(key) {
        if (!key) return new AbortController();
        // cancel any prior request bound to the same key
        const prev = _controllers.get(key);
        if (prev) {
            try { prev.abort(); } catch (_) { /* ignore */ }
        }
        const ctrl = new AbortController();
        _controllers.set(key, ctrl);
        return ctrl;
    }

    function _clearController(key, ctrl) {
        if (!key) return;
        if (_controllers.get(key) === ctrl) _controllers.delete(key);
    }

    function abort(key) {
        const ctrl = _controllers.get(key);
        if (ctrl) {
            try { ctrl.abort(); } catch (_) { /* ignore */ }
            _controllers.delete(key);
        }
    }

    async function _normalizeErrorBody(resp) {
        const ct = resp.headers.get('content-type') || '';
        try {
            if (ct.includes('application/json')) {
                const j = await resp.json();
                return {
                    code: j.code || j.error_code || `http_${resp.status}`,
                    message: j.error || j.message || resp.statusText || 'Request failed',
                    detail: j,
                };
            }
            const text = await resp.text();
            return {
                code: `http_${resp.status}`,
                message: resp.statusText || 'Request failed',
                detail: text ? text.slice(0, 500) : null,
            };
        } catch (_) {
            return { code: `http_${resp.status}`, message: resp.statusText || 'Request failed', detail: null };
        }
    }

    async function request(url, opts = {}) {
        const {
            method = 'GET',
            body,
            headers = {},
            key,
            signal,
            timeoutMs,
            parse = 'auto',   // 'auto' | 'json' | 'text' | 'response'
            credentials = 'same-origin',
        } = opts;

        const ctrl = signal ? null : _registerController(key);
        const finalSignal = signal || (ctrl ? ctrl.signal : undefined);

        let timeoutId = null;
        if (timeoutMs && ctrl) {
            timeoutId = setTimeout(() => {
                try { ctrl.abort(); } catch (_) { /* ignore */ }
            }, timeoutMs);
        }

        const finalHeaders = { Accept: 'application/json', ...headers };
        let finalBody = body;
        if (body && typeof body === 'object' && !(body instanceof FormData) && !(body instanceof Blob)) {
            finalHeaders['Content-Type'] = finalHeaders['Content-Type'] || 'application/json';
            finalBody = JSON.stringify(body);
        }

        let resp;
        try {
            resp = await fetch(url, {
                method,
                headers: finalHeaders,
                body: finalBody,
                signal: finalSignal,
                credentials,
            });
        } catch (err) {
            if (timeoutId) clearTimeout(timeoutId);
            _clearController(key, ctrl);
            if (err && err.name === 'AbortError') throw err;
            throw new ApiError({
                status: 0,
                code: 'network_error',
                message: err && err.message ? err.message : 'Network error',
                detail: null,
            });
        }

        if (timeoutId) clearTimeout(timeoutId);
        _clearController(key, ctrl);

        if (!resp.ok) {
            const norm = await _normalizeErrorBody(resp);
            throw new ApiError({ status: resp.status, ...norm });
        }

        if (parse === 'response') return resp;
        if (parse === 'text') return resp.text();
        if (parse === 'json') return resp.json();

        // auto
        const ct = resp.headers.get('content-type') || '';
        if (ct.includes('application/json')) return resp.json();
        if (ct.startsWith('text/')) return resp.text();
        return resp;
    }

    const api = {
        request,
        abort,
        ApiError,
        get: (url, opts = {}) => request(url, { ...opts, method: 'GET' }),
        post: (url, opts = {}) => request(url, { ...opts, method: 'POST' }),
        put: (url, opts = {}) => request(url, { ...opts, method: 'PUT' }),
        delete: (url, opts = {}) => request(url, { ...opts, method: 'DELETE' }),
    };

    root.api = api;
    root.ApiError = ApiError;
})(window);

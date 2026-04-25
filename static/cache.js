/* cache.js — client-side cache helpers (schema-versioned).
 *
 * Two responsibilities:
 *
 * 1. Schema version sentinel for `localStorage` so a deploy that changes the
 *    persisted form/config shape automatically purges any incompatible
 *    entries on the next page load. Bump `CACHE_SCHEMA_VERSION` whenever
 *    the localStorage layout changes; old keys are wiped silently.
 *
 * 2. A typed `sessionCache` helper backed by `sessionStorage` for caching
 *    expensive analysis responses by `(ticker, date_range)` so switching
 *    between recently-viewed tickers in the same tab is instantaneous.
 *
 * Loaded via <script> tag before main.js — exposes `window.appCache`.
 */
(function (root) {
    'use strict';

    // Bump this whenever the shape of any persisted cache changes.
    const CACHE_SCHEMA_VERSION = 2;
    const SCHEMA_KEY = '__cache_schema_version__';
    // Keys belonging to OptionView that participate in versioning.
    const MANAGED_LOCAL_KEYS = ['marketAnalysisForm', 'marketAnalysisConfig'];
    // Prefix for sessionStorage analysis cache entries.
    const SESSION_PREFIX = 'mv:analysis:';
    const SESSION_DEFAULT_TTL_MS = 30 * 60 * 1000;  // 30 minutes
    const SESSION_MAX_ENTRIES = 8;

    function _safeGet(storage, key) {
        try { return storage.getItem(key); } catch (_) { return null; }
    }
    function _safeSet(storage, key, value) {
        try { storage.setItem(key, value); return true; } catch (_) { return false; }
    }
    function _safeRemove(storage, key) {
        try { storage.removeItem(key); } catch (_) { /* ignore */ }
    }

    /* Validate (and migrate) the schema version. Runs once at script load.
       On mismatch we wipe ONLY the keys we manage so unrelated apps in the
       same origin (e.g. browser extensions) keep their data. */
    function _ensureSchema() {
        const stored = _safeGet(localStorage, SCHEMA_KEY);
        if (stored === String(CACHE_SCHEMA_VERSION)) return;
        for (const k of MANAGED_LOCAL_KEYS) _safeRemove(localStorage, k);
        // Clear all sessionStorage entries we own (analysis cache).
        try {
            const toDelete = [];
            for (let i = 0; i < sessionStorage.length; i++) {
                const k = sessionStorage.key(i);
                if (k && k.startsWith(SESSION_PREFIX)) toDelete.push(k);
            }
            toDelete.forEach((k) => _safeRemove(sessionStorage, k));
        } catch (_) { /* ignore */ }
        _safeSet(localStorage, SCHEMA_KEY, String(CACHE_SCHEMA_VERSION));
        if (stored !== null) {
            try { console.info('[cache] schema bumped', stored, '→', CACHE_SCHEMA_VERSION); } catch (_) { /* ignore */ }
        }
    }

    /* Tiny FNV-1a 32-bit hash → hex string. Stable across page loads.
       Used to compress (ticker + date_range) into a fixed-length cache key. */
    function _hash(s) {
        let h = 0x811c9dc5;
        for (let i = 0; i < s.length; i++) {
            h ^= s.charCodeAt(i);
            h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
        }
        return ('00000000' + h.toString(16)).slice(-8);
    }

    function buildKey(ticker, startDate, endDate, extra) {
        const t = (ticker || '').toUpperCase();
        const range = `${startDate || ''}|${endDate || ''}`;
        const ex = extra ? JSON.stringify(extra) : '';
        return SESSION_PREFIX + t + ':' + _hash(range + '|' + ex);
    }

    function _evictOldest() {
        try {
            const entries = [];
            for (let i = 0; i < sessionStorage.length; i++) {
                const k = sessionStorage.key(i);
                if (k && k.startsWith(SESSION_PREFIX)) {
                    const raw = _safeGet(sessionStorage, k);
                    if (!raw) continue;
                    try {
                        const parsed = JSON.parse(raw);
                        entries.push({ k, ts: parsed && parsed._ts ? parsed._ts : 0 });
                    } catch (_) { _safeRemove(sessionStorage, k); }
                }
            }
            if (entries.length <= SESSION_MAX_ENTRIES) return;
            entries.sort((a, b) => a.ts - b.ts);
            const toRemove = entries.slice(0, entries.length - SESSION_MAX_ENTRIES);
            toRemove.forEach((e) => _safeRemove(sessionStorage, e.k));
        } catch (_) { /* ignore */ }
    }

    const sessionCache = {
        /* Read a cached payload. Returns `null` on miss / expiry / parse error. */
        get(ticker, startDate, endDate, extra) {
            const key = buildKey(ticker, startDate, endDate, extra);
            const raw = _safeGet(sessionStorage, key);
            if (!raw) return null;
            try {
                const parsed = JSON.parse(raw);
                if (!parsed || typeof parsed !== 'object') return null;
                if (parsed._ts && (Date.now() - parsed._ts) > SESSION_DEFAULT_TTL_MS) {
                    _safeRemove(sessionStorage, key);
                    return null;
                }
                return parsed.data;
            } catch (_) {
                _safeRemove(sessionStorage, key);
                return null;
            }
        },

        /* Persist a payload. Silent on quota errors; oldest entries are
           evicted first so the cache never grows beyond `SESSION_MAX_ENTRIES`. */
        set(ticker, startDate, endDate, extra, data) {
            const key = buildKey(ticker, startDate, endDate, extra);
            const payload = JSON.stringify({ _ts: Date.now(), data });
            if (!_safeSet(sessionStorage, key, payload)) {
                _evictOldest();
                _safeSet(sessionStorage, key, payload);
            }
            _evictOldest();
        },

        clear() {
            try {
                const toDelete = [];
                for (let i = 0; i < sessionStorage.length; i++) {
                    const k = sessionStorage.key(i);
                    if (k && k.startsWith(SESSION_PREFIX)) toDelete.push(k);
                }
                toDelete.forEach((k) => _safeRemove(sessionStorage, k));
            } catch (_) { /* ignore */ }
        },

        // Exposed for tests / debugging.
        _buildKey: buildKey,
    };

    _ensureSchema();

    root.appCache = {
        SCHEMA_VERSION: CACHE_SCHEMA_VERSION,
        session: sessionCache,
    };
})(window);

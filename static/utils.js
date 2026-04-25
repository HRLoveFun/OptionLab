// Shared utility functions used across all JS modules.

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const s = String(text);
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

let currentPrice = null;

// Option chain cache moved to static/state/chainCacheState.js (appState.chainCache).
// These thin shims preserve legacy callers; new code should call
// `appState.chainCache.get(ticker)` / `.set(ticker, data)` directly.
function _chainCacheGet(ticker) {
    return window.appState && window.appState.chainCache
        ? window.appState.chainCache.get(ticker)
        : null;
}

function _chainCacheSet(ticker, data) {
    if (window.appState && window.appState.chainCache) {
        window.appState.chainCache.set(ticker, data);
    }
}

function parseTickers(rawInput) {
    return rawInput
        .split(/[,\n]+/)
        .map(t => t.trim().toUpperCase())
        .filter(t => t.length > 0)
        .filter((t, i, arr) => arr.indexOf(t) === i);
}

function getValidTickers() {
    const input = document.getElementById('ticker');
    return input ? parseTickers(input.value) : [];
}

function toggleOptionsSection() {
    // No-op: Positions section is now always visible
}

function toggleSizingSection() {
    // No-op: Position Sizing section is now always visible
}

function initializeOptionsTable() {
    const tbody = document.getElementById('positions-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    addPositionRow();
}

// Explicit `window` exports.
//
// When this file is loaded as a classic `<script>` (production), top-level
// function declarations already attach to `window` via the script's global
// scope, so these assignments are no-ops. When loaded as an ES module (e.g.
// in vitest unit tests), top-level decls live in module scope, so we need
// to publish them explicitly for callers that look on `window`.
if (typeof window !== 'undefined') {
    window.escapeHtml = escapeHtml;
    window.parseTickers = parseTickers;
    window.getValidTickers = getValidTickers;
    window.toggleOptionsSection = toggleOptionsSection;
    window.toggleSizingSection = toggleSizingSection;
    window.initializeOptionsTable = initializeOptionsTable;
    window._chainCacheGet = _chainCacheGet;
    window._chainCacheSet = _chainCacheSet;
}

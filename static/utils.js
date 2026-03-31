// Shared utility functions used across all JS modules.

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const s = String(text);
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

let currentPrice = null;
window._chainCache = {};  // Module 1: option chain cache per ticker
const _CHAIN_CACHE_TTL = 5 * 60 * 1000;  // 5 minutes in ms

function _chainCacheGet(ticker) {
    const entry = window._chainCache[ticker];
    if (!entry) return null;
    if (Date.now() - entry._ts > _CHAIN_CACHE_TTL) {
        delete window._chainCache[ticker];
        return null;
    }
    return entry;
}

function _chainCacheSet(ticker, data) {
    window._chainCache[ticker] = { ...data, _ts: Date.now() };
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

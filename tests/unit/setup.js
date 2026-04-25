// Vitest global setup: ensure each test gets a clean DOM/window state.
// jsdom provides `window`/`document` globally; we just reset module side
// effects (e.g. window.bus, window.appState) between tests.
import { afterEach, beforeEach } from 'vitest';

beforeEach(() => {
    // Reset known globals attached by IIFE modules. The `_loadScript` helper
    // re-imports each source with a unique query string per test so module
    // bodies re-execute and re-publish to `window`.
    delete window.bus;
    delete window.eventBus;
    delete window.api;
    delete window.ApiError;
    delete window.appState;
    delete window.escapeHtml;
    delete window.parseTickers;
    delete window.getValidTickers;
    delete window._chainCacheGet;
    delete window._chainCacheSet;
    delete window.initializeOptionsTable;
    delete window.toggleOptionsSection;
    delete window.toggleSizingSection;
    delete window.panelState;
    document.body.innerHTML = '';
});

afterEach(() => {
    try { window.localStorage.clear(); } catch (_) { /* ignore */ }
});

/**
 * Tests for static/state/paramsStore.js + the three module parameter groups
 * (batch B7).
 *
 * Contract under test:
 *   - a group hydrates its toolbar inputs from its own localStorage key;
 *   - a change on any bound input commits the WHOLE group and emits
 *     `module:params-changed` with the modules that consume it;
 *   - the shared horizon is one field bound to three toolbars, so all three
 *     inputs stay in sync;
 *   - disabled storage degrades to defaults instead of throwing;
 *   - `init()` returns the store (callers chain `.init()` onto the factory).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript } from './_loadScript.js';

const MARKET_TOOLBAR_HTML = `
<input type="month" id="mr-from" name="from">
<input type="month" id="mr-to" name="to">
<input type="month" id="stat-from" name="from">
<input type="month" id="stat-to" name="to">
<select id="stat-frequency" name="frequency">
  <option value="D"></option><option value="W"></option>
  <option value="ME"></option><option value="QE"></option>
</select>
<input type="month" id="assess-from" name="from">
<input type="month" id="assess-to" name="to">
<select id="assess-frequency" name="frequency">
  <option value="D"></option><option value="W"></option>
  <option value="ME"></option><option value="QE"></option>
</select>
<input type="hidden" id="start_time" name="start_time">
<input type="hidden" id="end_time" name="end_time">`;

const ASSESS_TOOLBAR_HTML = `
<select id="assess-side-bias" name="side_bias">
  <option value="Natural"></option><option value="Neutral"></option>
</select>
<input type="number" id="assess-risk-threshold" name="risk_threshold">
<input type="number" id="assess-rolling-window" name="rolling_window">
<input type="number" id="assess-account-size" name="account_size">
<input type="number" id="assess-max-risk-pct" name="max_risk_pct">`;

const OPTION_TOOLBAR_HTML = `
<input type="number" id="oc-max-dte" name="max_dte">
<input type="number" id="oc-moneyness-low" name="moneyness_low">
<input type="number" id="oc-moneyness-high" name="moneyness_high">
<input type="number" id="oc-max-contracts" name="max_contracts">
<input type="number" id="oc-refresh-interval" name="refresh_interval">`;

function mount(html) {
    document.body.innerHTML = html;
}

beforeEach(() => {
    window.localStorage.clear();
    delete window.appState;
    delete window.createParamsStore;
    delete window.__paramsDebug;
    loadScript('static/eventBus.js');
    loadScript('static/state/store.js');
    loadScript('static/state/paramsStore.js');
});

/** Mount the markup, THEN load the store scripts — the real page order: the
 *  toolbars are parsed before the scripts hydrate and bind them. */
function loadStores() {
    loadScript('static/state/marketParamsState.js');
    loadScript('static/state/assessmentParamsState.js');
    loadScript('static/state/optionFilterState.js');
}

describe('marketParams — hydration at parse time', () => {
    it('restores the group from its own localStorage key', () => {
        window.localStorage.setItem(
            'marketParams',
            JSON.stringify({ from: '2024-01', to: '2024-03', frequency: 'W' }),
        );
        mount(MARKET_TOOLBAR_HTML);
        loadStores();

        expect(window.appState.marketParams.get()).toEqual({
            from: '2024-01',
            to: '2024-03',
            frequency: 'W',
        });
        expect(document.getElementById('stat-frequency').value).toBe('W');
        expect(document.getElementById('assess-frequency').value).toBe('W');
    });

    it('mirrors the horizon into the bar\u2019s submit-only inputs', () => {
        window.localStorage.setItem(
            'marketParams',
            JSON.stringify({ from: '2024-01', to: '2024-03' }),
        );
        mount(MARKET_TOOLBAR_HTML);
        loadStores();

        expect(document.getElementById('start_time').value).toBe('2024-01');
        expect(document.getElementById('end_time').value).toBe('2024-03');
    });
});

describe('marketParams — commit + emit', () => {
    it('commits a toolbar change and emits only the modules that consume it', () => {
        mount(MARKET_TOOLBAR_HTML);
        loadStores();
        const seen = [];
        window.bus.on('module:params-changed', (payload) => seen.push(payload));

        const select = document.getElementById('stat-frequency');
        select.value = 'W';
        select.dispatchEvent(new Event('change', { bubbles: true }));

        expect(window.appState.marketParams.get().frequency).toBe('W');
        expect(window.localStorage.getItem('marketParams')).toContain('"frequency":"W"');
        expect(seen).toHaveLength(1);
        expect(seen[0].modules).toEqual(['market_review', 'statistical', 'assessment']);
    });

    it('keeps the three toolbars in sync through the shared horizon', () => {
        mount(MARKET_TOOLBAR_HTML);
        loadStores();
        const input = document.getElementById('assess-from');
        input.value = '2024-05';
        input.dispatchEvent(new Event('change', { bubbles: true }));

        expect(document.getElementById('mr-from').value).toBe('2024-05');
        expect(document.getElementById('stat-from').value).toBe('2024-05');
        expect(document.getElementById('start_time').value).toBe('2024-05');
    });

    it('exposes a query fragment for the module URL builder', () => {
        window.localStorage.setItem(
            'marketParams',
            JSON.stringify({ from: '2024-01', to: '2024-03', frequency: 'W' }),
        );
        mount(MARKET_TOOLBAR_HTML);
        loadStores();

        expect(window.appState.marketParams.query(['from', 'to', 'frequency'])).toBe(
            'from=2024-01&to=2024-03&frequency=W',
        );
    });
});

describe('assessmentParams', () => {
    it('commits its own knobs', () => {
        mount(ASSESS_TOOLBAR_HTML);
        loadStores();
        const input = document.getElementById('assess-risk-threshold');
        input.value = '85';
        input.dispatchEvent(new Event('change', { bubbles: true }));

        expect(window.appState.assessmentParams.get().risk_threshold).toBe('85');
        expect(window.localStorage.getItem('assessmentParams')).toContain('"risk_threshold":"85"');
    });
});

describe('optionFilter', () => {
    it('hydrates and commits the chain filters', () => {
        window.localStorage.setItem(
            'optionFilter',
            JSON.stringify({ max_dte: '30', moneyness_low: '0.80', moneyness_high: '1.20' }),
        );
        mount(OPTION_TOOLBAR_HTML);
        loadStores();

        expect(document.getElementById('oc-max-dte').value).toBe('30');

        const input = document.getElementById('oc-refresh-interval');
        input.value = '120';
        input.dispatchEvent(new Event('change', { bubbles: true }));

        expect(window.appState.optionFilter.get().refresh_interval).toBe('120');
    });

    it('does not ask the module rerunner for a /render round trip', () => {
        mount(OPTION_TOOLBAR_HTML);
        loadStores();
        expect(window.appState.optionFilter.MODULES).toEqual([]);
    });
});

describe('paramsStore — degraded storage', () => {
    it('falls back to defaults when localStorage is denied', () => {
        mount(MARKET_TOOLBAR_HTML);
        loadStores();
        vi.spyOn(window.localStorage, 'getItem').mockImplementation(() => {
            throw new Error('denied');
        });
        vi.spyOn(window.localStorage, 'setItem').mockImplementation(() => {
            throw new Error('denied');
        });

        expect(() => loadScript('static/state/marketParamsState.js')).not.toThrow();
        expect(() => window.appState.marketParams.set('frequency', 'Q')).not.toThrow();
        expect(window.appState.marketParams.get().frequency).toBe('Q');

        vi.restoreAllMocks();
    });
});

describe('paramsStore — init returns the store', () => {
    it('does not clobber the published global', () => {
        mount(MARKET_TOOLBAR_HTML);
        loadStores();
        const published = window.appState.marketParams;
        expect(published).toBeTruthy();
        expect(typeof published.init).toBe('function');
        expect(published.init()).toBe(published);
    });
});

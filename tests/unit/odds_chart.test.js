/** @vitest-environment jsdom */
// odds_chart.test.js — Expiry Odds tab: the single combined Call/Put chart.
//
// The fixture is the REAL Jinja partial (templates/partials/tab_odds.html)
// paired with the REAL renderer (_oddsRenderCharts in static/option-chain.js).
// Chart.js is stubbed so we can inspect the dataset list and the visibility
// calls the Call / Put switches make.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect, beforeEach } from 'vitest';

import { loadScript, loadStateBundle } from './_loadScript.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(__dirname, '../../templates/partials/tab_odds.html');

// ── Chart.js stub ──────────────────────────────────────────────────────────
class FakeChart {
    constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config;
        this.data = config.data;
        this.options = config.options;
        this._visible = this.data.datasets.map((d) => d.hidden !== true);
        this.updateCount = 0;
        FakeChart.instances.push(this);
    }
    destroy() { this.destroyed = true; }
    update() { this.updateCount += 1; }
    setDatasetVisibility(i, v) { this._visible[i] = !!v; }
    isDatasetVisible(i) { return this._visible[i]; }
}
FakeChart.instances = [];
FakeChart.defaults = {
    plugins: {
        legend: {
            labels: {
                generateLabels: (chart) => chart.data.datasets.map((ds, i) => ({
                    text: ds.label,
                    datasetIndex: i,
                    hidden: ds.hidden === true,
                    strokeStyle: ds.borderColor,
                    fillStyle: ds.backgroundColor,
                })),
            },
        },
    },
};

// Load the renderer exactly once for the whole file. loadScript() registers an
// anonymous DOMContentLoaded handler that cannot be de-duped, so calling it per
// test would stack a fresh click listener on the switches every run. The
// per-test beforeEach re-fires DOMContentLoaded to rewire the fresh partial.
window.Chart = FakeChart;
loadScript('static/option-chain.js');

// ── Fixture chain data ─────────────────────────────────────────────────────
const SPOT = 100;

function chainData({ putsPriced = true } = {}) {
    const strikes = [80, 90, 95, 100, 105, 110, 120];
    const mkCalls = () => strikes.map((k) => ({ strike: k, ask: 6, bid: 5, lastPrice: 5.5 }));
    const mkPuts = () => strikes.map((k) => ({
        strike: k,
        ask: putsPriced ? 6 : 0,
        bid: putsPriced ? 5 : 0,
        lastPrice: putsPriced ? 5.5 : 0,
    }));
    const exps = ['2026-09-18', '2026-10-16'];
    const chain = {};
    exps.forEach((e) => { chain[e] = { calls: mkCalls(), puts: mkPuts() }; });
    return { spot: SPOT, ticker: 'TEST', expirations: exps, chain };
}

function mount() {
    document.body.innerHTML = fs.readFileSync(TEMPLATE, 'utf8');
}

function seedAndRender(opts) {
    window.appState.oddsChain.setData(chainData(opts));
    window._oddsRenderCharts();
    return FakeChart.instances[FakeChart.instances.length - 1];
}

function click(id) {
    document.getElementById(id).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
}

describe('Expiry Odds — combined Call/Put chart', () => {
    beforeEach(() => {
        FakeChart.instances = [];
        mount();
        loadStateBundle();                 // idempotent (store.js guards on appState)
        window.appState.oddsChain.reset();
        // Re-run the (single) DOMContentLoaded wiring against the fresh nodes.
        document.dispatchEvent(new window.Event('DOMContentLoaded'));
    });

    it('draws exactly one chart holding both Call and Put curves', () => {
        const chart = seedAndRender();
        expect(FakeChart.instances).toHaveLength(1);

        const groups = chart.data.datasets.map((d) => d.oddsGroup);
        expect(groups).toContain('call');
        expect(groups).toContain('put');

        // Call curves come first, Put curves after — never interleaved.
        const firstPut = groups.indexOf('put');
        expect(groups.slice(0, firstPut).every((g) => g === 'call')).toBe(true);
        expect(groups.slice(firstPut).every((g) => g === 'put')).toBe(true);
    });

    it('renders Put curves dashed and Call curves solid', () => {
        const chart = seedAndRender();
        const calls = chart.data.datasets.filter((d) => d.oddsGroup === 'call');
        const puts = chart.data.datasets.filter((d) => d.oddsGroup === 'put');
        expect(calls.every((d) => d.borderDash === undefined)).toBe(true);
        expect(puts.every((d) => Array.isArray(d.borderDash))).toBe(true);
    });

    it('both switches start on (active + aria-pressed)', () => {
        seedAndRender();
        for (const id of ['odds-toggle-call', 'odds-toggle-put']) {
            const btn = document.getElementById(id);
            expect(btn.getAttribute('aria-pressed')).toBe('true');
            expect(btn.classList.contains('active')).toBe(true);
            expect(btn.disabled).toBe(false);
        }
    });

    it('turning the Put switch off hides every Put curve, keeps Calls', () => {
        const chart = seedAndRender();
        click('odds-toggle-put');

        const btn = document.getElementById('odds-toggle-put');
        expect(btn.getAttribute('aria-pressed')).toBe('false');
        expect(btn.classList.contains('active')).toBe(false);

        chart.data.datasets.forEach((ds, i) => {
            expect(chart.isDatasetVisible(i)).toBe(ds.oddsGroup === 'call');
        });
        expect(chart.updateCount).toBeGreaterThan(0);
    });

    it('keeps the switch state when the chart re-renders', () => {
        seedAndRender();
        click('odds-toggle-put');            // Put -> off
        const chart2 = seedAndRender();      // e.g. user tweaked "est. move"

        chart2.data.datasets.forEach((ds) => {
            if (ds.oddsGroup === 'put') expect(ds.hidden).toBe(true);
            else expect(ds.hidden).toBe(false);
        });
    });

    it('disables a switch whose group has no priceable options', () => {
        seedAndRender({ putsPriced: false });
        expect(document.getElementById('odds-toggle-put').disabled).toBe(true);
        expect(document.getElementById('odds-toggle-call').disabled).toBe(false);
    });

    it('legend shows one entry per expiration and toggles both groups together', () => {
        const chart = seedAndRender();
        const legend = chart.options.plugins.legend;

        const labels = legend.labels.generateLabels(chart);
        expect(labels).toHaveLength(2);                       // two expirations, not four
        expect(labels.map((l) => l.text)).toEqual(['20260918', '20261016']);

        // Clicking the first legend entry hides both its Call and its Put curve.
        legend.onClick(null, labels[0], { chart });
        const base = '20260918';
        chart.data.datasets.forEach((ds, i) => {
            if (ds.label.replace(/ [CP]$/, '') === base) {
                expect(chart.isDatasetVisible(i)).toBe(false);
            }
        });
    });
});

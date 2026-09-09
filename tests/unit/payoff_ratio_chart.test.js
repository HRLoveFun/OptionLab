/** @vitest-environment jsdom */
// payoff_ratio_chart.test.js — Payoff Ratio tab: the single combined Call/Put chart.
//
// The fixture is the REAL Jinja partial (templates/partials/tab_payoff_ratio.html)
// paired with the REAL renderer (_prRenderCharts in static/option-chain.js).
// Chart.js is stubbed so we can inspect the dataset list and the visibility
// calls the Call / Put switches make.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect, beforeEach } from 'vitest';

import { loadScript, loadStateBundle } from './_loadScript.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(__dirname, '../../templates/partials/tab_payoff_ratio.html');

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

// Local ISO date `n` days from today, so _prDte() reads back ~n regardless
// of when (or in which timezone) the suite runs. Built from local components,
// not toISOString(), to avoid a UTC day-boundary shift.
function isoInDays(n) {
    const d = new Date();
    d.setHours(12, 0, 0, 0);
    d.setDate(d.getDate() + n);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${d.getFullYear()}-${m}-${day}`;
}

// Three expirations at ~10, ~40, ~75 DTE.
const DTES = [10, 40, 75];

function chainData({ putsPriced = true, putAsk = 6, putBid = 3 } = {}) {
    const strikes = [80, 90, 95, 100, 105, 110, 120];
    const mkCalls = () => strikes.map((k) => ({ strike: k, ask: 6, bid: 5, lastPrice: 5.5 }));
    const mkPuts = () => strikes.map((k) => ({
        strike: k,
        ask: putsPriced ? putAsk : 0,
        bid: putsPriced ? putBid : 0,
        lastPrice: putsPriced ? 5.5 : 0,
    }));
    const exps = DTES.map(isoInDays);
    const chain = {};
    exps.forEach((e) => { chain[e] = { calls: mkCalls(), puts: mkPuts() }; });
    return { spot: SPOT, ticker: 'TEST', expirations: exps, chain };
}

function mount() {
    document.body.innerHTML = fs.readFileSync(TEMPLATE, 'utf8');
}

function seedAndRender(opts) {
    window.appState.payoffRatio.setData(chainData(opts));
    window.appState.panels.set('payoff_ratio', 'loaded');   // mirrors loadPayoffRatioData()
    window._prRenderCharts();
    return FakeChart.instances[FakeChart.instances.length - 1];
}

function click(id) {
    document.getElementById(id).dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
}

describe('Payoff Ratio — combined Call/Put chart', () => {
    beforeEach(() => {
        FakeChart.instances = [];
        mount();
        loadStateBundle();                 // idempotent (store.js guards on appState)
        window.appState.payoffRatio.reset();
        // Re-run the (single) DOMContentLoaded wiring against the fresh nodes.
        document.dispatchEvent(new window.Event('DOMContentLoaded'));
    });

    it('draws exactly one chart holding both Call and Put curves', () => {
        const chart = seedAndRender();
        expect(FakeChart.instances).toHaveLength(1);

        const groups = chart.data.datasets.map((d) => d.prGroup);
        expect(groups).toContain('call');
        expect(groups).toContain('put');

        // Call curves come first, Put curves after — never interleaved.
        const firstPut = groups.indexOf('put');
        expect(groups.slice(0, firstPut).every((g) => g === 'call')).toBe(true);
        expect(groups.slice(firstPut).every((g) => g === 'put')).toBe(true);
    });

    it('renders Put curves dashed and Call curves solid', () => {
        const chart = seedAndRender();
        const calls = chart.data.datasets.filter((d) => d.prGroup === 'call');
        const puts = chart.data.datasets.filter((d) => d.prGroup === 'put');
        expect(calls.every((d) => d.borderDash === undefined)).toBe(true);
        expect(puts.every((d) => Array.isArray(d.borderDash))).toBe(true);
    });

    it('both switches start on (active + aria-pressed)', () => {
        seedAndRender();
        for (const id of ['pr-toggle-call', 'pr-toggle-put']) {
            const btn = document.getElementById(id);
            expect(btn.getAttribute('aria-pressed')).toBe('true');
            expect(btn.classList.contains('active')).toBe(true);
            expect(btn.disabled).toBe(false);
        }
    });

    it('turning the Put switch off hides every Put curve, keeps Calls', () => {
        const chart = seedAndRender();
        click('pr-toggle-put');

        const btn = document.getElementById('pr-toggle-put');
        expect(btn.getAttribute('aria-pressed')).toBe('false');
        expect(btn.classList.contains('active')).toBe(false);

        chart.data.datasets.forEach((ds, i) => {
            expect(chart.isDatasetVisible(i)).toBe(ds.prGroup === 'call');
        });
        expect(chart.updateCount).toBeGreaterThan(0);
    });

    it('keeps the switch state when the chart re-renders', () => {
        seedAndRender();
        click('pr-toggle-put');              // Put -> off
        const chart2 = seedAndRender();      // e.g. user tweaked "est. move"

        chart2.data.datasets.forEach((ds) => {
            if (ds.prGroup === 'put') expect(ds.hidden).toBe(true);
            else expect(ds.hidden).toBe(false);
        });
    });

    it('disables a switch whose group has no priceable options', () => {
        seedAndRender({ putsPriced: false });
        expect(document.getElementById('pr-toggle-put').disabled).toBe(true);
        expect(document.getElementById('pr-toggle-call').disabled).toBe(false);
    });

    it('legend shows one entry per expiration and toggles both groups together', () => {
        const chart = seedAndRender();
        const legend = chart.options.plugins.legend;

        const labels = legend.labels.generateLabels(chart);
        expect(labels).toHaveLength(DTES.length);             // one per expiration, not two
        expect(labels.map((l) => l.text)).toEqual(DTES.map((d) => isoInDays(d).replace(/-/g, '')));

        // Clicking the first legend entry hides both its Call and its Put curve.
        legend.onClick(null, labels[0], { chart });
        const base = labels[0].text;
        chart.data.datasets.forEach((ds, i) => {
            if (ds.label.replace(/ [CP]$/, '') === base) {
                expect(chart.isDatasetVisible(i)).toBe(false);
            }
        });
    });

    // ── Gross payoff ratio, long option priced at the ask ────────────────
    it('is a gross ratio (payoff / premium) and prices the put at the ask', () => {
        // est. move 10% -> putTarget = 90. Strike 100 put: gross payoff = 100-90 = 10.
        // ratio at ask 6 = 10/6 = 1.6667; at (wrong) bid 3 it would be 3.3333.
        const chart = seedAndRender({ putAsk: 6, putBid: 3 });
        const put = chart.data.datasets.find((d) => d.prGroup === 'put');
        const at100 = put.data.find((pt) => pt.x === 100);
        expect(at100.y).toBeCloseTo(1.6667, 3);
        // A strike worthless at the target is 0x (whole premium lost), never negative.
        const at120 = put.data.find((pt) => pt.x === 120);   // K 120 > putTarget 90 -> 30/6 = 5x
        expect(at120.y).toBeGreaterThan(0);
        const at80 = put.data.find((pt) => pt.x === 80);     // K 80 < putTarget 90 -> 0
        expect(at80.y).toBe(0);
    });

    it('registers a breakeven reference line at ratio 1', () => {
        const chart = seedAndRender();
        const ids = (chart.config.plugins || []).map((p) => p.id);
        expect(ids).toContain('breakevenLine');
    });

    // ── est. move slider <-> number input ────────────────────────────────
    it('two-way binds the est. move slider and number input', () => {
        seedAndRender();
        const range = document.getElementById('pr-target-range');
        const num = document.getElementById('pr-target-pct');

        range.value = '25';
        range.dispatchEvent(new window.Event('input', { bubbles: true }));
        expect(num.value).toBe('25');

        num.value = '8';
        num.dispatchEvent(new window.Event('input', { bubbles: true }));
        expect(range.value).toBe('8');
    });

    it('moving the est. move slider re-targets and re-renders the chart', () => {
        seedAndRender();
        const before = FakeChart.instances.length;
        const range = document.getElementById('pr-target-range');
        range.value = '30';
        range.dispatchEvent(new window.Event('input', { bubbles: true }));
        // _prScheduleRender coalesces via requestAnimationFrame.
        return new Promise((r) => window.requestAnimationFrame(r)).then(() => {
            expect(FakeChart.instances.length).toBeGreaterThan(before);
        });
    });

    // ── DTE window dual slider ───────────────────────────────────────────
    it('the DTE window slider filters which expirations are drawn', async () => {
        seedAndRender();                       // full 0–90 window: all 3 expirations
        let chart = FakeChart.instances[FakeChart.instances.length - 1];
        expect(new Set(chart.data.datasets.map((d) => d.label.replace(/ [CP]$/, ''))).size).toBe(3);

        // Narrow to 0–50 DTE: the ~75-DTE expiration drops out.
        const hi = document.getElementById('pr-dte-hi');
        hi.value = '50';
        hi.dispatchEvent(new window.Event('input', { bubbles: true }));
        await new Promise((r) => window.requestAnimationFrame(r));

        chart = FakeChart.instances[FakeChart.instances.length - 1];
        const bases = new Set(chart.data.datasets.map((d) => d.label.replace(/ [CP]$/, '')));
        expect(bases.size).toBe(2);
        expect(bases.has(isoInDays(75).replace(/-/g, ''))).toBe(false);

        // the right-hand number box mirrors the slider
        expect(document.getElementById('pr-dte-hi-num').value).toBe('50');
    });

    it('the DTE number boxes default to 0 and 90 and two-way bind the sliders', async () => {
        seedAndRender();
        const loNum = document.getElementById('pr-dte-lo-num');
        const hiNum = document.getElementById('pr-dte-hi-num');
        const lo = document.getElementById('pr-dte-lo');
        const hi = document.getElementById('pr-dte-hi');
        expect(loNum.value).toBe('0');
        expect(hiNum.value).toBe('90');

        // typing in the box moves the slider (and clamps to 0–90)
        hiNum.value = '30';
        hiNum.dispatchEvent(new window.Event('input', { bubbles: true }));
        expect(hi.value).toBe('30');
        await new Promise((r) => window.requestAnimationFrame(r));
        const chart = FakeChart.instances[FakeChart.instances.length - 1];
        const bases = new Set(chart.data.datasets.map((d) => d.label.replace(/ [CP]$/, '')));
        expect(bases.has(isoInDays(40).replace(/-/g, ''))).toBe(false);   // 40 DTE now outside 0–30

        // moving the slider writes back into the box
        lo.value = '15';
        lo.dispatchEvent(new window.Event('input', { bubbles: true }));
        expect(loNum.value).toBe('15');
    });

    // ── X-axis aligns with the option chain strike range ─────────────────
    it('sets the x-axis min/max to the option chain strike range', () => {
        // fixture strikes: 80..120
        const chart = seedAndRender();
        expect(chart.options.scales.x.min).toBe(80);
        expect(chart.options.scales.x.max).toBe(120);
    });

    // ── X-axis ticks carry the strike's distance from spot ───────────────
    it('labels each x-axis tick with its signed distance from spot', () => {
        const chart = seedAndRender();                 // SPOT = 100
        const cb = chart.options.scales.x.ticks.callback;
        expect(cb(110)).toEqual(['110', '+10.0%']);
        expect(cb(95)).toEqual(['95', '-5.0%']);
        expect(cb(100)).toEqual(['100', '+0.0%']);
    });

    // ── Point tooltip appends the ask the multiple was priced from ───────
    it('carries the ask on every point and appends it to the tooltip label', () => {
        const chart = seedAndRender();                 // fixture call ask = 6
        const call = chart.data.datasets.find((d) => d.prGroup === 'call');
        const pt = call.data.find((p) => p.x === 100);
        expect(pt.ask).toBe(6);

        const label = chart.options.plugins.tooltip.callbacks.label({
            dataset: call, parsed: { y: pt.y }, raw: pt,
        });
        expect(label).toContain(`${call.label}: `);
        expect(label).toContain(`${pt.y.toFixed(2)}x`);
        expect(label).toContain('(ask 6.00)');
    });

    it('clamps the low thumb so it cannot pass the high thumb', () => {
        seedAndRender();
        const lo = document.getElementById('pr-dte-lo');
        const hi = document.getElementById('pr-dte-hi');
        hi.value = '30';
        hi.dispatchEvent(new window.Event('input', { bubbles: true }));
        lo.value = '60';                        // drag lo past hi
        lo.dispatchEvent(new window.Event('input', { bubbles: true }));
        expect(parseInt(lo.value, 10)).toBeLessThanOrEqual(parseInt(hi.value, 10));
    });

    it('keeps the panel loaded when the DTE window excludes everything', async () => {
        seedAndRender();
        const lo = document.getElementById('pr-dte-lo');
        const hi = document.getElementById('pr-dte-hi');
        // Window 85–90: no expiration falls in it (DTES max ~75).
        lo.value = '85';
        lo.dispatchEvent(new window.Event('input', { bubbles: true }));
        hi.value = '90';
        hi.dispatchEvent(new window.Event('input', { bubbles: true }));
        await new Promise((r) => window.requestAnimationFrame(r));

        expect(window.appState.panels.get('payoff_ratio').phase).toBe('loaded');
        const chart = FakeChart.instances[FakeChart.instances.length - 1];
        expect(chart.data.datasets).toHaveLength(0);
    });
});

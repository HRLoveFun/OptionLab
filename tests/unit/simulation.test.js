/** @vitest-environment jsdom */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { loadScript, loadStateBundle } from './_loadScript.js';
// Importing the engine module has the side effect of registering window.SimEngine.
import '../../static/sim/grid.js';

function buildDom() {
    document.body.innerHTML = `
        <input id="ticker" value="nvda">
        <input id="sim-ticker" value="">
        <input id="sim-spot" value="100">
        <select id="sim-option-type"><option value="call" selected>call</option><option value="put">put</option></select>
        <select id="sim-side"><option value="long" selected>long</option><option value="short">short</option></select>
        <input id="sim-strikes" value="95,100">
        <input id="sim-expiries" value="7, 30">
        <input id="sim-ivs" value="20">
        <input id="sim-forward-ivs" value="">
        <input type="checkbox" id="sim-link-iv" checked>
        <input id="sim-rate" value="5">
        <input id="sim-qty" value="1">
        <input id="sim-multiplier" value="100">
        <select id="sim-strike-select"></select>
        <select id="sim-combo-select"></select>
        <input type="range" id="sim-scenario-range" min="90" max="110" step="0.01" value="100">
        <input type="number" id="sim-scenario-price" value="100">
        <canvas id="sim-payoff-chart"></canvas>
        <div id="sim-matrix-body"></div>
        <div id="sim-detail-body"></div>
        <div id="sim-hero-value"></div>
        <div id="sim-hero-sub"></div>
        <div id="sim-kpi-premium"></div>
        <div id="sim-kpi-premium-sub"></div>
        <div id="sim-kpi-breakeven"></div>
        <div id="sim-kpi-extremes"></div>
        <div id="sim-kpi-extremes-sub"></div>
        <div id="sim-kpi-pop"></div>
    `;
}

describe('simulation.js (client engine)', () => {
    let chartInstances;

    beforeEach(() => {
        buildDom();
        loadStateBundle();
        HTMLCanvasElement.prototype.getContext = () => ({});
        chartInstances = [];
        window.Chart = vi.fn(function (ctx, config) {
            this.config = config;
            this.data = config.data;
            this.scales = { x: { min: 90, max: 110 }, y: { min: -1000, max: 10000 } };
            this.update = vi.fn();
            this.destroy = vi.fn();
            chartInstances.push(this);
        });
        window.requestAnimationFrame = (cb) => { cb(); return 1; };
        loadScript('static/simulation.js');
    });

    it('publishes its window surface', () => {
        expect(typeof window.loadSimulationTab).toBe('function');
        expect(typeof window.runSimulation).toBe('function');
    });

    it('computes locally, selects ATM strike, renders hero P&L at spot', async () => {
        await window.loadSimulationTab();
        // ATM (spot 100) long call → premium paid → negative P&L at spot.
        const hero = document.getElementById('sim-hero-value').textContent;
        expect(hero).toMatch(/−\$/);
        expect(chartInstances).toHaveLength(1);
        // datasets: 2 combos + spot + strike + terminal = 5
        expect(chartInstances[0].data.datasets).toHaveLength(5);
        const rows = document.querySelectorAll('#sim-matrix-body tr[data-strike]');
        expect(rows).toHaveLength(2);
        expect(rows[0].querySelectorAll('td[data-idx]')).toHaveLength(2);
        const detailRows = document.querySelectorAll('#sim-detail-body tbody tr');
        expect(detailRows).toHaveLength(2);
        // E[P&L] cell populated for each combo
        expect(document.querySelectorAll('#sim-detail-body td[data-detail-epl]').length).toBe(2);
    });

    it('updates hero and matrix when the scenario slider moves', async () => {
        await window.loadSimulationTab();
        // selected strike 100, combo 0; at 110 intrinsic=10 → pnl positive.
        const range = document.getElementById('sim-scenario-range');
        range.value = '110';
        range.dispatchEvent(new Event('input'));
        const hero = document.getElementById('sim-hero-value').textContent;
        expect(hero).toMatch(/\$/);
        const termLine = chartInstances[0].data.datasets[chartInstances[0].data.datasets.length - 1];
        expect(termLine.data[0].x).toBe(110);
    });

    it('recomputes on explicit runSimulation without throwing', async () => {
        await window.loadSimulationTab();
        await window.runSimulation();
        expect(window.appState.panels.get('simulation').phase).toBe('loaded');
    });

    it('shows error phase when the engine rejects the inputs', async () => {
        document.getElementById('sim-ivs').value = '9999'; // out of [0.001, 5.0]
        const spy = vi.spyOn(console, 'error').mockImplementation(() => { });
        await window.loadSimulationTab();
        spy.mockRestore();
        expect(window.appState.panels.get('simulation').phase).toBe('error');
    });
});

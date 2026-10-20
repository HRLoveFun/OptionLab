/** @vitest-environment jsdom */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { loadScript, loadStateBundle } from './_loadScript.js';

// A small, internally consistent /api/optsim payload (3 spots × 3 dates).
function fakeResponse(overrides = {}) {
    const row = (day, value, pnl, regt, pm) => ({
        day, value, pnl, delta: 1.5, gamma: -0.2, theta: 12.5, vega: -40.25, regt, regt_method: 'naked', pm,
    });
    return {
        status: 'ok',
        style: 'european',
        product: 'etf',
        multiplier: 100,
        spot: 100,
        tree_steps: null,
        legs: [
            { type: 'put', side: 'short', qty: 1, dte: 30, strike: 95, iv: 0.22, premium: 1.2, delta: -0.16 },
            { type: 'call', side: 'short', qty: 1, dte: 30, strike: 105, iv: 0.18, premium: 1.3, delta: 0.16 },
        ],
        entry_value: -250,
        spots: [95, 100, 105],
        days: [0, 15, 30],
        chart_days: [0, 1, 2],
        pnl_by_day: [[-300, 0, -300], [-200, 120, -200], [-250, 250, -250]],
        greeks_by_day: {
            delta: [[60, 0, -60], [70, 0, -70], [100, 0, -100]],
            gamma: [[-5, -8, -5], [-6, -9, -6], [0, 0, 0]],
            theta: [[10, 12, 10], [15, 20, 15], [0, 0, 0]],
            vega: [[-30, -40, -30], [-20, -30, -20], [0, 0, 0]],
        },
        iv_shifts: [-0.05, 0, 0.05],
        pnl_by_iv_at_entry: [[-200, 180, -200], [-300, 0, -300], [-400, -190, -400]],
        breakevens: [97.5, 102.5],
        profile: [row(0, -250, 0, 1000, 400), row(15, -130, 120, 1000, 380), row(30, -0.4, 249.6, 0, 0)],
        ...overrides,
    };
}

function buildDom() {
    document.body.innerHTML = `
        <div id="tab-optsim">
            <button type="button" data-action="optsim-run">Run</button>
            <select id="optsim-preset">
                <option value="">Load preset…</option>
                <option value="iron_condor">Iron condor</option>
                <option value="call_calendar">Calendar</option>
            </select>
            <table><tbody id="optsim-legs-body"></tbody></table>
            <button type="button" data-action="optsim-add-leg">Add leg</button>
            <input id="optsim-spot" value="600"><input id="optsim-rate" value="4.5">
            <input id="optsim-div" value="1.3"><input id="optsim-atm-iv" value="16">
            <input id="optsim-skew" value="-0.77"><input id="optsim-curvature" value="1">
            <input id="optsim-multiplier" value="100"><input id="optsim-spot-range" value="15">
            <input id="optsim-iv-shift" value="5">
            <select id="optsim-product"><option value="etf" selected>etf</option></select>
            <button type="button" data-optsim-style="european" aria-pressed="true" class="active">European</button>
            <button type="button" data-optsim-style="american" aria-pressed="false">American</button>
            <button type="button" data-optsim-margin="regt" aria-pressed="true" class="active">Reg-T</button>
            <button type="button" data-optsim-margin="pm" aria-pressed="false">PM</button>
            <button type="button" data-optsim-greek="delta" aria-pressed="true" class="active">Delta</button>
            <button type="button" data-optsim-greek="theta" aria-pressed="false">Theta</button>
            <div id="optsim-hero-label"></div><div id="optsim-hero-value"></div><div id="optsim-hero-sub"></div>
            <span id="optsim-kpi-margin-label"></span><span id="optsim-kpi-margin"></span>
            <span id="optsim-kpi-margin-sub"></span><span id="optsim-kpi-be-label"></span>
            <span id="optsim-kpi-be"></span><span id="optsim-kpi-theta"></span><span id="optsim-kpi-vega"></span>
            <div id="optsim-resolved"></div><div id="optsim-profile"></div>
            <canvas id="optsim-chart-pnl"></canvas><canvas id="optsim-chart-iv"></canvas>
            <canvas id="optsim-chart-greek"></canvas>
        </div>
    `;
}

const click = (selector) => document.querySelector(selector).click();
const text = (id) => document.getElementById(id).textContent;
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('optsim.js (Position Simulator tab)', () => {
    let charts;
    let post;

    beforeEach(() => {
        buildDom();
        loadStateBundle();
        HTMLCanvasElement.prototype.getContext = () => ({});
        charts = [];
        window.Chart = vi.fn(function (ctx, config) {
            this.config = config;
            this.data = config.data;
            this.destroy = vi.fn();
            charts.push(this);
        });
        post = vi.fn(async () => fakeResponse());
        window.api = { post };
        loadScript('static/optsim.js');
    });

    it('publishes its window surface', () => {
        expect(typeof window.loadOptsimTab).toBe('function');
        expect(typeof window.runOptsim).toBe('function');
        expect(typeof window.optsimDebug).toBe('function');
    });

    it('loads the default strangle and posts delta-picked legs with the market inputs', async () => {
        window.loadOptsimTab();
        await flush();
        expect(document.querySelectorAll('#optsim-legs-body tr')).toHaveLength(2);
        expect(post).toHaveBeenCalledTimes(1);
        const [url, opts] = post.mock.calls[0];
        expect(url).toBe('/api/optsim');
        expect(opts.key).toBe('optsim');
        expect(opts.body).toMatchObject({ spot: 600, rate: 4.5, atm_iv: 16, product: 'etf', style: 'european' });
        expect(opts.body.legs[0]).toEqual({ type: 'put', side: 'short', qty: 1, dte: 45, delta: 0.16 });
        expect(window.appState.panels.get('optsim').phase).toBe('loaded');
    });

    it('renders the credit, the binding margin with return on margin, and three charts', async () => {
        window.loadOptsimTab();
        await flush();
        expect(text('optsim-hero-label')).toBe('Net credit');
        expect(text('optsim-hero-value')).toBe('$250');
        expect(text('optsim-kpi-margin-label')).toBe('Reg-T margin');
        expect(text('optsim-kpi-margin')).toBe('$1,000');
        expect(text('optsim-kpi-margin-sub')).toBe('naked · max-profit ROM 25.0%');
        expect(text('optsim-kpi-be')).toBe('97.50 / 102.50');
        expect(text('optsim-kpi-theta')).toBe('+$12.50');
        expect(text('optsim-kpi-vega')).toBe('−$40.25');
        expect(charts).toHaveLength(3);
        const labels = charts[0].data.datasets.map((d) => d.label);
        expect(labels).toEqual(['Entry', 'Day 15', 'Day 30 (expiry)']);
        expect(charts[1].data.datasets.map((d) => d.label)).toEqual(['IV −5 vol pts', 'IV unchanged', 'IV +5 vol pts']);
    });

    it('prints values that round to zero without a sign', async () => {
        window.loadOptsimTab();
        await flush();
        const lastRow = [...document.querySelectorAll('#optsim-profile tbody tr')].pop();
        const cells = [...lastRow.querySelectorAll('td')].map((td) => td.textContent);
        expect(cells[0]).toBe('30 (expiry)');
        expect(cells[1]).toBe('$0');
    });

    it('switches the margin regime without a new request', async () => {
        window.loadOptsimTab();
        await flush();
        click('[data-optsim-margin="pm"]');
        expect(post).toHaveBeenCalledTimes(1);
        expect(text('optsim-kpi-margin-label')).toBe('Portfolio margin');
        expect(text('optsim-kpi-margin')).toBe('$400');
        expect(document.querySelector('[data-optsim-margin="pm"]').getAttribute('aria-pressed')).toBe('true');
        const bound = document.querySelectorAll('#optsim-profile .optsim-binding');
        expect(bound[0].textContent).toBe('PM');
    });

    it('re-runs with American exercise when the style switch flips', async () => {
        window.loadOptsimTab();
        await flush();
        post.mockResolvedValueOnce(fakeResponse({ style: 'american', tree_steps: 100 }));
        click('[data-optsim-style="american"]');
        await flush();
        expect(post).toHaveBeenCalledTimes(2);
        expect(post.mock.calls[1][1].body.style).toBe('american');
        expect(text('optsim-hero-sub')).toContain('100-step tree');
    });

    it('redraws only the Greek chart when another Greek is picked', async () => {
        window.loadOptsimTab();
        await flush();
        click('[data-optsim-greek="theta"]');
        expect(charts).toHaveLength(4);
        expect(charts[3].config.options.scales.y.title.text).toBe('Theta ($ per day)');
        expect(charts[3].data.datasets[1].data.map((p) => p.y)).toEqual([15, 20, 15]);
    });

    it('edits legs: add, switch a leg to a strike, remove', async () => {
        window.loadOptsimTab();
        await flush();
        click('[data-action="optsim-add-leg"]');
        expect(document.querySelectorAll('#optsim-legs-body tr')).toHaveLength(3);

        const by = document.querySelector('#optsim-legs-body tr[data-leg="0"] select[data-field="by"]');
        by.value = 'strike';
        by.dispatchEvent(new Event('change', { bubbles: true }));
        expect(window.optsimDebug().buildPayload().legs[0]).toMatchObject({ strike: 600 });

        document.querySelector('#optsim-legs-body tr[data-leg="2"] [data-action="optsim-remove-leg"]').click();
        expect(document.querySelectorAll('#optsim-legs-body tr')).toHaveLength(2);
    });

    it('applies a preset and runs it', async () => {
        window.loadOptsimTab();
        await flush();
        const preset = document.getElementById('optsim-preset');
        preset.value = 'call_calendar';
        preset.dispatchEvent(new Event('change'));
        await flush();
        const legs = post.mock.calls[1][1].body.legs;
        expect(legs.map((l) => [l.dte, l.strike])).toEqual([[30, 600], [60, 600]]);
        expect(preset.value).toBe('');
    });

    it('shows the server message in the error phase', async () => {
        post.mockRejectedValueOnce(Object.assign(new Error('leg 1 strike must be between 120 and 1800'), {
            name: 'ApiError',
        }));
        window.loadOptsimTab();
        await flush();
        const state = window.appState.panels.get('optsim');
        expect(state.phase).toBe('error');
        expect(state.message).toBe('leg 1 strike must be between 120 and 1800');
    });
});

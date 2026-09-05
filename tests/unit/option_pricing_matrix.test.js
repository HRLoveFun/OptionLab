/** @vitest-environment jsdom */
// option_pricing_matrix.test.js — DOM layer for the Option Pricing Matrix tab.
//
// No mocked data: the fixture is the REAL Jinja partial
// (templates/partials/tab_option_pricing_matrix.html) and the numbers come from the
// REAL engine (static/sim/option_pricing_matrix.js). That pairing is the point — if a
// template id and the script ever drift apart, this suite fails.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { loadScript, loadStateBundle } from './_loadScript.js';
// Importing the engine module publishes window.OptionPricingMatrix.
import '../../static/sim/option_pricing_matrix.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(__dirname, '../../templates/partials/tab_option_pricing_matrix.html');

// Let the async calendar fetch (now the only column source) resolve in tests.
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

// Column DTEs the calendar mock returns; kept in sync with conftest's
// FAKE_EXPIRY_CALENDAR so header assertions stay deterministic.
const LADDER_DTES = [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56, 61, 66, 71, 76, 81, 86];

function mountTemplate() {
    document.body.innerHTML = fs.readFileSync(TEMPLATE, 'utf8');
}

function phase() {
    return window.appState.panels.get('option_pricing_matrix').phase;
}

function fireInput(id, value) {
    const node = document.getElementById(id);
    node.value = value;
    node.dispatchEvent(new window.Event('input', { bubbles: true }));
}

describe('option_pricing_matrix.js (DOM layer)', () => {
    beforeEach(() => {
        mountTemplate();
        loadStateBundle();
        window.requestAnimationFrame = (cb) => { cb(); return 1; };
        // Columns are sourced from /api/expiry_calendar; provide a deterministic
        // canned response so the render pipeline runs without network.
        window.api = {
            get: vi.fn().mockResolvedValue({
                status: 'ok',
                reference_date: '2026-09-04',
                expirations: [1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, 56, 61, 66, 71, 76, 81, 86].map((d) => ({
                    date: '2026-09-04',
                    dte: d,
                    label: `${d}D`,
                    kind: 'standard',
                    cycle: 'monthly',
                })),
            }),
        };
        loadScript('static/option_pricing_matrix.js');
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('publishes its window surface', () => {
        expect(typeof window.loadOptionPricingMatrix).toBe('function');
    });

    it('renders the default 41 × 18 grid straight from the real partial', async () => {
        await window.loadOptionPricingMatrix();
        await flush();

        expect(phase()).toBe('loaded');
        const table = document.getElementById('opm-matrix');
        expect(table).toBeTruthy();
        expect(table.querySelectorAll('tbody tr')).toHaveLength(41);
        expect(table.querySelectorAll('tbody tr')[0].querySelectorAll('td.opm-cell')).toHaveLength(18);
        expect(table.querySelectorAll('.opm-half--call')).toHaveLength(41 * 18);
        expect(table.querySelectorAll('.opm-half--put')).toHaveLength(41 * 18);
        // 18 DTE columns plus the strike and sigma rails
        expect(table.querySelectorAll('thead th')).toHaveLength(20);

        // Strikes run 80 → 120, ATM row is flagged.
        const rows = table.querySelectorAll('tbody tr');
        expect(rows[0].querySelector("th[scope='row']").textContent).toBe('80');
        expect(rows[40].querySelector("th[scope='row']").textContent).toBe('120');
        expect(table.querySelectorAll('tr.opm-row-atm')).toHaveLength(1);
        expect(rows[20].classList.contains('opm-row-atm')).toBe(true);

        // Every cell shows a price and a premium rate.
        const first = rows[0].querySelector('td.opm-cell');
        expect(first.querySelector('.opm-half--call .opm-val--price').textContent).toMatch(/^\d/);
        expect(first.querySelector('.opm-half--call .opm-val--rate').textContent).toMatch(/%$/);
    });

    it('fills the hero metric and the KPI strip', async () => {
        await window.loadOptionPricingMatrix();
        await flush();

        expect(document.getElementById('opm-hero-value').textContent).toMatch(/%$/);
        expect(document.getElementById('opm-hero-sub').textContent).toContain('ATM 100');
        expect(document.getElementById('opm-kpi-grid').textContent).toBe('41 × 18');
        expect(document.getElementById('opm-kpi-sigma').textContent).not.toBe('—');
        expect(document.getElementById('opm-kpi-call').textContent).not.toBe('—');
        expect(document.getElementById('opm-kpi-put').textContent).not.toBe('—');
        expect(document.getElementById('opm-kpi-call-sub').textContent).toContain('mid');
    });

    it('drives the four visibility switches through data attributes only', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');
        const hint = document.getElementById('opm-all-hidden');
        const click = (name) => document
            .querySelector(`[data-opm-toggle="${name}"]`)
            .dispatchEvent(new window.Event('click', { bubbles: true }));

        expect(hint.hidden).toBe(true);

        click('price');
        expect(table.dataset.showPrice).toBe('0');
        expect(table.dataset.showPremium).toBe('1');
        expect(hint.hidden).toBe(true);

        click('premium');
        expect(table.dataset.showPremium).toBe('0');
        expect(hint.hidden).toBe(false); // nothing left to show

        click('premium');
        click('price');
        expect(table.dataset.showPrice).toBe('1');
        expect(hint.hidden).toBe(true);

        click('call');
        expect(table.dataset.showCall).toBe('0');
        expect(table.dataset.showPut).toBe('1');
        click('put');
        expect(table.dataset.showPut).toBe('0');
        expect(hint.hidden).toBe(false);
    });

    it('recalculates on debounced input changes', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        vi.useFakeTimers();
        const before = document.getElementById('opm-kpi-call').textContent;

        fireInput('opm-iv', '45');
        expect(document.getElementById('opm-kpi-call').textContent).toBe(before); // debounced
        vi.advanceTimersByTime(200);
        const after = document.getElementById('opm-kpi-call').textContent;
        expect(after).not.toBe(before);
        expect(parseFloat(after)).toBeGreaterThan(parseFloat(before));

        // A spread pushes the buyer's fill above the mid.
        fireInput('opm-spread', '10');
        vi.advanceTimersByTime(200);
        expect(document.getElementById('opm-kpi-call').textContent).not.toBe(after);
    });

    it('re-scales the sigma rail when the reference expiry changes', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');
        const rail = table.querySelector('td.opm-sigma');
        const atThirtyOne = rail.textContent;

        // Default reference is the column closest to 30D (31D here). The select
        // is gone, so the header carries the state: .is-ref on the <col> and
        // the <th>, plus aria-current on the control itself.
        expect(table.querySelector('col.opm-col-dte.is-ref').dataset.col).toBe('6');
        expect(table.querySelector('th.opm-head-dte.is-ref').dataset.col).toBe('6');
        expect(table.querySelector('th.opm-head-dte.is-ref').getAttribute('aria-current')).toBe('true');
        expect(table.querySelectorAll('.is-ref')).toHaveLength(2);

        table.querySelector('th.opm-head-dte[data-col="0"]')
            .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));

        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        expect(rail.textContent).not.toBe(atThirtyOne);
        // 1 DTE is a much smaller σ move, so the same strike is further out.
        expect(Math.abs(parseFloat(rail.textContent))).toBeGreaterThan(Math.abs(parseFloat(atThirtyOne)));
        // The highlight moves with the reference — exactly one column is ever marked.
        expect(table.querySelector('th.opm-head-dte.is-ref').dataset.col).toBe('0');
        expect(table.querySelector('col.opm-col-dte.is-ref').dataset.col).toBe('0');
        expect(table.querySelectorAll('.is-ref')).toHaveLength(2);
    });

    it('labels every expiration column with a CALL / PUT pair that mirrors the cell', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');

        // <col> map: two sticky rails, then one column per expiration.
        expect(table.querySelectorAll('colgroup col.opm-col-rail')).toHaveLength(2);
        expect(table.querySelectorAll('colgroup col.opm-col-dte')).toHaveLength(18);

        const heads = table.querySelectorAll('th.opm-head-dte');
        expect(heads).toHaveLength(18);
        heads.forEach((head, i) => {
            const dte = LADDER_DTES[i];
            const main = head.querySelector('.opm-head-main').textContent;
            const sub = head.querySelector('.opm-head-sub').textContent;
            const date = head.querySelector('.opm-head-date').textContent;
            // Three-line header: DTE / ±1σ move / MM-DD.
            expect(main).toBe(`${dte}D`);
            expect(sub.startsWith('±')).toBe(true);
            expect(sub.endsWith('%')).toBe(true);
            expect(date).toMatch(/^\d{2}-\d{2}$/);
            // Header and data cell are split the same way — two halves each.
            expect(head.querySelector('.opm-head-pair').children).toHaveLength(2);
            expect(head.querySelector('.opm-head-half--call').textContent).toBe('Call');
            expect(head.querySelector('.opm-head-half--put').textContent).toBe('Put');
        });

        const firstRow = table.querySelector('tbody tr');
        expect(firstRow.querySelectorAll('td.opm-cell')).toHaveLength(18);
        expect(firstRow.querySelector('td.opm-cell').querySelectorAll('.opm-half')).toHaveLength(2);
    });

    it('highlights a column on hover without rewriting a single value', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');
        const host = document.getElementById('opm-matrix-body');
        const rail = table.querySelector('td.opm-sigma');
        const railBefore = rail.textContent;
        const headBefore = document.getElementById('opm-head-sigma').textContent;

        table.querySelector('tbody tr td.opm-cell[data-col="5"]')
            .dispatchEvent(new window.MouseEvent('mouseover', { bubbles: true }));

        expect(table.querySelector('col.opm-col-dte[data-col="5"]').classList.contains('is-hover')).toBe(true);
        expect(table.querySelector('th.opm-head-dte[data-col="5"]').classList.contains('is-hover')).toBe(true);
        // Hovering is a crosshair, not a preview: numbers stay put.
        expect(rail.textContent).toBe(railBefore);
        expect(document.getElementById('opm-head-sigma').textContent).toBe(headBefore);

        // Exactly one column is ever highlighted.
        table.querySelector('tbody tr td.opm-cell[data-col="6"]')
            .dispatchEvent(new window.MouseEvent('mouseover', { bubbles: true }));
        expect(table.querySelector('col.opm-col-dte[data-col="5"]').classList.contains('is-hover')).toBe(false);
        expect(table.querySelector('col.opm-col-dte[data-col="6"]').classList.contains('is-hover')).toBe(true);
        expect(table.querySelectorAll('.is-hover')).toHaveLength(2); // <col> + header

        host.dispatchEvent(new window.MouseEvent('mouseleave'));
        expect(table.querySelectorAll('.is-hover')).toHaveLength(0);
    });

    it('clicking a column header promotes it to the sigma reference', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');
        const railBefore = table.querySelector('td.opm-sigma').textContent;

        table.querySelector('th.opm-head-dte[data-col="0"]')
            .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));

        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        expect(table.querySelector('td.opm-sigma').textContent).not.toBe(railBefore);
        // The header IS the readout now, so it can never contradict the rail.
        expect(table.querySelector('th.opm-head-dte.is-ref').dataset.col).toBe('0');
        expect(window.optionPricingMatrixDebug().refCol).toBe(0);
    });

    it('moves the sigma reference from the keyboard (Enter / Space / arrows)', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');
        const head = (i) => table.querySelector('th.opm-head-dte[data-col="' + i + '"]');
        // The header anchors the arrow-key walk, so it has to be tabbable.
        expect(head(0).getAttribute('tabindex')).toBe('0');

        head(0).dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        expect(head(0).classList.contains('is-ref')).toBe(true);

        // Space activates too — and is swallowed, or it scrolls the grid away.
        const space = new window.KeyboardEvent('keydown', { key: ' ', bubbles: true, cancelable: true });
        head(1).dispatchEvent(space);
        expect(space.defaultPrevented).toBe(true);
        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @6D');

        // ArrowLeft / ArrowRight walk the date axis one column at a time, and
        // move focus with the reference so the next press keeps stepping.
        head(1).dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        head(0).dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
        // Clamped at the left edge instead of wrapping.
        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        head(0).dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @6D');
        // Focus travelled with the reference; the old column is unmarked.
        expect(document.activeElement).toBe(head(1));
        expect(head(0).classList.contains('is-ref')).toBe(false);
        expect(table.querySelectorAll('.is-ref')).toHaveLength(2);
    });

    it('picks the reference when a data cell is clicked', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        const table = document.getElementById('opm-matrix');

        // Clicking anywhere in a column — data cell or header — promotes it.
        table.querySelector('tbody tr td.opm-cell[data-col="0"]')
            .dispatchEvent(new window.MouseEvent('click', { bubbles: true }));

        expect(document.getElementById('opm-head-sigma').textContent).toBe('σ @1D');
        expect(table.querySelector('th.opm-head-dte.is-ref').dataset.col).toBe('0');
        expect(window.optionPricingMatrixDebug().refCol).toBe(0);
    });

    it('reports invalid inputs in Chinese and falls back to idle without a price', async () => {
        await window.loadOptionPricingMatrix();
        await flush();
        expect(phase()).toBe('loaded');

        vi.useFakeTimers();
        fireInput('opm-iv', '0');
        vi.advanceTimersByTime(200);
        expect(phase()).toBe('error');
        expect(window.appState.panels.get('option_pricing_matrix').message).toMatch(/隐含波动率/);

        // Missing price: the Recalculate button drops the panel back to idle
        // instead of erroring (the user simply has not finished typing).
        document.getElementById('opm-iv').value = '25';
        document.getElementById('opm-price').value = '';
        document
            .querySelector('[data-action="opm-run"]')
            .dispatchEvent(new window.Event('click', { bubbles: true }));
        vi.advanceTimersByTime(1); // flush the async calendar fetch under fake timers
        expect(phase()).toBe('idle');
    });
});

/** @vitest-environment jsdom */
// premium_matrix.test.js — DOM layer for the Premium Matrix tab.
//
// No mocked data: the fixture is the REAL Jinja partial
// (templates/partials/tab_premium_matrix.html) and the numbers come from the
// REAL engine (static/sim/premium_matrix.js). That pairing is the point — if a
// template id and the script ever drift apart, this suite fails.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { loadScript, loadStateBundle } from './_loadScript.js';
// Importing the engine module publishes window.PremiumMatrix.
import '../../static/sim/premium_matrix.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATE = path.resolve(__dirname, '../../templates/partials/tab_premium_matrix.html');

function mountTemplate() {
    document.body.innerHTML = fs.readFileSync(TEMPLATE, 'utf8');
}

function phase() {
    return window.appState.panels.get('premium_matrix').phase;
}

function fireInput(id, value) {
    const node = document.getElementById(id);
    node.value = value;
    node.dispatchEvent(new window.Event('input', { bubbles: true }));
}

describe('premium_matrix.js (DOM layer)', () => {
    beforeEach(() => {
        mountTemplate();
        loadStateBundle();
        window.requestAnimationFrame = (cb) => { cb(); return 1; };
        loadScript('static/premium_matrix.js');
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('publishes its window surface', () => {
        expect(typeof window.loadPremiumMatrix).toBe('function');
    });

    it('renders the default 41 × 18 grid straight from the real partial', () => {
        window.loadPremiumMatrix();

        expect(phase()).toBe('loaded');
        const table = document.getElementById('pm-matrix');
        expect(table).toBeTruthy();
        expect(table.querySelectorAll('tbody tr')).toHaveLength(41);
        expect(table.querySelectorAll('tbody tr')[0].querySelectorAll('td.pm-cell')).toHaveLength(18);
        expect(table.querySelectorAll('.pm-half--call')).toHaveLength(41 * 18);
        expect(table.querySelectorAll('.pm-half--put')).toHaveLength(41 * 18);
        // 18 DTE columns plus the strike and sigma rails
        expect(table.querySelectorAll('thead th')).toHaveLength(20);

        // Strikes run 80 → 120, ATM row is flagged.
        const rows = table.querySelectorAll('tbody tr');
        expect(rows[0].querySelector("th[scope='row']").textContent).toBe('80');
        expect(rows[40].querySelector("th[scope='row']").textContent).toBe('120');
        expect(table.querySelectorAll('tr.pm-row-atm')).toHaveLength(1);
        expect(rows[20].classList.contains('pm-row-atm')).toBe(true);

        // Every cell shows a price and a premium rate.
        const first = rows[0].querySelector('td.pm-cell');
        expect(first.querySelector('.pm-half--call .pm-val--price').textContent).toMatch(/^\d/);
        expect(first.querySelector('.pm-half--call .pm-val--rate').textContent).toMatch(/%$/);
    });

    it('fills the hero metric and the KPI strip', () => {
        window.loadPremiumMatrix();

        expect(document.getElementById('pm-hero-value').textContent).toMatch(/%$/);
        expect(document.getElementById('pm-hero-sub').textContent).toContain('ATM 100');
        expect(document.getElementById('pm-kpi-grid').textContent).toBe('41 × 18');
        expect(document.getElementById('pm-kpi-sigma').textContent).not.toBe('—');
        expect(document.getElementById('pm-kpi-call').textContent).not.toBe('—');
        expect(document.getElementById('pm-kpi-put').textContent).not.toBe('—');
        expect(document.getElementById('pm-kpi-call-sub').textContent).toContain('mid');
    });

    it('drives the four visibility switches through data attributes only', () => {
        window.loadPremiumMatrix();
        const table = document.getElementById('pm-matrix');
        const hint = document.getElementById('pm-all-hidden');
        const click = (name) => document
            .querySelector(`[data-pm-toggle="${name}"]`)
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

    it('recalculates on debounced input changes', () => {
        vi.useFakeTimers();
        window.loadPremiumMatrix();
        const before = document.getElementById('pm-kpi-call').textContent;

        fireInput('pm-iv', '45');
        expect(document.getElementById('pm-kpi-call').textContent).toBe(before); // debounced
        vi.advanceTimersByTime(200);
        const after = document.getElementById('pm-kpi-call').textContent;
        expect(after).not.toBe(before);
        expect(parseFloat(after)).toBeGreaterThan(parseFloat(before));

        // A spread pushes the buyer's fill above the mid.
        fireInput('pm-spread', '10');
        vi.advanceTimersByTime(200);
        expect(document.getElementById('pm-kpi-call').textContent).not.toBe(after);
    });

    it('re-scales the sigma rail when the reference expiry changes', () => {
        window.loadPremiumMatrix();
        const rail = document.querySelector('td.pm-sigma');
        const atThirtyOne = rail.textContent;

        const select = document.getElementById('pm-ref-dte');
        expect(select.options.length).toBe(18);
        select.value = '0';
        select.dispatchEvent(new window.Event('change', { bubbles: true }));

        expect(document.getElementById('pm-head-sigma').textContent).toBe('σ @1D');
        expect(rail.textContent).not.toBe(atThirtyOne);
        // 1 DTE is a much smaller σ move, so the same strike is further out.
        expect(Math.abs(parseFloat(rail.textContent))).toBeGreaterThan(Math.abs(parseFloat(atThirtyOne)));
    });

    it('reports invalid inputs in Chinese and falls back to idle without a price', () => {
        window.loadPremiumMatrix();
        expect(phase()).toBe('loaded');

        vi.useFakeTimers();
        fireInput('pm-iv', '0');
        vi.advanceTimersByTime(200);
        expect(phase()).toBe('error');
        expect(window.appState.panels.get('premium_matrix').message).toMatch(/隐含波动率/);

        // Missing price: the Recalculate button drops the panel back to idle
        // instead of erroring (the user simply has not finished typing).
        document.getElementById('pm-iv').value = '25';
        document.getElementById('pm-price').value = '';
        document
            .querySelector('[data-action="pm-run"]')
            .dispatchEvent(new window.Event('click', { bubbles: true }));
        expect(phase()).toBe('idle');
    });
});

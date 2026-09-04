/* Simulation tab — expiration P&L across strikes × maturities × implied vols.
 *
 * Consumes POST /api/simulate_expiry. The server returns one payoff curve per
 * (strike, maturity, vol) cell; this module only selects, charts and tabulates
 * them. Scenario P&L at an arbitrary terminal price is derived client-side
 * from `premium` so dragging the slider never re-hits the API:
 *
 *     pnl(S_T) = side × qty × multiplier × (intrinsic(S_T) − premium)
 */
(function () {
    'use strict';

    const PANEL = 'simulation';

    let data = null;              // last /api/simulate_expiry payload
    let selectedStrike = null;
    let selectedCombo = 0;        // index into data.combos
    let scenarioPrice = 0;
    let chart = null;
    let wired = false;
    let rafPending = false;

    // Categorical palette for scenario curves. Colour encodes implied vol,
    // dash pattern encodes maturity — see renderChart().
    // TRADEOFF: hue-cycling rather than hand-picked colors because the number
    // of vol scenarios is user-controlled (1..5).
    function seriesColor(idx) {
        const hue = (idx * 137.508) % 360;
        return `hsl(${hue.toFixed(1)}, 62%, 45%)`;
    }

    const DASH_BY_DTE = [[], [8, 4], [2, 3], [10, 3, 2, 3], [4, 4], [1, 4]];

    const el = (id) => document.getElementById(id);

    function fmtNum(v, digits) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return Number(v).toLocaleString('en-US', {
            minimumFractionDigits: digits === undefined ? 2 : digits,
            maximumFractionDigits: digits === undefined ? 2 : digits,
        });
    }

    function fmtMoney(v) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        const sign = v > 0 ? '+' : (v < 0 ? '−' : '');
        return sign + '$' + fmtNum(Math.abs(v));
    }

    function fmtPct(v, digits) {
        if (v === null || v === undefined || isNaN(v)) return '—';
        return (v * 100).toFixed(digits === undefined ? 1 : digits) + '%';
    }

    function esc(v) {
        return window.escapeHtml ? window.escapeHtml(v) : String(v == null ? '' : v);
    }

    /* -- payoff algebra (mirrors core.options.simulation.expiry) ---------- */
    function intrinsicAt(price, strike) {
        return data.option_type === 'call'
            ? Math.max(price - strike, 0)
            : Math.max(strike - price, 0);
    }

    function pnlAt(cell, strike, price) {
        const sign = data.side === 'long' ? 1 : -1;
        return sign * data.qty * data.multiplier * (intrinsicAt(price, strike) - cell.premium);
    }

    function strikeRow(strike) {
        return data.results.find((r) => Math.abs(r.strike - strike) < 1e-9)
            || data.results[0];
    }

    function selectedRow() {
        return strikeRow(selectedStrike);
    }

    function selectedCell() {
        const row = selectedRow();
        return row.cells[Math.min(selectedCombo, row.cells.length - 1)];
    }

    /* -- reads ------------------------------------------------------------ */
    function readInputs() {
        const inheritTicker = ((el('ticker') || {}).value || '').trim();
        const linkEl = el('sim-link-iv');
        const link = linkEl ? linkEl.checked !== false : true; // default linked
        const fwdEl = el('sim-forward-ivs');
        return {
            ticker: ((el('sim-ticker') || {}).value || inheritTicker).trim().toUpperCase(),
            spot: (el('sim-spot') || {}).value || null,
            option_type: (el('sim-option-type') || {}).value || 'call',
            side: (el('sim-side') || {}).value || 'long',
            strikes: (el('sim-strikes') || {}).value || null,
            expiries: (el('sim-expiries') || {}).value || '7, 30, 60, 90',
            ivs: (el('sim-ivs') || {}).value || '20, 30, 45',
            forwardIvs: link ? null : (fwdEl ? fwdEl.value : null),
            linkIv: link,
            r: (el('sim-rate') || {}).value || 5,
            qty: (el('sim-qty') || {}).value || 1,
            multiplier: (el('sim-multiplier') || {}).value || 100,
        };
    }

    function errMessage(err) {
        if (!err) return 'Simulation failed.';
        if (err.detail && err.detail.message) return err.detail.message;
        return err.message || 'Simulation failed.';
    }

    /* -- run -------------------------------------------------------------- */
    async function runSimulation() {
        const p = readInputs();
        const spot = parseFloat(p.spot);
        if (!Number.isFinite(spot) || spot <= 0) {
            window.appState.panels.set(PANEL, 'idle', {
                message: 'Enter a spot price to run the simulation.',
            });
            return;
        }

        window.appState.panels.set(PANEL, 'loading', { message: 'Simulating expiry payoffs…' });

        try {
            if (typeof window.SimEngine?.simulateExpiry !== 'function') {
                throw new Error('Simulation engine not loaded.');
            }
            const res = window.SimEngine.simulateExpiry({
                ticker: p.ticker,
                spot,
                strikes: p.strikes,
                expiries: p.expiries,
                ivs: p.ivs,
                forwardIvs: p.forwardIvs,
                optionType: p.option_type,
                side: p.side,
                r_pct: parseFloat(p.r),
                qty: parseInt(p.qty, 10) || 1,
                multiplier: parseFloat(p.multiplier) || 100,
            });

            if (!res || !res.results || !res.results.length) {
                window.appState.panels.set(PANEL, 'empty', {
                    message: 'No strikes matched these inputs.',
                });
                return;
            }

            data = res;
            selectedCombo = 0;
            selectedStrike = nearestStrike(res.spot);
            scenarioPrice = res.spot;
            window.appState.panels.set(PANEL, 'loaded', { data: res });
            renderAll();
        } catch (err) {
            window.appState.panels.set(PANEL, 'error', { message: errMessage(err) });
        }
    }

    function nearestStrike(spot) {
        let best = data.results[0].strike;
        let bestGap = Infinity;
        for (const row of data.results) {
            const gap = Math.abs(row.strike - spot);
            if (gap < bestGap) { bestGap = gap; best = row.strike; }
        }
        return best;
    }

    /* -- rendering -------------------------------------------------------- */
    function renderAll() {
        renderSelects();
        renderHero();
        renderChart();
        renderMatrix();
        renderDetail();
    }

    function renderSelects() {
        const strikeSel = el('sim-strike-select');
        if (strikeSel) {
            strikeSel.innerHTML = data.results
                .map((r) => {
                    const atm = Math.abs(r.strike - data.spot) < 1e-9 ? ' (ATM)' : '';
                    const sel = Math.abs(r.strike - selectedStrike) < 1e-9 ? ' selected' : '';
                    return `<option value="${r.strike}"${sel}>${fmtNum(r.strike)}${atm}</option>`;
                })
                .join('');
        }

        const comboSel = el('sim-combo-select');
        if (comboSel) {
            comboSel.innerHTML = data.combos
                .map((c, i) => `<option value="${i}"${i === selectedCombo ? ' selected' : ''}>${esc(c.label)}</option>`)
                .join('');
        }

        const range = el('sim-scenario-range');
        const prices = data.prices;
        if (range) {
            const lo = prices[0];
            const hi = prices[prices.length - 1];
            range.min = String(lo);
            range.max = String(hi);
            range.step = String((hi - lo) / 200);
            range.value = String(scenarioPrice);
            range.setAttribute('aria-valuetext', fmtNum(scenarioPrice));
        }
        const num = el('sim-scenario-price');
        if (num) num.value = scenarioPrice.toFixed(2);
    }

    function renderHero() {
        const row = selectedRow();
        const cell = selectedCell();
        if (!row || !cell) return;

        const pnl = pnlAt(cell, row.strike, scenarioPrice);
        const valueEl = el('sim-hero-value');
        if (valueEl) {
            valueEl.textContent = fmtMoney(pnl);
            valueEl.className = 'metric-hero__value '
                + (pnl > 0 ? 'semantic-pos' : (pnl < 0 ? 'semantic-neg' : ''));
        }
        const sub = el('sim-hero-sub');
        if (sub) {
            const kind = data.option_type === 'call' ? 'Call' : 'Put';
            sub.textContent = `${kind} ${fmtNum(row.strike)} · ${esc(cell.label)} · settles at ${fmtNum(scenarioPrice)}`;
        }

        setText('sim-kpi-premium', fmtMoney(cell.premium));
        setText('sim-kpi-premium-sub', `per contract ×${data.qty}`);
        setText('sim-kpi-breakeven', fmtNum(cell.breakeven));
        setText('sim-kpi-extremes',
            `${cell.max_profit === null ? '∞' : fmtMoney(cell.max_profit)} / ${cell.max_loss === null ? '−∞' : fmtMoney(cell.max_loss)}`);
        setText('sim-kpi-extremes-sub',
            cell.unbounded_profit || cell.unbounded_loss ? 'unbounded side shown as ∞' : 'per position');
        setText('sim-kpi-pop', fmtPct(cell.pop));
    }

    function setText(id, text) {
        const node = el(id);
        if (node) node.textContent = text;
    }

    function renderChart() {
        const canvas = el('sim-payoff-chart');
        if (!canvas || typeof Chart === 'undefined') return;
        const row = selectedRow();
        if (!row) return;

        const prices = data.prices;
        let lo = Infinity;
        let hi = -Infinity;
        for (const cell of row.cells) {
            for (const v of cell.pnl) { if (v < lo) lo = v; if (v > hi) hi = v; }
        }
        if (!isFinite(lo) || !isFinite(hi)) { lo = -1; hi = 1; }
        const pad = Math.max((hi - lo) * 0.08, 1);
        const yMin = lo - pad;
        const yMax = hi + pad;

        const dteOrder = [];
        data.combos.forEach((c) => { if (!dteOrder.includes(c.dte)) dteOrder.push(c.dte); });

        const datasets = row.cells.map((cell, i) => {
            const combo = data.combos[i];
            const hueIdx = data.combos.findIndex((c) => c.iv_pct === combo.iv_pct);
            const dashIdx = dteOrder.indexOf(combo.dte) % DASH_BY_DTE.length;
            const active = i === selectedCombo;
            return {
                label: combo.label,
                data: prices.map((p, j) => ({ x: p, y: cell.pnl[j] })),
                borderColor: seriesColor(hueIdx < 0 ? i : hueIdx),
                backgroundColor: 'transparent',
                borderWidth: active ? 3 : 1.4,
                borderDash: DASH_BY_DTE[dashIdx],
                pointRadius: 0,
                pointHitRadius: 4,
                tension: 0,
            };
        });

        datasets.push({
            label: 'Spot',
            data: [{ x: data.spot, y: yMin }, { x: data.spot, y: yMax }],
            borderColor: '#64748b',
            borderDash: [6, 4],
            borderWidth: 1.2,
            pointRadius: 0,
        });
        datasets.push({
            label: 'Strike',
            data: [{ x: row.strike, y: yMin }, { x: row.strike, y: yMax }],
            borderColor: '#f59e0b',
            borderDash: [6, 4],
            borderWidth: 1.2,
            pointRadius: 0,
        });
        datasets.push({
            label: 'Terminal price',
            data: [{ x: scenarioPrice, y: yMin }, { x: scenarioPrice, y: yMax }],
            borderColor: '#3b82f6',
            borderDash: [2, 3],
            borderWidth: 1.2,
            pointRadius: 0,
        });

        if (chart) { chart.destroy(); chart = null; }

        chart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                parsing: false,
                animation: false,
                interaction: { mode: 'nearest', intersect: false },
                scales: {
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Underlying price at expiration' },
                        ticks: { callback: (v) => fmtNum(v, 2) },
                    },
                    y: {
                        title: { display: true, text: 'P&L (USD)' },
                        ticks: { callback: (v) => fmtMoney(v) },
                        grid: {
                            color: (ctx) => (ctx.tick && ctx.tick.value === 0 ? '#94a3b8' : '#eef2f7'),
                            lineWidth: (ctx) => (ctx.tick && ctx.tick.value === 0 ? 1.5 : 1),
                        },
                    },
                },
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { boxWidth: 24, usePointStyle: false } },
                    tooltip: {
                        callbacks: {
                            title: (items) => 'Price ' + fmtNum(items[0] ? items[0].parsed.x : 0),
                            label: (ctx) => {
                                if (ctx.dataset.label === 'Spot' || ctx.dataset.label === 'Strike'
                                    || ctx.dataset.label === 'Terminal price') {
                                    return ctx.dataset.label + ' ' + fmtNum(ctx.parsed.x);
                                }
                                return `${ctx.dataset.label}: ${fmtMoney(ctx.parsed.y)}`;
                            },
                        },
                    },
                },
            },
        });
    }

    function renderMatrix() {
        const host = el('sim-matrix-body');
        if (!host) return;

        let head = '<tr><th scope="col">Strike</th>';
        data.combos.forEach((c) => {
            head += `<th scope="col"><span class="sim-col-main">${esc(c.label)}</span>`
                + `<span class="sim-col-sub">${esc(c.expiry)}</span></th>`;
        });
        head += '</tr>';

        let body = '';
        data.results.forEach((row) => {
            const active = Math.abs(row.strike - selectedStrike) < 1e-9;
            body += `<tr class="${active ? 'sim-row-active' : ''}" data-strike="${row.strike}">`;
            body += `<th scope="row"><button type="button" class="sim-strike-btn" data-strike="${row.strike}"`
                + ` aria-pressed="${active}">${fmtNum(row.strike)}</button></th>`;
            row.cells.forEach((cell, i) => {
                body += `<td data-strike="${row.strike}" data-idx="${i}"></td>`;
            });
            body += '</tr>';
        });

        host.innerHTML = `<table class="sim-matrix" aria-label="Expiration P&L by strike and scenario">`
            + `<thead>${head}</thead><tbody>${body}</tbody></table>`;
        refreshMatrixValues();
    }

    function refreshMatrixValues() {
        const host = el('sim-matrix-body');
        if (!host || !data) return;
        host.querySelectorAll('td[data-idx]').forEach((td) => {
            const strike = parseFloat(td.getAttribute('data-strike'));
            const idx = parseInt(td.getAttribute('data-idx'), 10);
            const row = strikeRow(strike);
            const cell = row && row.cells[idx];
            if (!cell) { td.textContent = '—'; return; }
            const pnl = pnlAt(cell, strike, scenarioPrice);
            td.textContent = fmtMoney(pnl);
            td.className = pnl > 0 ? 'semantic-pos-bg' : (pnl < 0 ? 'semantic-neg-bg' : '');
        });
    }

    function renderDetail() {
        const host = el('sim-detail-body');
        if (!host) return;
        const row = selectedRow();
        if (!row) { host.innerHTML = ''; return; }

        let html = '<table class="sim-detail" aria-label="Scenario detail for the selected strike">'
            + '<thead><tr>'
            + '<th scope="col">Maturity</th><th scope="col">DTE</th><th scope="col">IV</th>'
            + '<th scope="col">Premium</th><th scope="col">Delta</th><th scope="col">Breakeven</th>'
            + '<th scope="col">Max profit</th><th scope="col">Max loss</th>'
            + '<th scope="col">Prob. profit</th><th scope="col">Expected P&amp;L</th>'
            + '<th scope="col">P&L @ terminal</th>'
            + '</tr></thead><tbody>';

        row.cells.forEach((cell, i) => {
            html += `<tr class="${i === selectedCombo ? 'sim-row-active' : ''}">`
                + `<td>${esc(cell.expiry)}</td>`
                + `<td>${cell.dte}</td>`
                + `<td>${fmtNum(cell.iv_pct, 1)}%</td>`
                + `<td>${fmtMoney(cell.premium)}</td>`
                + `<td>${fmtNum(cell.delta, 3)}</td>`
                + `<td>${fmtNum(cell.breakeven)}</td>`
                + `<td>${cell.max_profit === null ? '∞' : fmtMoney(cell.max_profit)}</td>`
                + `<td>${cell.max_loss === null ? '−∞' : fmtMoney(cell.max_loss)}</td>`
                + `<td>${fmtPct(cell.pop)}</td>`
                + `<td data-detail-epl="${i}"></td>`
                + `<td data-detail-idx="${i}"></td>`
                + '</tr>';
        });

        html += '</tbody></table>';
        host.innerHTML = html;
        refreshDetailValues();
    }

    function refreshDetailValues() {
        const host = el('sim-detail-body');
        if (!host || !data) return;
        const row = selectedRow();
        if (!row) return;
        host.querySelectorAll('td[data-detail-idx]').forEach((td) => {
            const idx = parseInt(td.getAttribute('data-detail-idx'), 10);
            const cell = row.cells[idx];
            if (!cell) { td.textContent = '—'; return; }
            const pnl = pnlAt(cell, row.strike, scenarioPrice);
            td.textContent = fmtMoney(pnl);
            td.className = pnl > 0 ? 'semantic-pos' : (pnl < 0 ? 'semantic-neg' : '');
        });
        host.querySelectorAll('td[data-detail-epl]').forEach((td) => {
            const idx = parseInt(td.getAttribute('data-detail-epl'), 10);
            const cell = row.cells[idx];
            if (!cell || cell.expected_pnl === null || cell.expected_pnl === undefined) { td.textContent = '—'; return; }
            td.textContent = fmtMoney(cell.expected_pnl);
            td.className = cell.expected_pnl > 0 ? 'semantic-pos' : (cell.expected_pnl < 0 ? 'semantic-neg' : '');
        });
    }

    function refreshScenario() {
        if (!data) return;
        const num = el('sim-scenario-price');
        if (num && document.activeElement !== num) num.value = scenarioPrice.toFixed(2);
        const range = el('sim-scenario-range');
        if (range) {
            range.value = String(scenarioPrice);
            range.setAttribute('aria-valuetext', fmtNum(scenarioPrice));
        }
        if (chart && chart.data.datasets.length) {
            const line = chart.data.datasets[chart.data.datasets.length - 1];
            const yMin = chart.scales.y.min;
            const yMax = chart.scales.y.max;
            line.data = [{ x: scenarioPrice, y: yMin }, { x: scenarioPrice, y: yMax }];
            chart.update('none');
        }
        renderHero();
        refreshMatrixValues();
        refreshDetailValues();
    }

    function scheduleRefresh() {
        if (rafPending) return;
        rafPending = true;
        window.requestAnimationFrame(() => {
            rafPending = false;
            refreshScenario();
        });
    }

    function setStrike(strike) {
        selectedStrike = strike;
        const sel = el('sim-strike-select');
        if (sel) sel.value = String(strike);
        renderAll();
    }

    function wireControls() {
        const strikeSel = el('sim-strike-select');
        if (strikeSel) {
            strikeSel.addEventListener('change', () => setStrike(parseFloat(strikeSel.value)));
        }

        const comboSel = el('sim-combo-select');
        if (comboSel) {
            comboSel.addEventListener('change', () => {
                selectedCombo = parseInt(comboSel.value, 10) || 0;
                renderHero();
                renderChart();
                renderDetail();
            });
        }

        const range = el('sim-scenario-range');
        if (range) {
            range.addEventListener('input', () => {
                scenarioPrice = parseFloat(range.value);
                scheduleRefresh();
            });
        }

        const num = el('sim-scenario-price');
        if (num) {
            num.addEventListener('change', () => {
                const v = parseFloat(num.value);
                if (!isNaN(v)) { scenarioPrice = v; refreshScenario(); }
            });
        }

        const matrix = el('sim-matrix-body');
        if (matrix) {
            matrix.addEventListener('click', (ev) => {
                const btn = ev.target.closest('.sim-strike-btn');
                if (!btn) return;
                setStrike(parseFloat(btn.getAttribute('data-strike')));
            });
        }
    }

    window.loadSimulationTab = function () {
        if (!wired) { wireControls(); wired = true; }
        // Re-sync the inherited ticker each visit so the panel follows the
        // Parameter tab without forcing the user to retype it.
        const inherit = ((el('ticker') || {}).value || '').trim().toUpperCase();
        const own = el('sim-ticker');
        if (own && inherit && own.value.trim().toUpperCase() !== inherit) own.value = inherit;
        runSimulation();
    };

    window.runSimulation = runSimulation;
})();
